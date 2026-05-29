"""EmpathyLens — generate BLANK Kappa annotation sheets (Week 5, 盲标)
intensity / sensitivity 留空,两人独立填,不看草拟值。Run: python -m src.make_kappa_sheets"""
import csv
from src.dataset import load_dataset, _ROOT

# 10 条试标:两人都是中文母语,用 zh 版(理解力对等)。覆盖 high/medium/low + 对抗。可改。
PILOT_IDS = ["S01_zh","S05_zh","S07_zh","S08_zh","S12_zh",
             "S14_zh","S15_zh","S16_zh","S17_zh","S20_zh"]
OUT_DIR = _ROOT / "annotations"

def main():
    by_id = {r["id"]: r for r in load_dataset()}
    OUT_DIR.mkdir(exist_ok=True)
    rows = [{"id": i, "text": by_id[i]["text"], "intensity": "", "sensitivity": ""}
            for i in PILOT_IDS if i in by_id]
    for who in ["frida", "helena"]:
        p = OUT_DIR / f"{who}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id","text","intensity","sensitivity"])
            w.writeheader(); w.writerows(rows)
        print(f"✅ {p}({len(rows)} 条)")
    print("提醒:两人独立、盲标 intensity(1–5)+ sensitivity(high/medium/low),不商量、不看 JSON 草拟值。")

if __name__ == "__main__":
    main()