"""EmpathyLens — generate BLANK Kappa annotation sheets (Week 5, 盲标).
v1.1: 15 条 = 首轮 10 条(校准新定义)+ 新增 5 条未标过的 zh(防记忆效应)。
不覆盖已存在的文件(保护上一轮数据)。
Run (项目根):
    python -m src.make_kappa_sheets          # 写 annotations/frida.csv, helena.csv
    python -m src.make_kappa_sheets _r2       # 第二轮:写 frida_r2.csv, helena_r2.csv
"""
import csv, sys
from src.dataset import load_dataset, _ROOT

# 首轮 10 条 + 新增 5 条(S02/S04/S06/S11/S18:首轮未碰,含一条 direct 对抗 S18)
PILOT_IDS = ["S01_zh", "S05_zh", "S07_zh", "S08_zh", "S12_zh",
             "S14_zh", "S15_zh", "S16_zh", "S17_zh", "S20_zh",
             "S02_zh", "S04_zh", "S06_zh", "S11_zh", "S18_zh"]
OUT_DIR = _ROOT / "annotations"


def main(suffix=""):
    by_id = {r["id"]: r for r in load_dataset()}
    OUT_DIR.mkdir(exist_ok=True)
    missing = [i for i in PILOT_IDS if i not in by_id]
    if missing:
        print("⚠️ 数据集里找不到这些 id:", missing)
    rows = [{"id": i, "text": by_id[i]["text"], "intensity": "", "sensitivity": ""}
            for i in PILOT_IDS if i in by_id]
    for who in ["frida", "helena"]:
        p = OUT_DIR / f"{who}{suffix}.csv"
        if p.exists():
            print(f"✋ {p} 已存在,不覆盖(保护上一轮)。换 suffix 或先删它。")
            continue
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "text", "intensity", "sensitivity"])
            w.writeheader(); w.writerows(rows)
        print(f"✅ {p}({len(rows)} 条)")
    print("提醒:两人独立、盲标 intensity(1–5)+ sensitivity(high/medium/low);不商量、不看草拟值/设计表。")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
