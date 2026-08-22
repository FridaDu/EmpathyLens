# EmpathyLens

**Cross-cultural evaluation infrastructure for LLM outputs — Chinese · German · English**

*跨文化 LLM 输出评估基础设施（中 / 德 / 英）*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-Phase%202%20(Stage%209%2F22)-orange)]()
[![Providers](https://img.shields.io/badge/LLM%20providers-OpenAI%20%7C%20Anthropic%20%7C%20DeepSeek-4B32C3)]()
[![Dashboard](https://img.shields.io/badge/Tableau-interactive%20dashboard-E97627?logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/feifan.du/viz/EmpathyLensCross-CulturalEvaluation/1)

**Authors:** Frida Du (Feifan Du) · Helena Cai (Xinyan Cai) — LMU Munich, B.Sc. Computational Linguistics

---

## In one minute

Consumer AI companionship products are trained mostly on English data, then deployed into markets
where the norms of *good emotional support* differ substantially. This project builds the
infrastructure to **measure that mismatch reliably** — a trilingual test set, a 7-dimension rubric
as code, and a reference-free LLM-as-a-Judge pipeline that runs under enforced cost controls.

| | |
|---|---|
| **Dataset** | 60 items · 20 scenarios × zh/de/en · natively authored, not translated |
| **Evaluation** | 7 dimensions × 3 judge models, reference-free (no gold answers) |
| **Scale so far** | 300 responses × 4 prompt conditions → **6,210 scored data points** |
| **Explore it** | 📊 **[Interactive Tableau dashboard →](https://public.tableau.com/app/profile/feifan.du/viz/EmpathyLensCross-CulturalEvaluation/1)** |

---

## Project status

| Phase | Stages | Focus | Status |
|---|---|---|---|
| 1 · Foundations | 1–6 | Research design, MVP, test set, rubric | ✅ Complete |
| 2 · Technical core | 7–15 | Prompts, evaluation pipeline, retrieval, BI, demo | 🔄 **Stage 9** — risk-control rebuild |
| 3 · Product & writing | 16–22 | Public deployment, paper, preprint | ⏳ Planned |

**Done:** trilingual dataset · 7-dimension rubric · tri-provider client · full evaluation pipeline ·
first complete scoring run · tiered cost-control protocol · interactive dashboard
**Next:** prompt v2 iteration (Stage 9) → lightweight retrieval (10) → statistical analysis (11) →
commercial product audit (12) → **locked full evaluation (13)** → demo (15) → paper (17–19)

---

## The problem

American-mainstream emotional support tends toward explicit validation, fairly rapid positive
reframing, and actionable advice. German norms lean toward **acknowledging the negative** before
offering any silver lining. Chinese norms often prioritize **presence over action**, and relational
rather than individualist attribution.

A model that applies the first pattern to all three audiences isn't neutral — it is systematically
mismatched, in a domain where mismatch carries real cost. This connects directly to
**EU AI Act Article 15** (accuracy and robustness of high-risk AI systems): robustness that holds
only for English-language inputs is not robustness.

---

## What's built

| Component | What it does |
|---|---|
| **Trilingual test set** | 20 scenarios × zh/de/en, natively authored; covers mild venting / adversarial / control / crisis, with per-item cultural metadata |
| **Rubric as code** | `eval/rubrics.py` — 7 dimensions + a closed 14-token intention taxonomy, machine-readable rather than prose-only |
| **Judge pipeline** | `eval/run_judge.py` — reference-free scoring across 3 judge models, with self-vs-cross-judgment bias reporting |
| **Tri-provider client** | `llm_client.py` — one interface over OpenAI / Anthropic / DeepSeek, plus real token-usage reporting |
| **Cost-control protocol** | Tiered runs, non-bypassable budget caps, active throttling, code-enforced manual checkpoints |
| **Reproducible data pipeline** | Schema validation + Cohen's κ inter-rater reliability, fully scripted |
| **BI export + dashboard** | `viz/export_for_bi.py` → flat CSVs → interactive Tableau dashboard |

---

## What the data shows

> ⚠️ **Directional, not conclusive.** Single-sample generation (N=1), no significance testing yet,
> one prompt version. The locked full evaluation these claims stand or fall on is Stage 13.

**A country label is not a substitute for cultural calibration.** Adding *"the person lives in
China"* to an English prompt scores **3.11 / 5** on cultural norm fit, against **4.76** for a
properly calibrated Chinese prompt. The same gap appears in intention alignment (3.24 vs 4.63).

**But the universal dimensions hold up.** Empathy, non-judgment, and crisis recognition score
4.5–4.9 across *all* conditions. Only the culture-dependent dimensions collapse — which is what
makes this a cultural-mismatch finding rather than a general capability finding.

**The weakest behaviour isn't where we expected.** D7 (progression & tension handling) is the
weakest dimension overall. Splitting it by scenario type:

| Scenario type | D7 score |
|---|---|
| Mild venting | 3.95 |
| *Direct* pushback — "you're just a machine" | 3.87 |
| *Indirect* withdrawal — "never mind, you wouldn't get it" | **3.03** |

Models handle being challenged head-on — the prompts explicitly cover that. What they miss is a
user quietly closing the conversation, which the prompts never named.

**Judges disagree most exactly where scores are lowest.** The country-label condition has both the
lowest scores *and* the highest inter-judge disagreement (up to 1.73 points). That could mean its
outputs land in an ambiguous middle ground — or that our rubric is underspecified for it. The
current data can't distinguish these, and saying so is part of the finding.

---

## Engineering highlights

**Caught a measurement artifact before it became a published result.**
One condition scored 1.43/5 on language naturalness versus 4.5–4.9 elsewhere — a dramatic-looking
result. It was ours, not the model's: the judge was told the target language was Chinese/German,
while that condition's responses are always English by design. Root cause was conflating two
fields — *the language the response is in* (governs naturalness) versus *the cultural norm it's
judged against* (governs cultural fit). Fixed, assertion-tested, and contamination scope traced
explicitly: cultural-fit dimensions were unaffected, and the Equitability metric never ingested
the condition at all.

**Rebuilt the pipeline after a budget failure.**
The first full run issued 300 generation + 6,165 judge calls and exhausted the API budget faster
than the pipeline's own estimator predicted. Four root causes: the judge was invoked once per
*(response × dimension × judge)* — 21 calls per response; pricing was hard-coded and never
reconciled against invoices; the budget cap could be overridden with a flag; and back-off only
existed *after* an error. The fix was structural — judge calls now return all dimensions in one
JSON response, cutting volume to **~1/7** while reproducing an identical 6,210-row output schema
with **zero downstream changes**. Budget caps became non-bypassable per-run and per-day, backed by
a ledger using provider-reported token counts. A side benefit: user disclosures, including
crisis-scenario items, were previously embedded up to 21 times per response in outbound requests —
now 3.

*Both are documented rather than quietly rewritten out of the commit history. An evaluation
framework nobody can afford to run twice isn't reusable, and a measurement artifact you don't catch
becomes a published mistake.*

---

## Quick start

```bash
git clone https://github.com/FridaDu/EmpathyLens.git && cd EmpathyLens
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your OPENAI / ANTHROPIC / DEEPSEEK keys
```

**Verify the dataset and rubric — no API calls, no cost:**

```bash
python -m src.validate_dataset           # 60 records, schema check → expect 0 errors
python -m src.eval.rubrics               # 7 dimensions + 14-token intention taxonomy
python -m src.eval.assemble_judge_input  # judge-input assembler self-test
```

**Generate responses across the three cultural modes:**

```bash
python -m src.cli.empathy_cli --text "我妈又催我相亲了,烦死了。"
```

**Run the evaluation pipeline — tiered by cost:**

```bash
# Tier 1 — single judge, 10-item subset: run this first after any prompt change
python -m src.eval.run_judge --tier 1 --gen results/week7_sanity_check_v1.json

# Tier 2 — three judges, same subset: quantitative confirmation
python -m src.eval.run_judge --tier 2 --gen results/week7_sanity_check_v1.json

# Tier 3 — three judges, full 60 items: final data, requires explicit balance confirmation
python -m src.eval.run_judge --tier 3 --gen results/full_gen_v1.json \
    --balance-checked --max-cost-eur 15 --daily-cap-eur 20
```

Add `--dry-run` to exercise the full pipeline without spending anything. Budget caps have no
override flag: if the estimate exceeds the cap, the run exits without spending.

**Export for BI tools:**

```bash
python -m src.viz.export_for_bi          # → results/bi/*.csv
```

---

## Repository structure

```
data/         dataset_draft.json — 60-item trilingual test set (source of truth)
annotations/  annotation CSVs + Cohen's κ pilot rounds
docs/         methodology decision log, annotation guidelines, rubric spec, budget tracking
src/
  dataset.py            schema / controlled vocabulary / loader
  validate_dataset.py   structure & schema validator
  compute_kappa.py      inter-rater reliability
  llm_client.py         unified tri-provider client (+ token-usage reporting)
  eval/
    rubrics.py               machine-readable 7-dimension rubric + intention taxonomy
    assemble_judge_input.py  judge-input assembler (one call → all applicable dimensions)
    run_judge.py             tiered evaluation runner with enforced budget caps
    aggregate.py             multi-judge medians, self-vs-cross, Equitability
    budget_ledger.py         persistent cost ledger
  prompts/registry.py   version-locked cultural-mode prompts (native-reviewer approved)
  viz/
    week8_plots.py        publication-grade static figures
    export_for_bi.py      flat CSV export for Tableau / Power BI
results/      experiment outputs, figures, and BI exports
```

*Some filenames keep stage-numbered prefixes from earlier in the project
(e.g. `week7_sanity_check_v1.json`) as a historical record; they are referenced by path in code and
deliberately left unrenamed.*

---

## Methods & stack

**Python 3.12** · `openai` · `anthropic` · `pandas` · `matplotlib` · `python-dotenv` · Tableau
Planned: `chromadb` (retrieval), `streamlit` (demo app)

LLM-as-a-Judge (reference-free) · multi-judge median with inter-judge agreement ·
self-vs-cross-judgment bias reporting · inter-annotator reliability (Cohen's κ) ·
pooled-baseline confounder correction for cross-language score gaps

---

## Ethics

A research prototype, **not a clinical tool** — every demo surface says so. Each cultural-mode
prompt embeds crisis recognition and locale-appropriate professional referral (Beijing Crisis
Intervention Center / Telefonseelsorge / 988). Test data is authored by the team and anonymized,
not scraped from real users in distress. The paper includes a standalone Ethics Statement.

---

## Citation & license

```bibtex
@misc{du2026empathylens,
  author = {Du, Feifan and Cai, Xinyan},
  title  = {EmpathyLens: A Cross-Cultural Evaluation Framework for AI Emotional Companionship},
  year   = {2026},
  note   = {LMU Munich. Preprint in preparation.}
}
```

MIT — see [LICENSE](./LICENSE). Questions, collaboration, or feedback: open an issue.
