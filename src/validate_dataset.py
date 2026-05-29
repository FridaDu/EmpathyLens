"""EmpathyLens — dataset validator (Week 5, schema locked). Run: python -m src.validate_dataset"""
from collections import Counter, defaultdict
from src.dataset import (load_dataset, LANGS, KINDS, SENSITIVITY, MISMATCH_CODES, INTENSITY_RANGE)

REQUIRED = ["scenario_id","id","lang","scenario_type","kind","cultural_sensitivity",
            "stressed_axes","framework_anchor","text","emotional_intensity","cultural_cue",
            "ideal_norm_direction","ideal_intention","watch_mismatches","author",
            "native_reviewed","note"]
SCENARIO_LEVEL = ["scenario_type","kind","stressed_axes","framework_anchor"]

def validate():
    data = load_dataset()
    errors, warnings = [], []
    lo, hi = INTENSITY_RANGE

    for id_, n in Counter(r.get("id") for r in data).items():
        if n > 1: errors.append(f"duplicate id: {id_}")

    by_scenario = defaultdict(list)
    for r in data:
        rid = r.get("id","<no-id>")
        for f in REQUIRED:
            if f not in r: errors.append(f"{rid}: missing field '{f}'")
        if r.get("lang") not in LANGS: errors.append(f"{rid}: bad lang {r.get('lang')}")
        if r.get("kind") not in KINDS: errors.append(f"{rid}: bad kind {r.get('kind')}")
        if not r.get("text"): warnings.append(f"{rid}: text 未填")
        sens = r.get("cultural_sensitivity")
        if not sens: warnings.append(f"{rid}: sensitivity 未填(Kappa 后回填)")
        elif sens not in SENSITIVITY: errors.append(f"{rid}: bad sensitivity {sens}")
        inten = r.get("emotional_intensity")
        if inten in (None, ""): warnings.append(f"{rid}: intensity 未填")
        elif not (isinstance(inten, int) and lo <= inten <= hi):
            errors.append(f"{rid}: intensity {inten} 不在 {lo}-{hi}")
        for c in r.get("watch_mismatches", []):
            if c not in MISMATCH_CODES: warnings.append(f"{rid}: unknown mismatch {c}")
        if r.get("lang") in ("de","en") and not r.get("native_reviewed"):
            warnings.append(f"{rid}: native_reviewed=False(定稿前需母语者复核)")
        by_scenario[r.get("scenario_id")].append(r)

    for sid, recs in by_scenario.items():
        langs = sorted(x.get("lang") for x in recs)
        if langs != ["de","en","zh"]:
            errors.append(f"{sid}: langs={langs}(需 zh/de/en 各一)")
        for f in SCENARIO_LEVEL:
            if len({repr(x.get(f)) for x in recs}) > 1:
                errors.append(f"{sid}: 场景级字段 '{f}' 三语不一致")
        ints = [x.get("emotional_intensity") for x in recs if isinstance(x.get("emotional_intensity"), int)]
        if len(ints) >= 2 and max(ints) - min(ints) > 1:
            warnings.append(f"{sid}: 三语 intensity 相差 >1 档 {ints} — 检查烈度可比性")

    for lang in LANGS:
        adv = sum(1 for r in data if r.get("lang")==lang and str(r.get("kind","")).startswith("adversarial"))
        if adv < 2: errors.append(f"{lang}: 仅 {adv} 条对抗(需 ≥2)")

    print(f"Loaded {len(data)} records, {len(by_scenario)} scenarios.")
    if errors:
        print(f"\n❌ {len(errors)} ERROR(S):"); [print("  -", e) for e in errors]
    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for w in warnings[:20]: print("  -", w)
        if len(warnings) > 20: print(f"  ... +{len(warnings)-20} more")
    if not errors: print("\n✅ 结构检查通过(warnings 多为未填字段,正常)。")
    return not errors

if __name__ == "__main__":
    validate()