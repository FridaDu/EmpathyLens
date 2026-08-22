# EmpathyLens

**Cross-cultural evaluation infrastructure for LLM outputs — Chinese · German · English**

*跨文化 LLM 输出评估基础设施（中 / 德 / 英）*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-Phase%202%20(Stage%209%2F22)-orange)]()
[![Providers](https://img.shields.io/badge/LLM%20providers-OpenAI%20%7C%20Anthropic%20%7C%20DeepSeek-4B32C3)]()

> How do you tell whether an LLM handles a German user's grief the way German users actually
> need — and not merely the way an English-trained model assumes anyone should be comforted?
> EmpathyLens builds the measurement infrastructure to answer that question, and packages it as
> a reusable, cost-controlled evaluation toolkit.

**Authors:** Frida Du (Feifan Du) · Helena Cai (Xinyan Cai) — LMU Munich, B.Sc. Computational Linguistics
**Progress:** Phase 2 · Stage 9 of 22

---

## Why this matters

Consumer AI companionship products (Character.ai, Replika, Pi, 猫箱) are trained predominantly
on English data, then deployed into markets where the norms of *good emotional support* differ
substantially. American-mainstream support tends toward explicit validation, fairly rapid positive
reframing, and actionable advice. German norms lean toward **acknowledging the negative** before
offering any silver lining. Chinese norms often prioritize **presence over action** and relational
rather than individualist attribution.

A model that applies the first pattern to all three audiences isn't neutral — it is systematically
mismatched, in a domain where mismatch carries real cost. **Measuring that mismatch reliably is
the hard part, and that's what this project builds.**

This directly connects to **EU AI Act Article 15** (accuracy and robustness of high-risk AI
systems): robustness claims that hold only for English-language inputs are not robustness claims
at all.

---

## What's built (and verified)

| Component | What it does |
|---|---|
| **60-item trilingual test set** | 20 scenarios × zh/de/en, natively authored (not translated), covering mild venting / adversarial / control / crisis, with per-item cultural metadata |
| **7-dimension rubric as code** | `eval/rubrics.py` — dimensions + a closed 14-token intention taxonomy, machine-readable rather than prose-only |
| **Reference-free LLM-as-a-Judge pipeline** | `eval/run_judge.py` — scores outputs with no gold-standard answers, across three judge models, with self-vs-cross-judgment reporting |
| **Tri-provider abstraction** | `llm_client.py` — one interface over OpenAI / Anthropic / DeepSeek; evaluation logic stays provider-agnostic |
| **Tiered, cost-controlled protocol** | Non-bypassable budget caps, active throttling, real-token-usage accounting, code-enforced manual checkpoints |
| **Reproducible data pipeline** | Schema validation + Cohen's κ inter-rater reliability, fully scripted |

**Scale of the first full evaluation run:** 300 generated responses × 3 providers × 4 prompt
conditions, scored on 7 dimensions by 3 independent judge models → 6,210 scored data points.

---

## Two engineering findings worth reading

These are the parts a reviewer might actually want to ask about.

### 1. Catching a measurement artifact that would have corrupted a core result

One experimental condition (`en_geo` — an English prompt plus a country-context label, our strong
baseline for testing whether a nationality tag alone can substitute for real cultural calibration)
scored **1.43 / 5** on language naturalness, versus 4.50–4.92 for every other condition.

That looked like a dramatic finding. It wasn't. The judge prompt was being told the target
language was Chinese/German (inherited from the item's target-culture record), while `en_geo`
responses are by design always in English. The judge was correctly scoring a contradiction we had
constructed. Root cause was a conflation of two distinct fields: *the language the response is
actually in* (which governs naturalness scoring) versus *the cultural norm the response is being
evaluated against* (which governs cultural-fit scoring). These were separated, with assertion
tests added.

**Why this matters:** the affected condition is precisely the one testing our most interesting
hypothesis. Publishing a 3-point gap that was an artifact of our own prompt assembly would have
been considerably worse than the delay of finding it. Contamination scope was then traced
explicitly — cultural-fit and intention dimensions were unaffected, and the Equitability metric
never ingested this condition at all.

### 2. Rebuilding the pipeline after a budget failure

The first full run issued 300 generation calls plus **6,165 judge calls**, and exhausted the API budget faster than the pipeline's own estimator predicted. Root causes, in order
of contribution:

1. **Structural over-calling** — the judge was invoked once per *(response × dimension × judge)*: 7 × 3 = 21 calls per response.
2. **Uncalibrated cost estimation** — hard-coded per-token pricing, never reconciled against invoices.
3. **A bypassable cap** — `--max-cost-eur` could be overridden with `--yes`.
4. **No active throttling** — back-off existed only *after* an error.

The fix was structural rather than cosmetic. Judge calls now return all applicable dimensions in a
single JSON response: **~1/7 the call volume** for identical output data (verified — the rebuilt
pipeline reproduces the same 6,210-row output schema, and every downstream consumer required zero
changes). Budget caps became non-bypassable at both per-run and per-day granularity, backed by a
local ledger using **provider-reported token counts** rather than character-count estimates. Manual
balance verification became a code-enforced precondition for any full-dataset run.

A side benefit: user disclosures — including crisis-scenario items — were previously embedded up to
21 times per response across outbound requests. Now 3.

**Why this matters:** the incident is documented here rather than quietly deleted from the commit
history, because a cost-controlled, auditable evaluation protocol is part of what this project
claims to deliver. An evaluation framework nobody can afford to run twice isn't reusable.

---

## Preliminary findings

⚠️ **Read as directional, not conclusive.** Single-sample generation (N=1), no significance testing
yet, one prompt version. The locked full evaluation that these claims will stand or fall on is
scheduled for Stage 13.

- **D7 (progression & tension-handling) is the weakest dimension** across all conditions
  (4.24 vs 4.56–4.93 for the other six).
- **The weak point is not where we expected.** Splitting D7 by scenario type: *direct* adversarial
  input ("you're just a machine") scores **4.45** — the explicit handling written into the prompts
  works. *Indirect, withdrawing* adversarial input ("never mind, you wouldn't get it") scores
  **3.65**. Models fall back to reassurance templates when a user quietly closes the conversation,
  which is exactly the failure mode our framework predicts but the prompts didn't yet name.
- **Cross-model variance is largest in Chinese** (D7: 3.88–4.95 across the three models), suggesting
  the Chinese guidance may be less consistently executable across models than the German version.

---

## Tech stack

**Python 3.12** · `openai` · `anthropic` · `pandas` · `matplotlib` · `python-dotenv`
Planned: `chromadb` (retrieval), `streamlit` (demo app), interactive BI dashboard (Tableau)

**Methods:** LLM-as-a-Judge (reference-free) · multi-judge median with inter-judge agreement ·
self-vs-cross-judgment bias reporting · inter-annotator reliability (Cohen's κ) ·
pooled-baseline confounder correction for cross-language score gaps

---

## Quick start

```bash
git clone https://github.com/FridaDu/EmpathyLens.git && cd EmpathyLens
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your OPENAI / ANTHROPIC / DEEPSEEK keys
```

**Verify the dataset and rubric (no API calls, no cost):**

```bash
python -m src.validate_dataset           # 60 records, schema check → expect 0 errors
python -m src.eval.rubrics               # 7 dimensions + 14-token intention taxonomy
python -m src.eval.assemble_judge_input  # judge-input assembler self-test
```

**Generate responses across the three cultural modes:**

```bash
python -m src.cli.empathy_cli --text "我妈又催我相亲了,烦死了。"
```

**Run the evaluation pipeline (tiered):**

```bash
# Tier 1 — single judge, 10-item subset: cheapest, run this first after any prompt change
python -m src.eval.run_judge --tier 1 --gen results/week7_sanity_check_v1.json

# Tier 2 — three judges, same subset: quantitative confirmation
python -m src.eval.run_judge --tier 2 --gen results/week7_sanity_check_v1.json

# Tier 3 — three judges, full 60 items: final data; requires explicit balance confirmation
python -m src.eval.run_judge --tier 3 --gen results/full_gen_v1.json \
    --balance-checked --max-cost-eur 15 --daily-cap-eur 20
```

Add `--dry-run` to any command to exercise the full pipeline without spending anything. Budget
caps have no override flag: if the estimate exceeds the cap, the run exits without spending.

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
  viz/                  publication-grade figures
results/      experiment outputs + figures
```

*Note: some filenames retain stage-numbered prefixes from earlier in the project
(e.g. `week7_sanity_check_v1.json`) as a historical record; they are referenced by path in code
and are deliberately left unrenamed.*

---

## Roadmap

| Phase | Stages | Focus | Status |
|---|---|---|---|
| 1 · Foundations | 1–6 | Research design, MVP, test set, rubric | ✅ Complete |
| 2 · Technical core | 7–15 | Prompts, evaluation pipeline, retrieval, BI dashboard, demo | 🔄 Stage 9 — risk-control rebuild |
| 3 · Product & writing | 16–22 | Public deployment, paper, arXiv | ⏳ Planned |

Planned in Phase 2: an interactive dashboard over the 6,210-point scoring dataset — model ×
language × dimension slicing, Equitability heatmaps, and drill-down to individual scenarios —
complementing the static publication figures.

Public deployment will use a static pre-recorded case library by default, with an optional
rate-limited live layer — so a public demo can't become an unbounded cost surface.

---

## Ethics

This is a research prototype, **not a clinical tool**. All demo surfaces carry that statement
explicitly. Every cultural-mode prompt embeds crisis recognition and locale-appropriate
professional referral (Beijing Crisis Intervention Center / Telefonseelsorge / 988). Test data is
anonymized and authored by the team, not scraped from real users in distress. The paper includes a
standalone Ethics Statement.

---

## Citation

```bibtex
@misc{du2026empathylens,
  author = {Du, Feifan and Cai, Xinyan},
  title  = {EmpathyLens: A Cross-Cultural Evaluation Framework for AI Emotional Companionship},
  year   = {2026},
  note   = {LMU Munich. Preprint in preparation.}
}
```

---

## License & contact

MIT — see [LICENSE](./LICENSE). Questions, collaboration, or feedback: open an issue.
