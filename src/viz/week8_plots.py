"""EmpathyLens — Week 8 visualization (Pandas + Matplotlib).
读 scores_<run>.json + scores_agg_<run>.json + equitability_<run>.json,出 5 张图存 results/figures/:
  1 score_distribution.png    每 (condition × dim) 分数 box plot
  2 judge_agreement.png       (dim × condition) 平均裁判分歧热图
  3 crosslang_gap.png         跨语言分差 raw vs corrected(条形)
  4 self_vs_cross.png         自评 vs 互评均分对照
  5 condition_radar.png       (gen_model × condition) 七维均分雷达

放置:src/viz/week8_plots.py。运行:
    python -m src.viz.week8_plots --scores results/scores_full_gen_v1.json
依赖:pandas, matplotlib, numpy(pip install --break-system-packages pandas matplotlib)。
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                    # 无显示环境也能存图
import matplotlib.pyplot as plt

from src.eval.rubrics import DIMENSION_ORDER


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def plot_score_distribution(rows, figdir):
    df = pd.DataFrame([r for r in rows if r.get("applicable") and isinstance(r.get("score"), int)])
    if df.empty:
        return
    conds = [c for c in ("zh", "de", "en", "en_geo") if c in df["condition"].unique()]
    fig, axes = plt.subplots(1, len(conds), figsize=(4 * len(conds), 4), sharey=True)
    if len(conds) == 1:
        axes = [axes]
    for ax, cond in zip(axes, conds):
        sub = df[df["condition"] == cond]
        data = [sub[sub["dimension"] == d]["score"].values for d in DIMENSION_ORDER]
        ax.boxplot(data, labels=DIMENSION_ORDER)
        ax.set_title(cond); ax.set_ylim(0.5, 5.5); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Score distribution by condition × dimension")
    fig.tight_layout(); fig.savefig(figdir / "score_distribution.png", dpi=130); plt.close(fig)


def plot_judge_agreement(units, figdir):
    df = pd.DataFrame(units)
    if df.empty:
        return
    piv = df.pivot_table(index="dimension", columns="condition", values="disagreement", aggfunc="mean")
    piv = piv.reindex(DIMENSION_ORDER)
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(piv.values, cmap="Reds", aspect="auto", vmin=0)
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, label="mean disagreement (max-min)")
    ax.set_title("Inter-judge disagreement"); fig.tight_layout()
    fig.savefig(figdir / "judge_agreement.png", dpi=130); plt.close(fig)


def plot_crosslang_gap(eq, figdir):
    recs = []
    for m, r in eq.items():
        for d in r["per_dimension"]:
            recs.append({"model": m, **d})
    df = pd.DataFrame(recs)
    if df.empty:
        return
    fig, axes = plt.subplots(1, len(eq), figsize=(5 * len(eq), 4), squeeze=False)
    for ax, (m, _) in zip(axes[0], eq.items()):
        sub = df[df["model"] == m]
        x = np.arange(len(sub)); w = 0.38
        ax.bar(x - w/2, sub["raw_gap"], w, label="raw")
        ax.bar(x + w/2, sub["corrected_gap"].fillna(0), w, label="corrected")
        ax.set_xticks(x); ax.set_xticklabels(sub["dimension"] + "\n" + sub["compare"], fontsize=7)
        ax.axhline(0, color="k", lw=0.6); ax.set_title(m); ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Cross-language gap (en − zh/de): raw vs ability-corrected")
    fig.tight_layout(); fig.savefig(figdir / "crosslang_gap.png", dpi=130); plt.close(fig)


def plot_self_vs_cross(svc, figdir):
    df = pd.DataFrame(svc)
    if df.empty:
        return
    g = df.groupby(["condition", "self_judge"])["mean"].mean().unstack()
    fig, ax = plt.subplots(figsize=(6, 4))
    g.plot(kind="bar", ax=ax)
    ax.set_ylabel("mean score"); ax.set_title("Self vs cross judging (by condition)")
    ax.legend(["cross (False)", "self (True)"]); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(figdir / "self_vs_cross.png", dpi=130); plt.close(fig)


def plot_condition_radar(mat, figdir):
    df = pd.DataFrame(mat)
    if df.empty:
        return
    angles = np.linspace(0, 2 * np.pi, len(DIMENSION_ORDER), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
    for (gm, cond), sub in df.groupby(["gen_model", "condition"]):
        s = sub.set_index("dimension")["mean_score"].reindex(DIMENSION_ORDER).fillna(0).tolist()
        s += s[:1]
        ax.plot(angles, s, label=f"{gm}/{cond}", lw=1)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(DIMENSION_ORDER)
    ax.set_ylim(0, 5); ax.set_title("Mean score radar (gen_model × condition)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=6)
    fig.tight_layout(); fig.savefig(figdir / "condition_radar.png", dpi=130); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Week 8 plots.")
    ap.add_argument("--scores", default="results/scores_full_gen_v1.json")
    ap.add_argument("--figdir", default="results/figures")
    args = ap.parse_args()
    stem = Path(args.scores).stem.replace("scores_", "")
    rows = _load(args.scores)
    agg = _load(f"results/scores_agg_{stem}.json")
    eq = _load(f"results/equitability_{stem}.json")
    figdir = Path(args.figdir); figdir.mkdir(parents=True, exist_ok=True)

    plot_score_distribution(rows, figdir)
    plot_judge_agreement(agg["units"], figdir)
    plot_crosslang_gap(eq, figdir)
    plot_self_vs_cross(agg["self_vs_cross"], figdir)
    plot_condition_radar(agg["matrix"], figdir)
    print(f"✅ 5 张图 → {figdir}/")


if __name__ == "__main__":
    main()
