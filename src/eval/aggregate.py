"""EmpathyLens — Week 8 score aggregation + Equitability.
从 run_judge 的 scores JSON 算:
  (a) 每 (响应×维) 三家裁判中位数 + 分歧度(max-min),分歧>1 打标;
  (b) self-vs-cross 双套聚合(落地 Week6 自评偏差决策);
  (c) (gen_model × condition × dim) 均分矩阵(给可视化);
  (d) Equitability:per-dim 带符号分差 + 总指数 mean(|分差|),D1/D2 池化能力基线扣除,
      输出 raw_gap / corrected_gap;排除 S14 的 D3、S19 的 D4/D5。

放置:src/eval/aggregate.py。运行:
    python -m src.eval.aggregate --scores results/scores_full_gen_v1.json
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median, mean, pstdev

from src.eval.rubrics import DIMENSION_ORDER, D3_CROSS_LANG_INCOMPARABLE, CULTURE_INVARIANT_SCENARIOS

BASE_LANGS = ("zh", "de", "en")          # Equitability 只在基础三条件上算(不含 en_geo)
ABILITY_DIMS = ("D1", "D2")              # 文化无关维,用于池化能力基线
ABILITY_SCENARIOS = ("S15", "S16")       # 低敏感度对照条


def _unit_key(r):
    return (r["gen_model"], r["condition"], r.get("geo"), r["scenario_id"],
            r["lang"], r["run_index"], r["dimension"])


def cross_judge_medians(rows):
    """(a) 把同一 (响应×维) 的多家裁判分数合成中位数 + 分歧度。返回 unit 列表。"""
    buckets = defaultdict(list)
    for r in rows:
        if r.get("applicable") and isinstance(r.get("score"), int):
            buckets[_unit_key(r)].append(r["score"])
    units = []
    for k, scores in buckets.items():
        gm, cond, geo, sid, lang, ri, dim = k
        units.append({"gen_model": gm, "condition": cond, "geo": geo, "scenario_id": sid,
                      "lang": lang, "run_index": ri, "dimension": dim,
                      "median": median(scores), "disagreement": max(scores) - min(scores),
                      "n_judges": len(scores), "high_disagreement": (max(scores) - min(scores)) > 1})
    return units


def self_vs_cross(rows):
    """(b) 自评 vs 互评:按 (gen_model, condition, dim, self_judge) 算均值/方差。"""
    buckets = defaultdict(list)
    for r in rows:
        if r.get("applicable") and isinstance(r.get("score"), int) and r.get("self_judge") is not None:
            buckets[(r["gen_model"], r["condition"], r["dimension"], r["self_judge"])].append(r["score"])
    out = []
    for (gm, cond, dim, selfj), s in buckets.items():
        out.append({"gen_model": gm, "condition": cond, "dimension": dim,
                    "self_judge": selfj, "mean": round(mean(s), 3),
                    "std": round(pstdev(s), 3) if len(s) > 1 else 0.0, "n": len(s)})
    return out


def matrix(units):
    """(c) (gen_model × condition × dim) 均分(对 scenario/run 取均值的中位数)。"""
    buckets = defaultdict(list)
    for u in units:
        buckets[(u["gen_model"], u["condition"], u["dimension"])].append(u["median"])
    return [{"gen_model": gm, "condition": cond, "dimension": dim,
             "mean_score": round(mean(v), 3), "n": len(v)}
            for (gm, cond, dim), v in buckets.items()]


def _score_map(units):
    """(model, lang, dim, scenario) -> 对 run 取均值的中位数(仅基础三条件)。"""
    tmp = defaultdict(list)
    for u in units:
        if u["condition"] in BASE_LANGS:        # lang == condition for base
            tmp[(u["gen_model"], u["condition"], u["dimension"], u["scenario_id"])].append(u["median"])
    return {k: mean(v) for k, v in tmp.items()}


def _excluded(dim, sid):
    """该 (dim, scenario) 是否排除出文化分差(S14 的 D3 不可比;S19 的 D4/D5 culture-invariant)。"""
    if dim == "D3" and sid in D3_CROSS_LANG_INCOMPARABLE:
        return True
    if dim in ("D4", "D5") and sid in CULTURE_INVARIANT_SCENARIOS:
        return True
    return False


def equitability(units):
    """(d) 池化基线 Equitability。对每个 gen_model:
       raw_gap(D,lang) = mean_scenario[ S(en) - S(lang) ];
       ability_baseline(lang) = mean over D1/D2 × S15/S16 of [S(en)-S(lang)];
       corrected = raw - baseline;总指数 = mean(|corrected|) over dims。lang ∈ {zh,de}。"""
    sm = _score_map(units)
    models = sorted({k[0] for k in sm})
    result = {}
    for m in models:
        # 能力基线
        baseline = {}
        for lang in ("zh", "de"):
            diffs = [sm[(m, "en", d, s)] - sm[(m, lang, d, s)]
                     for d in ABILITY_DIMS for s in ABILITY_SCENARIOS
                     if (m, "en", d, s) in sm and (m, lang, d, s) in sm]
            baseline[lang] = round(mean(diffs), 3) if diffs else None
        per_dim, totals = [], {"zh": [], "de": []}
        for dim in DIMENSION_ORDER:
            for lang in ("zh", "de"):
                scen = [s for (mm, ln, d, s) in sm
                        if mm == m and ln == "en" and d == dim and (m, lang, dim, s) in sm
                        and not _excluded(dim, s)]
                diffs = [sm[(m, "en", dim, s)] - sm[(m, lang, dim, s)] for s in scen]
                if not diffs:
                    continue
                raw = mean(diffs)
                base = baseline.get(lang)
                corrected = (raw - base) if base is not None else None
                per_dim.append({"dimension": dim, "compare": f"en-{lang}",
                                "raw_gap": round(raw, 3),
                                "corrected_gap": round(corrected, 3) if corrected is not None else None,
                                "n_scenarios": len(diffs)})
                if corrected is not None:
                    totals[lang].append(abs(corrected))
        result[m] = {
            "ability_baseline": baseline,
            "per_dimension": per_dim,
            "total_equitability_index": {  # mean(|corrected gap|),越小越公平
                lang: round(mean(v), 3) if v else None for lang, v in totals.items()},
        }
    return result


def main():
    ap = argparse.ArgumentParser(description="Week 8 score aggregation + Equitability.")
    ap.add_argument("--scores", default="results/scores_full_gen_v1.json")
    ap.add_argument("--out-agg", default=None)
    ap.add_argument("--out-eq", default=None)
    args = ap.parse_args()

    rows = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    stem = Path(args.scores).stem.replace("scores_", "")
    out_agg = Path(args.out_agg or f"results/scores_agg_{stem}.json")
    out_eq = Path(args.out_eq or f"results/equitability_{stem}.json")

    units = cross_judge_medians(rows)
    agg = {"units": units, "self_vs_cross": self_vs_cross(rows), "matrix": matrix(units),
           "high_disagreement_units": [u for u in units if u["high_disagreement"]]}
    eq = equitability(units)

    out_agg.parent.mkdir(parents=True, exist_ok=True)
    out_agg.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    out_eq.write_text(json.dumps(eq, ensure_ascii=False, indent=2), encoding="utf-8")
    nd = len(agg["high_disagreement_units"])
    print(f"✅ 聚合 {len(units)} units → {out_agg}（高分歧 {nd} 条）")
    print(f"✅ Equitability {len(eq)} 模型 → {out_eq}")
    for m, r in eq.items():
        print(f"   {m}: total_index={r['total_equitability_index']} baseline={r['ability_baseline']}")


if __name__ == "__main__":
    main()
