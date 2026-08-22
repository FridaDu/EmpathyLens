"""EmpathyLens — 把评估结果导出成 BI 工具（Tableau / Power BI）可直接导入的扁平 CSV。

为什么需要这一步:评估管道的输出是嵌套 JSON(便于程序消费),但 BI 工具吃的是"一行一条
观测、列都是扁平字段"的表格。本脚本做的就是这个转换,并把数据集的场景元数据(场景类型、
文化敏感度、情感强度等)join 进来,这样在 Tableau 里可以直接按这些维度切片。

输出三份 CSV 到 results/bi/:
  1. scores_long.csv        —— 主表。一行 = (场景 × 条件 × 生成模型 × 裁判 × 维度) 的一个分数。
                                长格式(long format),Tableau 处理长格式比宽格式灵活得多。
  2. judge_median_long.csv  —— 三家裁判取中位数后的分数 + 裁判分歧度。做"最终得分"类图用这份。
  3. equitability_long.csv  —— 跨语言分差(raw / corrected),做 Equitability 相关图用这份。

⚠️ 数据质量标记(重要):Week 9 发现 en_geo 条件的 D6(语言自然度)分数是评分上下文构造错误
   导致的伪影(裁判被告知目标语言是中文/德语,但 en_geo 响应恒为英文),不是真实的语言质量。
   本脚本给每一行加了 data_quality 列,把这些行标成 "known_artifact_excluded"。
   **在 Tableau 里请务必先用 data_quality = "ok" 做筛选**,否则图表会讲一个错误的故事。
   修复后重测的数据不会带这个标记。

放置:src/viz/export_for_bi.py。运行(项目根):
    python -m src.viz.export_for_bi
    python -m src.viz.export_for_bi --scores results/scores_full_gen_v1.json
"""
import argparse
import csv
import json
from pathlib import Path

from src.dataset import load_dataset

# Week 9 已知伪影:en_geo 条件下的 D6 分数不可用(见模块 docstring)。
ARTIFACT_CONDITION_DIMS = {("en_geo", "D6")}

CONDITION_LABEL = {
    "zh": "Chinese (calibrated)",
    "de": "German (calibrated)",
    "en": "English (uncalibrated baseline)",
    "en_geo": "English + country label (strong baseline)",
}

DIMENSION_LABEL = {
    "D1": "D1 Empathy & emotion validation",
    "D2": "D2 No minimizing / no judging",
    "D3": "D3 Safety & crisis recognition",
    "D4": "D4 Cultural norm fit",
    "D5": "D5 Intention alignment",
    "D6": "D6 Language naturalness",
    "D7": "D7 Progression & tension handling",
}

DIMENSION_LAYER = {
    "D1": "Universal", "D2": "Universal", "D3": "Universal",
    "D4": "Cultural", "D5": "Cultural", "D6": "Cultural",
    "D7": "Interaction",
}


def _quality_flag(condition, dimension):
    return ("known_artifact_excluded"
            if (condition, dimension) in ARTIFACT_CONDITION_DIMS else "ok")


def _join_lang(condition, lang, geo):
    """目标文化解析:en_geo 按源文化 geo,其余按 condition(同 JUDGE_INPUT_CONTRACT §3)。"""
    return geo if condition == "en_geo" else lang


def export_scores_long(rows, data, out_path):
    """主表:一行一个 (响应 × 维度 × 裁判) 的分数,join 上场景元数据。"""
    fields = [
        "scenario_id", "scenario_type", "kind", "cultural_sensitivity",
        "emotional_intensity", "stressed_axes", "framework_anchor",
        "condition", "condition_label", "lang", "geo", "prompt_version",
        "gen_model", "judge_model", "self_judge",
        "dimension", "dimension_label", "dimension_layer",
        "score", "applicable", "data_quality", "justification",
    ]
    n = 0
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig:带 BOM,避免 Excel / Tableau 在 Windows 上把中文显示成乱码
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            ds_key = f"{r['scenario_id']}_{_join_lang(r['condition'], r['lang'], r.get('geo'))}"
            ds = data.get(ds_key, {})
            w.writerow({
                "scenario_id": r["scenario_id"],
                "scenario_type": ds.get("scenario_type", ""),
                "kind": ds.get("kind", ""),
                "cultural_sensitivity": ds.get("cultural_sensitivity", ""),
                "emotional_intensity": ds.get("emotional_intensity", ""),
                "stressed_axes": "|".join(ds.get("stressed_axes") or []),
                "framework_anchor": ds.get("framework_anchor", ""),
                "condition": r["condition"],
                "condition_label": CONDITION_LABEL.get(r["condition"], r["condition"]),
                "lang": r["lang"],
                "geo": r.get("geo") or "",
                "prompt_version": r.get("prompt_version", ""),
                "gen_model": r.get("gen_model", ""),
                "judge_model": r.get("judge_model") or "",
                "self_judge": r.get("self_judge"),
                "dimension": r["dimension"],
                "dimension_label": DIMENSION_LABEL.get(r["dimension"], r["dimension"]),
                "dimension_layer": DIMENSION_LAYER.get(r["dimension"], ""),
                "score": r.get("score") if r.get("score") is not None else "",
                "applicable": r.get("applicable"),
                "data_quality": _quality_flag(r["condition"], r["dimension"]),
                "justification": (r.get("justification") or "").replace("\n", " ")[:300],
            })
            n += 1
    return n


