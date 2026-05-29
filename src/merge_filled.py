"""EmpathyLens — merge filled entries into the skeleton (Week 5)
按 id 把写好的某语言条目 merge 进 data/dataset_draft.json。
Run: python -m src.merge_filled data/dataset_zh_de_filled_v1.json"""
import json, sys
from src.dataset import DATA_PATH, load_dataset

def main():
    if len(sys.argv) < 2:
        print("用法: python -m src.merge_filled <filled.json>"); return
    by_id = {r["id"]: r for r in load_dataset()}     # 骨架(或已部分 merge)
    filled = json.load(open(sys.argv[1], encoding="utf-8"))
    n = 0
    for r in filled:
        if r["id"] in by_id:
            by_id[r["id"]] = r; n += 1
        else:
            print(f"⚠️  {r['id']} 不在骨架里,跳过(检查 scenario_id/lang)")
    DATA_PATH.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"✅ merge 了 {n} 条,写回 {DATA_PATH}(共 {len(by_id)} 条)")

if __name__ == "__main__":
    main()