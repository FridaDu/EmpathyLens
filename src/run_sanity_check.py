"""EmpathyLens — Week 7 sanity-check batch runner (generation only, NO scoring).
对 week7_sanity_check.md §1 选定的 10 个场景 × 三语 v1 + 10 条 en_geo = 40 条,跑一次生成,存
results/week7_sanity_check_v1.json,供作者逐条粗读(语言一致/格式/明显违背)。
评分是 Week 8 的事 —— 本脚本不调 judge、不打分。

放置:src/run_sanity_check.py。运行(项目根,需 .env 里的 ANTHROPIC_API_KEY):
    python -m src.run_sanity_check                      # 默认 claude-opus-4-6,40 条
    python -m src.run_sanity_check --no-geo             # 只跑 30 条(跳过 en_geo)
    python -m src.run_sanity_check --dry-run            # 不调 API,假响应,验证装配/schema
"""
from dotenv import load_dotenv
load_dotenv()

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.dataset import load_dataset
from src.prompts.registry import load_prompt, GEO_FILL

PROMPT_VERSION = "v1"
DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_TEMPERATURE = 0.7

# week7_sanity_check.md §1.2 选定的 10 条。
SANITY_SCENARIOS = ["S02", "S05", "S06", "S08", "S14", "S15", "S16", "S17", "S18", "S20"]
# en_geo 的国别标签按场景文化来源(week7_sanity_check.md 表 2.1b);geo 取语言码。
EN_GEO_SOURCE = {
    "S02": "zh", "S05": "de", "S06": "zh", "S08": "de", "S14": "zh",
    "S15": "zh", "S16": "zh", "S17": "zh", "S18": "zh", "S20": "zh",
}


def _gen(system_prompt, user_text, model, temperature, dry_run):
    """跑一次生成,返回 (response_text, 元数据 dict)。dry_run 时不调 API。"""
    if dry_run:
        return ("[DRY-RUN 假响应] " + user_text[:18],
                {"model": model, "temperature": temperature, "max_tokens": 600,
                 "thinking_mode": "disabled", "stop_reason": "end_turn",
                 "input_tokens": 0, "output_tokens": 0, "latency_sec": 0.0})
    # 复用 CLI 已建好的 Anthropic 调用(带完整元数据 + 懒加载 + key 检查)。
    from src.cli.empathy_cli import call_model
    r = call_model(system_prompt=system_prompt, user_text=user_text,
                   model=model, temperature=temperature)
    text = r.pop("response_text")
    return text, r


def build_units(include_geo=True):
    """装配评分前的'被评单元'列表(不含响应)。每个 dict 描述一次生成请求。"""
    data = {r["id"]: r for r in load_dataset()}
    units = []
    for sid in SANITY_SCENARIOS:
        for lang in ("zh", "de", "en"):                      # 三语 calibrated/baseline
            rec = data[f"{sid}_{lang}"]
            units.append({"condition": lang, "scenario_id": sid, "lang": lang,
                          "geo": None, "user_text": rec["text"],
                          "system": load_prompt(PROMPT_VERSION, lang)})
    if include_geo:
        for sid in SANITY_SCENARIOS:                         # en_geo 强基线
            geo = EN_GEO_SOURCE[sid]
            rec = data[f"{sid}_{geo}"]                       # 母语原文输入
            units.append({"condition": "en_geo", "scenario_id": sid, "lang": geo,
                          "geo": geo, "country": GEO_FILL[geo]["COUNTRY"],
                          "user_text": rec["text"],
                          "system": load_prompt(PROMPT_VERSION, "en_geo", geo=geo)})
    return units


def main():
    ap = argparse.ArgumentParser(description="Week 7 sanity-check runner (generation only).")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--no-geo", action="store_true", help="跳过 en_geo,只跑 30 条")
    ap.add_argument("--dry-run", action="store_true", help="不调 API,验证装配/schema")
    ap.add_argument("--output", default="results/week7_sanity_check_v1.json")
    args = ap.parse_args()

    units = build_units(include_geo=not args.no_geo)
    print(f"▶️  {len(units)} 条 ({'含' if not args.no_geo else '不含'} en_geo) "
          f"· model={args.model} · dry_run={args.dry_run}")

    records = []
    for i, u in enumerate(units, 1):
        tag = u["condition"] + (f"/{u['geo']}" if u["geo"] else "")
        print(f"[{i:>2}/{len(units)}] {u['scenario_id']} {tag}")
        text, meta = _gen(u["system"], u["user_text"], args.model, args.temperature, args.dry_run)
        rec = {
            "prompt_version": PROMPT_VERSION,
            "condition": u["condition"],          # zh | de | en | en_geo
            "scenario_id": u["scenario_id"],
            "lang": u["lang"],                    # 输入文本语言(en_geo 为源文化语言)
            "geo": u["geo"],                      # en_geo 的国别码,否则 None
            "user_text": u["user_text"],
            "response_text": text,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **meta,                               # model/temperature/thinking_mode/stop_reason/tokens/latency
        }
        if u["geo"]:
            rec["country_label"] = u["country"]
        records.append(rec)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 写入 {len(records)} 条 → {out}")
    print("   下一步:作者按 week7_sanity_check.md §2 逐条粗读填表。不在本脚本评分。")


if __name__ == "__main__":
    main()