def export_median_long(agg, data, out_path):
    """三家裁判中位数 + 分歧度。做"最终得分"类图表用这份(避免同一响应被三家裁判重复计数)。"""
    fields = [
        "scenario_id", "scenario_type", "kind", "cultural_sensitivity",
        "condition", "condition_label", "lang", "gen_model",
        "dimension", "dimension_label", "dimension_layer",
        "median_score", "judge_disagreement", "high_disagreement",
        "n_judges", "data_quality",
    ]
    n = 0
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for u in agg.get("units", []):
            ds_key = f"{u['scenario_id']}_{_join_lang(u['condition'], u['lang'], u.get('geo'))}"
            ds = data.get(ds_key, {})
            w.writerow({
                "scenario_id": u["scenario_id"],
                "scenario_type": ds.get("scenario_type", ""),
                "kind": ds.get("kind", ""),
                "cultural_sensitivity": ds.get("cultural_sensitivity", ""),
                "condition": u["condition"],
                "condition_label": CONDITION_LABEL.get(u["condition"], u["condition"]),
                "lang": u["lang"],
                "gen_model": u["gen_model"],
                "dimension": u["dimension"],
                "dimension_label": DIMENSION_LABEL.get(u["dimension"], u["dimension"]),
                "dimension_layer": DIMENSION_LAYER.get(u["dimension"], ""),
                "median_score": u["median"],
                "judge_disagreement": u["disagreement"],
                "high_disagreement": u["high_disagreement"],
                "n_judges": u["n_judges"],
                "data_quality": _quality_flag(u["condition"], u["dimension"]),
            })
            n += 1
    return n


def export_equitability_long(eq, out_path):
    """Equitability:每 (模型 × 维度 × 语言对) 一行,含 raw / corrected 分差。"""
    fields = ["gen_model", "dimension", "dimension_label", "compare",
              "raw_gap", "corrected_gap", "n_scenarios",
              "ability_baseline_zh", "ability_baseline_de",
              "total_index_zh", "total_index_de", "data_quality"]
    n = 0
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for model, r in eq.items():
            base = r.get("ability_baseline", {})
            total = r.get("total_equitability_index", {})
            for d in r.get("per_dimension", []):
                w.writerow({
                    "gen_model": model,
                    "dimension": d["dimension"],
                    "dimension_label": DIMENSION_LABEL.get(d["dimension"], d["dimension"]),
                    "compare": d["compare"],
                    "raw_gap": d["raw_gap"],
                    "corrected_gap": d["corrected_gap"],
                    "n_scenarios": d["n_scenarios"],
                    "ability_baseline_zh": base.get("zh"),
                    "ability_baseline_de": base.get("de"),
                    "total_index_zh": total.get("zh"),
                    "total_index_de": total.get("de"),
                    # Equitability 只在 zh/de/en 上计算,不含 en_geo,不受该伪影影响
                    "data_quality": "ok",
                })
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description="导出 BI 工具可用的扁平 CSV。")
    ap.add_argument("--scores", default="results/scores_full_gen_v1.json")
    ap.add_argument("--outdir", default="results/bi")
    args = ap.parse_args()

    stem = Path(args.scores).stem.replace("scores_", "")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    data = {r["id"]: r for r in load_dataset()}
    rows = json.loads(Path(args.scores).read_text(encoding="utf-8"))

    n1 = export_scores_long(rows, data, outdir / "scores_long.csv")
    print(f"✅ 主表        {n1:>5} 行 → {outdir/'scores_long.csv'}")

    agg_path = Path(f"results/scores_agg_{stem}.json")
    if agg_path.exists():
        agg = json.loads(agg_path.read_text(encoding="utf-8"))
        n2 = export_median_long(agg, data, outdir / "judge_median_long.csv")
        print(f"✅ 裁判中位数  {n2:>5} 行 → {outdir/'judge_median_long.csv'}")
    else:
        print(f"⚠️  找不到 {agg_path},跳过中位数表(先跑 python -m src.eval.aggregate)")

    eq_path = Path(f"results/equitability_{stem}.json")
    if eq_path.exists():
        eq = json.loads(eq_path.read_text(encoding="utf-8"))
        n3 = export_equitability_long(eq, outdir / "equitability_long.csv")
        print(f"✅ Equitability {n3:>4} 行 → {outdir/'equitability_long.csv'}")
    else:
        print(f"⚠️  找不到 {eq_path},跳过 Equitability 表")

    print("\n📊 下一步:在 Tableau 里连接这些 CSV。")
    print("   ⚠️ 记得先加筛选器 data_quality = \"ok\",排除 en_geo 的 D6 已知伪影。")


if __name__ == "__main__":
    main()
