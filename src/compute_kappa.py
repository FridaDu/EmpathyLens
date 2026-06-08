"""EmpathyLens — inter-annotator Kappa (Week 5).
读两份盲标 CSV(列: id, text, intensity, sensitivity),算:
  - emotional_intensity : 二次加权 Cohen's Kappa(有序 1–5,相邻分歧惩罚轻)
  - cultural_sensitivity: 普通 Cohen's Kappa(无序 high/medium/low)
并列出双方分歧的条目(供 reconcile)。
Run: python -m src.compute_kappa annotations/frida.csv annotations/helena.csv
依赖: pip install scikit-learn
"""
import csv, sys
from sklearn.metrics import cohen_kappa_score


def load(path):
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def interp(k):
    if k < 0.2: return "poor"
    if k < 0.4: return "fair"
    if k < 0.6: return "moderate"
    if k < 0.8: return "substantial ✅"
    return "almost perfect ✅"


def main(p1, p2):
    a, b = load(p1), load(p2)
    n1, n2 = p1.split("/")[-1], p2.split("/")[-1]
    ids = [i for i in a if i in b]
    if not ids:
        print("❌ 两份表没有共同 id,检查文件。"); return

    int_a, int_b, sen_a, sen_b = [], [], [], []
    int_dis, sen_dis = [], []
    for i in ids:
        ia, ib = a[i].get("intensity", "").strip(), b[i].get("intensity", "").strip()
        if ia and ib:
            int_a.append(int(ia)); int_b.append(int(ib))
            if ia != ib: int_dis.append((i, ia, ib))
        sa = a[i].get("sensitivity", "").strip().lower()
        sb = b[i].get("sensitivity", "").strip().lower()
        if sa and sb:
            sen_a.append(sa); sen_b.append(sb)
            if sa != sb: sen_dis.append((i, sa, sb))

    print(f"配对 {len(ids)} 条 (intensity 双方都填 {len(int_a)} 条, sensitivity {len(sen_a)} 条)\n")
    if len(int_a) >= 2:
        k = cohen_kappa_score(int_a, int_b, weights="quadratic")
        print(f"emotional_intensity  (加权 Kappa): {k:.3f}  [{interp(k)}]")
    else:
        print("emotional_intensity: 数据不足(<2 条双方都填)")
    if len(sen_a) >= 2:
        k = cohen_kappa_score(sen_a, sen_b)
        print(f"cultural_sensitivity (Cohen's Kappa): {k:.3f}  [{interp(k)}]")
    else:
        print("cultural_sensitivity: 数据不足(<2 条双方都填)")

    if int_dis:
        print(f"\n强度分歧 {len(int_dis)} 条:")
        for i, x, y in int_dis: print(f"  {i}: {n1}={x}  {n2}={y}")
    if sen_dis:
        print(f"敏感度分歧 {len(sen_dis)} 条:")
        for i, x, y in sen_dis: print(f"  {i}: {n1}={x}  {n2}={y}")
    print("\n(分歧条 = reconcile 时一起讨论、定最终值的对象。)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python -m src.compute_kappa <a.csv> <b.csv>"); sys.exit()
    main(sys.argv[1], sys.argv[2])
