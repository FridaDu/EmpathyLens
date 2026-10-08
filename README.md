# EmpathyLens

**Cross-cultural evaluation infrastructure for LLM outputs — Chinese · German · English**

*跨文化 LLM 输出评估基础设施（中 / 德 / 英）*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-Phase%202%20(Stage%209%2F22)-orange)]()
[![Providers](https://img.shields.io/badge/LLM%20providers-OpenAI%20%7C%20Anthropic%20%7C%20DeepSeek-4B32C3)]()
[![CI](https://github.com/FridaDu/EmpathyLens/actions/workflows/ci.yml/badge.svg)](https://github.com/FridaDu/EmpathyLens/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-reproducible%20env-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![Dashboard](https://img.shields.io/badge/Tableau-interactive%20dashboard-E97627?logo=tableau&logoColor=white)](https://public.tableau.com/app/profile/feifan.du/viz/EmpathyLensCross-CulturalEvaluation/1)

**Authors:** Frida Du (Feifan Du) — LMU Munich, B.Sc. Computational Linguistics | Xinyan Cai — LMU Munich, M.Sc. Computational Linguistics

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
| **Reproducibility** | Containerized Linux environment · Make entrypoints · CI on every push |
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
| **Reproducible environment** | Make entrypoints · Bash pre-flight checks · Docker image · GitHub Actions CI on Ubuntu, run on every push |

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

## Reproducibility & tooling

The evaluation pipeline is developed on macOS and runs identically on Linux — in CI containers and
in Docker. Everything below is in the repo and verifiable.

### Continuous integration

`.github/workflows/ci.yml` runs on an **Ubuntu runner** on every push and pull request:

```
✓ Dataset schema validation          ✓ Prompt registry version-lock check
✓ Rubric self-test                   ✓ Budget ledger self-test
✓ Judge-input assembler self-test    ✓ Full pipeline dry-run (no requests sent)
✓ Secret-leak guard                  ✓ BI export pipeline
```

**No API keys are configured in CI, by design.** Real evaluation runs are billable and must happen
under human supervision per the tiered protocol — letting CI fire paid calls on every push is
exactly the failure mode this project already recovered from once. The workflow says so in a
comment, so the omission reads as a decision rather than an oversight.

The secret-leak guard fails the build if `.env` ever gets tracked by git:

```bash
if git ls-files --error-unmatch .env 2>/dev/null; then
  echo "::error::.env is tracked by git — API keys may be exposed."
  exit 1
fi
```

### Make as the command surface

Raw pipeline invocations are long and some of them spend money. `make` turns them into short
commands and encodes the safety rules:

```bash
make              # list every target, each labelled zero-cost or billable
make validate     # all local checks — same set CI runs
make dry-run      # full pipeline logic, zero requests
make bi           # export flat CSVs for Tableau / Power BI
make tier1        # billable: single judge, 10-item subset
make tier3        # billable: full run — prompts for human balance confirmation first
```

`make tier3` will not proceed without an interactive confirmation that provider balances were
checked — the risk-control protocol enforced by the tooling, not just documented in a file.

The Python interpreter is resolved at runtime rather than hard-coded, so the same Makefile works
inside an activated virtualenv, outside one, and in CI:

```makefile
PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
```

### Containerized environment

`Dockerfile` builds a Debian-slim image that reproduces the full evaluation environment:

```bash
make docker-build       # build the image
make docker-validate    # run the zero-cost checks inside the container
```

Notable choices: dependencies are installed in a separate layer *before* source is copied, so
editing code doesn't invalidate the dependency cache; the container runs as a **non-root user**;
`.dockerignore` excludes `.env`, `.venv`, and `.git` so credentials never enter an image layer; and
the default `CMD` is the zero-cost validation target — never anything billable.

*This demonstrates Linux tooling and containerization in a real project — not systems
administration or kernel-level work.*

---

## Quick start

```bash
git clone https://github.com/FridaDu/EmpathyLens.git && cd EmpathyLens
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your OPENAI / ANTHROPIC / DEEPSEEK keys
```

**Verify everything — no API calls, no cost.** These are the same checks CI runs on every push:

```bash
make validate     # dataset schema, rubric, judge assembler, prompt registry, budget ledger
make preflight    # Bash pre-flight: env, keys, data, disk, spend ledger
make dry-run      # exercise the full evaluation pipeline without sending a single request
```

Run `make` on its own to list every available command, each labelled zero-cost or billable.

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

Or via Make — `make tier1` / `make tier2` / `make tier3`. The `tier3` target additionally prompts
for confirmation that provider balances were checked by a human before it will run at all.

Budget caps have no override flag: if the estimate exceeds the cap, the run exits without spending.

**Export for BI tools:**

```bash
make bi           # → results/bi/*.csv, ready for Tableau / Power BI
```

**Run it in a container** — verifies the environment reproduces cleanly on any machine:

```bash
make docker-build
make docker-validate
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
scripts/preflight.sh       Bash pre-flight checks, gated into the Make targets
.github/workflows/ci.yml   zero-cost validation on every push (Ubuntu runner)
Makefile      command entrypoints, labelled zero-cost vs billable
Dockerfile    reproducible evaluation environment
```

*Some filenames keep stage-numbered prefixes from earlier in the project
(e.g. `week7_sanity_check_v1.json`) as a historical record; they are referenced by path in code and
deliberately left unrenamed.*

---

## Environment & tooling

The evaluation pipeline is built to run reproducibly on Linux, and every safeguard is enforced by
tooling rather than by remembering to be careful.

| | |
|---|---|
| **CI** | GitHub Actions on an Ubuntu runner — schema validation, four module self-tests, a pipeline dry-run, and a guard that fails the build if `.env` is ever tracked by git. No API credentials are configured in CI, by design. |
| **Make** | `make` lists every command, each labelled zero-cost or billable. `make tier3` refuses to start until a Bash pre-flight passes and a human confirms provider balances. |
| **Bash** | `scripts/preflight.sh` — checks interpreter and dependencies, verifies keys are present *and* not committed, confirms data files and disk headroom, reads the local spend ledger, and applies stricter rules before a full run. Exits 0 / 1 / 2 so Make can gate on it. |
| **Docker** | `python:3.12-slim` image, non-root user, layer-cached dependency install, `.dockerignore` that keeps `.env` and `.venv` out of the image. `make docker-validate` proves the environment reproduces on a clean machine. |

```bash
make preflight            # environment + secrets + data + budget checks
make docker-validate      # same checks, inside a clean container
```

---

## Methods & stack

**Python 3.12** · `openai` · `anthropic` · `pandas` · `matplotlib` · `python-dotenv` · Tableau
**Linux tooling:** Docker (Debian-slim) · GNU Make · GitHub Actions (Ubuntu runners) · Bash / POSIX shell (`sed`, `grep`, `find` for repo-wide refactors) · Git
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
