"""EmpathyLens — Week 8 full generation (被评对象,正式版).
用【锁定的 v1 prompt】把 60 条数据集 × 三家生成模型跑一遍,外加 en_geo 强基线对照,
输出 results/full_gen_v1.json,供 run_judge.py 评分。本脚本只生成,不评分。

范围:
  基础三条件 = 20 场景 × {zh,de,en} × {gpt-5.4, claude-opus-4-6, deepseek-v4-pro} = 180
  en_geo 对照 = 20 场景 × {geo=zh, geo=de} × 3 模型 = 120(母语原文输入 + 国别标签,英文响应)
  (geo=en 省略:en_geo-en ≈ 纯 en 基线,信息增量小,§4.5)

放置:src/run_full_generation.py。运行(项目根,需 .env 三家 key):
    python -m src.run_full_generation --dry-run                 # 不调 API,验证装配/schema
    python -m src.run_full_generation --models claude-opus-4-6  # 先单模型试
    python -m src.run_full_generation                           # 全量
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.dataset import load_dataset
from src.prompts.registry import load_prompt, GEO_FILL

PROMPT_VERSION = "v1"
GEN_MODELS = ["gpt-5.4", "claude-opus-4-6", "deepseek-v4-pro"]
DEFAULT_TEMPERATURE = 0.7
EN_GEO_GEOS = ["zh", "de"]   # en_geo 跑哪些源文化(每个场景都跑这些,平衡 zh/de 覆盖)


def _gen(system, user, model, temperature, dry):
    if dry:
        return "[DRY] " + user[:16], 0.0
    from src.llm_client import call_model        # 统一三家客户端(Week8 已建)
    t = time.time()
    text = call_model(prompt=user, system=system, model=model, temperature=temperature)
    return text, round(time.time() - t, 2)


def build_units(data, scenarios, en_geo_geos):
    """装配生成单元(不含模型维度)。每个 dict = 一次 (condition × scenario) 的输入。"""
    units = []
    for sid in scenarios:
        for lang in ("zh", "de", "en"):                       # 基础三条件
            rec = data[f"{sid}_{lang}"]
            units.append({"condition": lang, "scenario_id": sid, "lang": lang, "geo": None,
                          "user_text": rec["text"], "system": load_prompt(PROMPT_VERSION, lang)})
        for geo in en_geo_geos:                               # en_geo 强基线
            rec = data[f"{sid}_{geo}"]
            units.append({"condition": "en_geo", "scenario_id": sid, "lang": geo, "geo": geo,
                          "country_label": GEO_FILL[geo]["COUNTRY"], "user_text": rec["text"],
                          "system": load_prompt(PROMPT_VERSION, "en_geo", geo=geo)})
    return units


def main():
    ap = argparse.ArgumentParser(description="Week 8 full generation (v1 locked prompts).")
    ap.add_argument("--models", nargs="+", default=GEN_MODELS)
    ap.add_argument("--scenarios", nargs="+", default=None, help="限定 scenario_id,默认全 20")
    ap.add_argument("--en-geo-geos", nargs="+", default=EN_GEO_GEOS, help="en_geo 源文化,可设 [] 跳过")
    ap.add_argument("--n", type=int, default=1, help="每条重复采样次数(run_index),默认 1")
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", default="results/full_gen_v1.json")
    args = ap.parse_args()

    data = {r["id"]: r for r in load_dataset()}
    scenarios = args.scenarios or sorted({r["scenario_id"] for r in data.values()})
    units = build_units(data, scenarios, args.en_geo_geos)
    total = len(units) * len(args.models) * args.n
    print(f"▶️  {total} 次生成 = {len(units)} units × {len(args.models)} models × n={args.n}"
          f" · dry_run={args.dry_run}")

    out = Path(args.output)
    records, done = [], set()
    if out.exists() and not args.dry_run:                     # 断点续跑:跳过已生成
        records = json.loads(out.read_text(encoding="utf-8"))
        done = {(r["scenario_id"], r["condition"], r.get("geo"), r["gen_model"], r["run_index"]) for r in records}
        print(f"   断点续跑:已有 {len(records)} 条,跳过这些。")

    i = 0
    for ri in range(args.n):
        for u in units:
            for model in args.models:
                i += 1
                key = (u["scenario_id"], u["condition"], u["geo"], model, ri)
                if key in done:
                    continue
                tag = u["condition"] + (f"/{u['geo']}" if u["geo"] else "")
                print(f"[{i}/{total}] {u['scenario_id']} {tag} · {model}")
                text, latency = _gen(u["system"], u["user_text"], model, args.temperature, args.dry_run)
                rec = {
                    "prompt_version": PROMPT_VERSION, "condition": u["condition"],
                    "scenario_id": u["scenario_id"], "lang": u["lang"], "geo": u["geo"],
                    "gen_model": model, "run_index": ri,
                    "user_text": u["user_text"], "response_text": text,
                    "temperature": args.temperature, "thinking_mode": "disabled",
                    "latency_sec": latency, "char_len": len(text),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }
                if u["geo"]:
                    rec["country_label"] = u["country_label"]
                records.append(rec)
                if not args.dry_run and i % 30 == 0:           # 每 30 次落盘一次
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ {len(records)} 条 → {out}（下一步:python -m src.eval.run_judge --gen {out}）")


if __name__ == "__main__":
    main()
