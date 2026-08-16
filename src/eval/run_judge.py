"""EmpathyLens — Week 9 风控重写版 LLM-as-a-Judge runner (评估管道心脏).

相对 Week 8 版本的核心变更（详见 EmpathyLens_22周计划_v3 的 Week 9 条目 / 风控框架总览）：
  ① 分级调用协议 --tier {1,2,3}：Tier 1 单裁判 10 条子集试错、Tier 2 三裁判同子集定量确认、
     Tier 3 三裁判 60 条全量（论文最终数据，整个项目周期内只计划执行一次）。
  ② 裁判调用结构性合并：改用 assemble_judge_input.assemble_all()，每条响应每个裁判只调用
     一次（而非每维度一次），调用量降至约 1/7；用一次返回的七维 JSON 展开成与旧版兼容的
     逐维度行，下游 aggregate.py 完全不需要改动。
  ③ 预算硬顶真正硬：取消 --yes 一键跳过；单次跑批上限 --max-cost-eur 与按日累计上限
     --daily-cap-eur 都是硬性拒绝，任何情况下不绕过。
  ④ 主动节流：--sleep-sec 控制每次调用后的强制间隔（不管成功失败都执行），不再是"报错了
     才退避"。
  ⑤ Tier 3 强制人工检查点：必须显式传 --balance-checked 才能执行 Tier 3，否则拒绝启动并
     提示"先登录三家平台后台核对余额"。这是把"人工检查点"从文档要求变成代码强制。
  ⑥ 断点续跑逻辑不变（仍按"响应×维度×裁判"粒度判断是否已完成），但现在的判断单位是
     "本次(响应×裁判)调用要不要发"——只要该响应在该裁判下还有未完成的维度，就会发起
     (一次)调用补齐所有缺失维度，不会因为部分维度已完成就重复调用整条。

工程保障（沿用 Week 8）：断点续跑(每 50 次落盘 + 启动跳过已完成)；自动重试 + 指数退避
（应对服务商临时错误）；硬错误(余额不足/认证失败) → 存盘后干净退出。

⚠️ PRICING 常量仍是估算值，需要用三家平台的真实账单校准后才可信——这是本次重写唯一
没有能力自己完成的一步（我不知道你们的真实账单数字）。启动时会打印醒目提醒。

放置：src/eval/run_judge.py。运行（项目根，需 .env 三家 key）：
    # Tier 1：单裁判 10 条子集冒烟测试，先看格式对不对
    python -m src.eval.run_judge --tier 1 --gen results/week7_sanity_check_v1.json

    # Tier 2：三裁判同子集，定量确认 prompt 改动是否有效
    python -m src.eval.run_judge --tier 2 --gen results/week7_sanity_check_v1.json

    # Tier 3：三裁判 60 条全量——必须显式确认已核对余额
    python -m src.eval.run_judge --tier 3 --gen results/full_gen_v1.json \\
        --balance-checked --max-cost-eur 15 --daily-cap-eur 20
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

from src.dataset import load_dataset
from src.eval.rubrics import DIMENSION_ORDER
from src.eval.assemble_judge_input import assemble_all
from src.eval import budget_ledger

JUDGES = ["gpt-5.4", "claude-opus-4-6", "deepseek-v4-pro"]

# Week 7 sanity 子集的 10 个 scenario_id（week7_sanity_check.md §1.2）。
# Tier 1/2 默认只在这 10 条上跑，不管 --gen 传的文件本身覆盖了多少条。
TIER_SUBSET_SCENARIOS = {"S02", "S05", "S06", "S08", "S14", "S15", "S16", "S17", "S18", "S20"}

TIER_JUDGE_DEFAULTS = {
    1: ["deepseek-v4-pro"],   # 最便宜的一家，先看管道跑不跑得通、格式对不对
    2: JUDGES,                # 三家，同一个 10 条子集，定量确认
    3: JUDGES,                # 三家，60 条全量
}

# ⚠️⚠️⚠️ 粗略单价占位符(EUR / 1M tokens, in/out)。这一版数字沿用 Week 8 的估算，
# 尚未用三家平台的真实账单校准过——在跑 Tier 3 之前，请务必登录三家后台账单页面，
# 用最近一次真实扣费反推实际单价，替换下面这三行。校准前的估算可能偏低（Week 8 的
# 预算失控正是源于这里）。
PRICING = {
    "gpt-5.4":          {"in": 2.0, "out": 8.0},   # TODO: 用真实账单校准
    "claude-opus-4-6":  {"in": 5.0, "out": 15.0},  # TODO: 用真实账单校准
    "deepseek-v4-pro":  {"in": 0.3, "out": 0.9},   # TODO: 用真实账单校准
}

# 单个维度的评分理由(markers + score + justification)大致输出 token 数的估算基数。
# 合并调用后，一次调用的输出是"N 个维度的 JSON"，粗略按每维度 ~260 token 估算。
EST_OUTPUT_TOKENS_PER_DIM = 260

# 临时性错误(可重试):服务器过载、限流、超时、网络抖动。
_TRANSIENT = ("529", "overloaded", "503", "502", "500", "429", "rate limit",
              "timeout", "timed out", "connection", "temporarily")
# 硬错误(不可重试,应停):余额不足、认证失败。
_FATAL = ("credit balance", "too low", "insufficient", "401", "authentication",
          "invalid x-api-key", "permission")


def join_lang(rec):
    """目标文化解析(JUDGE_INPUT_CONTRACT §3):en_geo 按源文化 geo,其余按 condition。"""
    return rec["geo"] if rec["condition"] == "en_geo" else rec["lang"]


def parse_judge_json_multi(text, expected_dims):
    """从裁判输出里抽多维度 JSON：{"D1": {...}, "D2": {...}, ...}。
    返回 dict(dim -> {"markers":..., "score":..., "justification":...})，
    对每个 expected_dims 里的键：解析成功就放进去，解析失败/缺失的维度不放进返回值
    （调用方据此判断哪些维度这次没拿到、需要标记 parse_error）。"""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return {}
    out = {}
    for dim in expected_dims:
        v = obj.get(dim)
        if not isinstance(v, dict):
            continue
        try:
            out[dim] = {"markers": v.get("markers", []),
                       "score": int(v["score"]),
                       "justification": v.get("justification", "")}
        except (ValueError, KeyError, TypeError):
            continue
    return out


def judge_call(call_model, user, system, model, retries=5, sleep_sec=1.5):
    """调一次裁判(现在覆盖全部可评维度)，带重试 + 强制节流。
    返回 (raw_text 或 None, err 或 None, fatal:bool)。
    无论成功/失败/重试，每次真正发起调用后都会 sleep(sleep_sec)——这是 Week 9 新增的
    主动节流，防止短时间内爆发式请求（Week 8 的问题不只是总量大，也是没有节流）。"""
    delay = 4
    for attempt in range(retries):
        try:
            result = call_model(prompt=user, system=system, model=model, temperature=0.0)
            time.sleep(sleep_sec)
            return result, None, False
        except Exception as e:
            time.sleep(sleep_sec)
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
    """粗估 EUR。units 现在是"每条响应"（而非每条响应×维度），每个 unit 对每个
    judge 只发一次调用，input≈(system+user)/4 token，output≈每个可评维度 ~260 token。"""
    total = 0.0
    for u in units:
        in_tok = len(u["system"] + u["user"]) / 4
        out_tok = EST_OUTPUT_TOKENS_PER_DIM * len(u["applicable_dims"])
        for j in judges:
            p = PRICING.get(j, {"in": 2.0, "out": 8.0})
            total += in_tok / 1e6 * p["in"] + out_tok / 1e6 * p["out"]
    return total


def build_units(gen_records, data):
    """对每条生成响应,装配【单次覆盖全部可评维度】的评分单元；N/A 维度(空轴 D4 等)单独
    列为 na_rows，不进入需要调用裁判的 units。

    ⚠️ 字段名兼容说明（Week 9 发现的既有不一致，顺手修掉）：JUDGE_INPUT_CONTRACT.md §2
    文档的字段名是 "model"，week7_sanity_check_v1.json（run_sanity_check.py 的输出）也用
    "model"；但 full_gen_v1.json（Week 8 全量生成脚本的输出）用的是 "gen_model"，且带
    "run_index"（sanity 阶段 N=1 没有这个字段，JUDGE_INPUT_CONTRACT.md §2 的表注也提到了
    这一点）。旧版 run_judge.py 只认 "gen_model"，导致直接对 week7_sanity_check_v1.json
    跑 Tier 1 会在这里报 KeyError——这条兼容逻辑修的就是这个，不用改生成脚本或已有数据文件。
    建议团队后续统一生成脚本的字段命名（在 JUDGE_INPUT_CONTRACT.md 里挑一个定为唯一标准），
    这里的兼容写法只是让 Week 9 的 Tier 1 能立刻可用，不是长期方案。"""
    units, na_rows = [], []
    for g in gen_records:
        ds = data[f"{g['scenario_id']}_{join_lang(g)}"]      # 目标文化的数据集记录
        gen_model = g.get("gen_model") or g.get("model")
        if gen_model is None:
            raise KeyError(f"生成记录缺少 'gen_model'/'model' 字段: {g.get('scenario_id')}")
        base = {"scenario_id": g["scenario_id"], "lang": g["lang"], "condition": g["condition"],
                "geo": g.get("geo"), "prompt_version": g["prompt_version"],
                "gen_model": gen_model, "run_index": g.get("run_index", 0)}
        a = assemble_all(ds, g["response_text"], condition=g["condition"])
        for dim in a["na_dims"]:
            na_rows.append({**base, "dimension": dim, "judge_model": None,
                            "score": None, "applicable": False, "self_judge": None,
                            "reason": "stressed_axes 为空 → 本维记 N/A(不进 Equitability 文化分差)"})
        if a["applicable_dims"]:
            units.append({**base, "applicable_dims": a["applicable_dims"],
                          "system": a["system"], "user": a["user"]})
    return units, na_rows


def filter_tier_subset(records, key_fn):
    """Tier 1/2 只在 TIER_SUBSET_SCENARIOS 上跑，不管来源文件本身覆盖了多少条。
    key_fn 从一条记录里取 scenario_id（生成记录和数据集记录字段名一致，直接用 'scenario_id'）。"""
    return [r for r in records if key_fn(r) in TIER_SUBSET_SCENARIOS]


def main():
    ap = argparse.ArgumentParser(description="Week 9 风控重写版 LLM-as-a-Judge runner.")
    ap.add_argument("--gen", default="results/full_gen_v1.json", help="生成 JSON 路径")
    ap.add_argument("--tier", type=int, choices=[1, 2, 3], default=None,
                    help="分级评估协议：1=单裁判10条子集试错，2=三裁判同子集确认，"
                         "3=三裁判60条全量（论文最终数据，计划内仅执行一次）。"
                         "会据此设置 --judges 默认值（显式传 --judges 可覆盖）；"
                         "tier 1/2 会自动把 --gen 过滤到 10 条 sanity 子集范围。")
    ap.add_argument("--judges", nargs="+", default=None,
                    help="不传则按 --tier 决定；两者都不传则默认三家全跑。")
    ap.add_argument("--out", default=None, help="默认 results/scores_<gen文件名>.json")
    ap.add_argument("--max-cost-eur", type=float, default=30.0,
                    help="本次跑批的预估成本硬顶。超过直接拒绝执行，没有绕过参数。")
    ap.add_argument("--daily-cap-eur", type=float, default=15.0,
                    help="按日累计（跨多次调用命令也生效）的硬顶，基于本地预算台账"
                         "（results/.budget_ledger.json）。同样没有绕过参数。")
    ap.add_argument("--balance-checked", action="store_true",
                    help="Tier 3 强制要求的人工检查点确认：登录三家平台后台核对过实时余额、"
                         "预留了 ≥1.5 倍安全边际后，才传这个参数。不传则 Tier 3 拒绝启动。")
    ap.add_argument("--sleep-sec", type=float, default=1.5,
                    help="每次调用后的强制间隔秒数（主动节流，不管成功失败都执行）。")
    ap.add_argument("--dry-run", action="store_true", help="不调 API,假分数验证管道")
    args = ap.parse_args()

    judges = args.judges or (TIER_JUDGE_DEFAULTS.get(args.tier) if args.tier else JUDGES)

    if args.tier == 3 and not args.balance_checked and not args.dry_run:
        print("❌ Tier 3 是计划内仅执行一次的全量锁定评估，启动前必须人工核对三家平台后台"
              "实时余额、预留 ≥1.5 倍预估费用的安全边际。\n"
              "   确认过后，重新加上 --balance-checked 参数再跑。")
        return

    print(f"⚠️  PRICING 仍是估算占位符，未用真实账单校准（见 run_judge.py 顶部 TODO）。"
          f"Tier 3 正式跑批前请务必先核对。")

    gen = json.loads(Path(args.gen).read_text(encoding="utf-8"))
    if args.tier in (1, 2):
        before = len(gen)
        gen = filter_tier_subset(gen, lambda r: r["scenario_id"])
        print(f"   Tier {args.tier}：已将生成记录从 {before} 条过滤到 sanity 子集范围内的 {len(gen)} 条。")

    data = {r["id"]: r for r in load_dataset()}
    units, na_rows = build_units(gen, data)
    out = Path(args.out or f"results/scores_{Path(args.gen).stem}.json")

    est = estimate_cost(units, judges)
    print(f"▶️  {len(units)} 条响应 × {len(judges)} 裁判 = {len(units)*len(judges)} 次调用"
          f"（Week 8 旧结构下同等规模约需 {len(units)*len(judges)*7} 次调用，约为本次的 7 倍）"
          f" + {len(na_rows)} 条 N/A · 预估 ≈ €{est:.2f}"
          f"（整任务估算；续跑时已完成的会跳过，不重复计费）")

    if not args.dry_run:
        ok_run, _ = (True, 0.0) if est <= args.max_cost_eur else (False, 0.0)
        if not ok_run:
            print(f"❌ 预估 €{est:.2f} > 单次跑批上限 €{args.max_cost_eur}。"
                  f"没有绕过参数——请缩小范围（更少裁判/更小子集）或在确认预算后调高 --max-cost-eur。")
            return
        ok_daily, spent_today = budget_ledger.check_daily_cap(est, args.daily_cap_eur)
        if not ok_daily:
            print(f"❌ 今日已花 ≈€{spent_today:.2f}，加上本次预估 €{est:.2f} 会超过按日硬顶 "
                  f"€{args.daily_cap_eur}。没有绕过参数——等到明天，或先去核对台账/真实账单"
                  f"是否有偏差（results/.budget_ledger.json）。")
            return

    rows, done = list(na_rows), set()
    if out.exists():                                          # 断点续跑
        prev = json.loads(out.read_text(encoding="utf-8"))
        rows = prev
        done = {(r["scenario_id"], r["condition"], r.get("geo"), r["gen_model"],
                 r["run_index"], r["dimension"], r["judge_model"]) for r in prev}
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

    actual_spend_this_run = 0.0
    n, skipped = 0, 0
    for u in units:
        for j in judges:
            # 该(响应×裁判)组合还缺哪些维度？全齐了就跳过，不重复调用。
            missing_dims = [d for d in u["applicable_dims"]
                           if (u["scenario_id"], u["condition"], u["geo"], u["gen_model"],
                               u["run_index"], d, j) not in done]
            if not missing_dims:
                continue
            n += 1
            call_cost = 0.0
            if args.dry_run:
                parsed = {d: {"markers": ["[dry]"], "score": 3, "justification": "[dry-run]"} for d in missing_dims}
            else:
                raw, err, fatal = judge_call(call_model, u["user"], u["system"], j, sleep_sec=args.sleep_sec)
                if fatal:                                     # 余额/认证 → 存盘后干净退出
                    flush()
                    budget_ledger.record(actual_spend_this_run, note=f"{out.name} (中断于硬错误)")
                    print(f"\n❌ 硬错误({j}),已存盘 {len(rows)} 行,预算台账已记录本次已发生部分。"
                          f"修复后(如充值)重跑同一条会自动续跑。\n   {err}")
                    return
                if raw is None:                               # 临时错误重试仍失败 → 跳过,下次重跑重试
                    skipped += 1
                    print(f"   ⚠️ 跳过(重跑会重试) {u['scenario_id']}/{j}: {err}")
                    continue
                parsed = parse_judge_json_multi(raw, missing_dims)
                in_tok = len(u["system"] + u["user"]) / 4
                out_tok = EST_OUTPUT_TOKENS_PER_DIM * len(missing_dims)
                p = PRICING.get(j, {"in": 2.0, "out": 8.0})
                call_cost = in_tok / 1e6 * p["in"] + out_tok / 1e6 * p["out"]
                actual_spend_this_run += call_cost

            for dim in missing_dims:
                row = {"scenario_id": u["scenario_id"], "lang": u["lang"], "condition": u["condition"],
                       "geo": u["geo"], "prompt_version": u["prompt_version"], "gen_model": u["gen_model"],
                       "run_index": u["run_index"], "dimension": dim,
                       "judge_model": j, "applicable": True, "self_judge": (j == u["gen_model"])}
                if dim in parsed:
                    row.update(parsed[dim])
                else:
                    row.update({"score": None, "markers": [], "justification": "", "parse_error": True})
                rows.append(row)

            if not args.dry_run and n % 50 == 0:              # 每 50 次落盘
                flush()
                budget_ledger.record(actual_spend_this_run, note=f"{out.name} (进行中)")
                actual_spend_this_run = 0.0
                print(f"   ...{n} 次调用已存盘（预算台账已同步累计）")

    flush()
    if not args.dry_run and actual_spend_this_run > 0:
        today_total = budget_ledger.record(actual_spend_this_run, note=f"{out.name} (完成)")
        print(f"   预算台账已更新，今日累计 ≈€{today_total:.2f}。")
    msg = f"\n✅ {len(rows)} 行(含 {len(na_rows)} N/A) → {out}"
    if skipped:
        msg += f"\n⚠️ 有 {skipped} 次因临时错误被跳过——再跑一次同一条命令会把它们补上(续跑)。"
    print(msg + f"（下一步:python -m src.eval.aggregate --scores {out}）")


if __name__ == "__main__":
    main()
