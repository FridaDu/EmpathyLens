"""EmpathyLens — fill final intensity/sensitivity into dataset_draft.json.
读两张标注表(annotations/),把值写回数据集:
  - annotation_sensitivity.csv : 场景级,一个值写进该 scenario 的 zh/de/en 三条。
  - annotation_intensity.csv   : 逐条,按 id 写。
空格自动跳过,可反复跑(填多少写多少)。每次跑完报告还差哪些。
Run (项目根): python -m src.fill_annotations
"""
import csv, json
from src.dataset import DATA_PATH, _ROOT

SENS_CSV = _ROOT / "annotations" / "annotation_sensitivity.csv"
INT_CSV = _ROOT / "annotations" / "annotation_intensity.csv"
VALID_SENS = {"high", "medium", "low"}


def _read(path, key, val):
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            v = (r.get(val) or "").strip()
            if v:
                out[(r.get(key) or "").strip()] = v
    return out


def main():
    sens = _read(SENS_CSV, "scenario_id", "sensitivity")   # {S01: high}
    inten = _read(INT_CSV, "id", "intensity")               # {S01_zh: 4}
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    n_i = n_s = 0
    blank_i, blank_scen = [], set()
    for rec in data:
        sid = rec.get("scenario_id") or rec["id"].rsplit("_", 1)[0]
        # intensity(逐条)
        if rec["id"] in inten:
            rec["emotional_intensity"] = int(inten[rec["id"]])
            n_i += 1
        else:
            blank_i.append(rec["id"])
        # sensitivity(场景级)
        if sid in sens:
            v = sens[sid].lower()
            if v not in VALID_SENS:
                print(f"⚠️ {sid} sensitivity 非法值 '{v}',跳过(应为 high/medium/low)")
            else:
                rec["cultural_sensitivity"] = v
                n_s += 1
        else:
            blank_scen.add(sid)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 写入 emotional_intensity {n_i}/60,cultural_sensitivity {n_s}/60")
    if blank_i:
        print(f"⏳ 还差 intensity({len(blank_i)} 条):", ", ".join(blank_i))
    if blank_scen:
        print(f"⏳ 还差 sensitivity({len(blank_scen)} 场景):", ", ".join(sorted(blank_scen)))
    if not blank_i and not blank_scen:
        print("🎉 60 条全部填完,跑 validate_dataset 查跨语言一致性。")


if __name__ == "__main__":
    main()
