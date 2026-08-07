"""EmpathyLens — Week 8 LLM-as-a-Judge runner (评估管道心脏).
读 results 里的生成 JSON,对每条响应循环七维 → assemble_judge_input 拼裁判输入 →
三家裁判打分 → 解析 {markers,score,justification} → 写 results/scores_<run>.json。
照 JUDGE_INPUT_CONTRACT.md 落地:目标文化解析、self_judge 标志、applicable=False 记 N/A。

工程保障:
  - 断点续跑(每 50 次落盘 + 启动跳过已完成);
  - 自动重试 + 指数退避(应对 Anthropic 529 Overloaded / 超时 / 限流等临时错误);
  - 硬错误(余额不足 / 认证失败)→ 存盘后干净退出,提示充值/修复后重跑续跑;
  - 预算守护(--max-cost-eur);--judges 可只用 DeepSeek 先验证。

放置:src/eval/run_judge.py。运行(项目根,需 .env 三家 key):
    python -m src.eval.run_judge --gen results/full_gen_v1.json --judges deepseek-v4-pro   # 先单裁判验证
    python -m src.eval.run_judge --gen results/full_gen_v1.json                            # 三裁判
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import re
import time
from pathlib import Path

from src.dataset import load_dataset
from src.eval.rubrics import DIMENSION_ORDER
from src.eval.assemble_judge_input import assemble

JUDGES = ["gpt-5.4", "claude-opus-4-6", "deepseek-v4-pro"]

# 粗略单价(EUR / 1M tokens, in/out)。仅用于预算预估,按实际账单校准。
# 注:Anthropic opus 实际偏贵,这里估算偏保守,以官网账单为准。
PRICING = {
    "gpt-5.4":          {"in": 2.0, "out": 8.0},
    "claude-opus-4-6":  {"in": 5.0, "out": 15.0},
    "deepseek-v4-pro":  {"in": 0.3, "out": 0.9},
}

# 临时性错误(可重试):服务器过载、限流、超时、网络抖动。
_TRANSIENT = ("529", "overloaded", "503", "502", "500", "429", "rate limit",
              "timeout", "timed out", "connection", "temporarily")
# 硬错误(不可重试,应停):余额不足、认证失败。
_FATAL = ("credit balance", "too low", "insufficient", "401", "authentication",
          "invalid x-api-key", "permission")


def join_lang(rec):
    """目标文化解析(JUDGE_INPUT_CONTRACT §3):en_geo 按源文化 geo,其余按 condition。"""
    return rec["geo"] if rec["condition"] == "en_geo" else rec["lang"]


def parse_judge_json(text):
    """从裁判输出里抽 {markers, score, justification}。失败返回 None。"""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return {"markers": obj.get("markers", []),
                "score": int(obj["score"]),
                "justification": obj.get("justification", "")}
    except (ValueError, KeyError, TypeError):
        return None


def judge_call(call_model, user, system, model, retries=5):
    """调一次裁判,带重试。返回 (raw_text 或 None, err 或 None, fatal:bool)。
    fatal=True 表示余额/认证类硬错误,调用方应存盘后退出。"""
    delay = 4
    for attempt in range(retries):
        try:
            return call_model(prompt=user, system=system, model=model, temperature=0.0), None, False
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in _FATAL):
                return None, str(e)[:200], True
            transient = any(k in msg for k in _TRANSIENT)
            if transient and attempt < retries - 1:
                print(f"      ⏳ {model} 临时错误,{delay}s 后重试({attempt+1}/{retries}): {str(e)[:80]}")
                time.sleep(delay); delay = min(delay * 2, 60); continue
            return None, str(e)[:200], False     # 放弃这一次调用(不写行 → 下次重跑会重试)
    return None, "max_retries", False


def estimate_cost(units, judges):
    """粗估 EUR:每个评分单元 input≈(system+user)/4 token,output≈200 token。"""
    total = 0.0
    for u in units:
        in_tok = len(u["system"] + u["user"]) / 4
        for j in judges:
            p = PRICING.get(j, {"in": 2.0, "out": 8.0})
            total += in_tok / 1e6 * p["in"] + 200 / 1e6 * p["out"]
    return total


def build_units(gen_records, data):
    """对每条生成响应 × 每维,装配评分单元;applicable=False 的(空轴 D4 等)单列、不评分。"""
    units, na_rows = [], []
    for g in gen_records:
        ds = data[f"{g['scenario_id']}_{join_lang(g)}"]      # 目标文化的数据集记录
        base = {"scenario_id": g["scenario_id"], "lang": g["lang"], "condition": g["condition"],
                "geo": g.get("geo"), "prompt_version": g["prompt_version"],
                "gen_model": g["gen_model"], "run_index": g.get("run_index", 0)}
        for dim in DIMENSION_ORDER:
            a = assemble(ds, g["response_text"], dim)
            if not a["applicable"]:
                na_rows.append({**base, "dimension": dim, "judge_model": None,
                                "score": None, "applicable": False, "self_judge": None,
                                "reason": a.get("reason", "")})
                continue
            units.append({**base, "dimension": dim, "system": a["system"], "user": a["user"]})
    return units, na_rows


def main():
    ap = argparse.ArgumentParser(description="Week 8 LLM-as-a-Judge runner.")
    ap.add_argument("--gen", default="results/full_gen_v1.json", help="生成 JSON 路径")
    ap.add_argument("--judges", nargs="+", default=JUDGES)
    ap.add_argument("--out", default=None, help="默认 results/scores_<gen文件名>.json")
    ap.add_argument("--max-cost-eur", type=float, default=30.0)
    ap.add_argument("--yes", action="store_true", help="跳过预算确认")
    ap.add_argument("--dry-run", action="store_true", help="不调 API,假分数验证管道")
    args = ap.parse_args()

    gen = json.loads(Path(args.gen).read_text(encoding="utf-8"))
    data = {r["id"]: r for r in load_dataset()}
    units, na_rows = build_units(gen, data)
    out = Path(args.out or f"results/scores_{Path(args.gen).stem}.json")

    est = estimate_cost(units, args.judges)
    print(f"▶️  {len(units)} 评分单元 × {len(args.judges)} 裁判 = {len(units)*len(args.judges)} 次调用"
          f" + {len(na_rows)} 条 N/A · 预估 ≈ €{est:.2f}（整任务估算;续跑时已完成的会跳过,不重复计费）")
    if not args.dry_run and est > args.max_cost_eur and not args.yes:
        print(f"❌ 预估 €{est:.2f} > 上限 €{args.max_cost_eur}。加 --yes 确认,或 --judges deepseek-v4-pro 先验证。")
        return

    rows, done = list(na_rows), set()
    if out.exists():                                          # 断点续跑
        prev = json.loads(out.read_text(encoding="utf-8"))
        rows = prev
        done = {(r["scenario_id"], r["condition"], r.get("geo"), r["gen_model"],
                 r["run_index"], r["dimension"], r["judge_model"]) for r in prev}
        # 补上本次新场景可能产生、prev 里还没有的 N/A 行
        na_keys = {(r["scenario_id"], r["condition"], r.get("geo"), r["gen_model"],
                    r["run_index"], r["dimension"]) for r in prev if not r.get("applicable")}
        for r in na_rows:
            k = (r["scenario_id"], r["condition"], r.get("geo"), r["gen_model"], r["run_index"], r["dimension"])
            if k not in na_keys:
                rows.append(r)
        print(f"   断点续跑:已有 {len(prev)} 行,跳过已完成。")

    if not args.dry_run:
        from src.llm_client import call_model

    def flush():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    n, skipped = 0, 0
    for u in units:
        for j in args.judges:
            key = (u["scenario_id"], u["condition"], u["geo"], u["gen_model"], u["run_index"], u["dimension"], j)
            if key in done:
                continue
            n += 1
            if args.dry_run:
                parsed = {"markers": ["[dry]"], "score": 3, "justification": "[dry-run]"}
            else:
                raw, err, fatal = judge_call(call_model, u["user"], u["system"], j)
                if fatal:                                     # 余额/认证 → 存盘后干净退出
                    flush()
                    print(f"\n❌ 硬错误({j}),已存盘 {len(rows)} 行。修复后(如充值)重跑同一条会自动续跑。\n   {err}")
                    return
                if raw is None:                               # 临时错误重试仍失败 → 跳过,下次重跑重试
                    skipped += 1
                    print(f"   ⚠️ 跳过(重跑会重试) {u['scenario_id']}/{u['dimension']}/{j}: {err}")
                    continue
                parsed = parse_judge_json(raw)
            row = {k: u[k] for k in ("scenario_id", "lang", "condition", "geo",
                                     "prompt_version", "gen_model", "run_index", "dimension")}
            row.update({"judge_model": j, "applicable": True,
                        "self_judge": (j == u["gen_model"])})
            if parsed:
                row.update(parsed)
            else:
                row.update({"score": None, "markers": [], "justification": "", "parse_error": True})
            rows.append(row)
            if not args.dry_run and n % 50 == 0:              # 每 50 次落盘
                flush(); print(f"   ...{n} 已存盘")

    flush()
    msg = f"\n✅ {len(rows)} 行(含 {len(na_rows)} N/A) → {out}"
    if skipped:
        msg += f"\n⚠️ 有 {skipped} 次因临时错误被跳过——再跑一次同一条命令会把它们补上(续跑)。"
    print(msg + f"（下一步:python -m src.eval.aggregate --scores {out}）")


if __name__ == "__main__":
    main()