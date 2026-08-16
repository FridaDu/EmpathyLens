# EmpathyLens

> A cross-cultural evaluation framework and prototype system for testing how reliably AI models handle culturally and linguistically ambiguous input, across Chinese, German, and English.
> *跨文化 AI 评估框架与原型系统(中 / 德 / 英)*

**Status:** Phase 2, Week 9 of 22 (technical core — risk-control infrastructure rebuild after Week 8's first full evaluation run)
**Started:** 2026-04-20 · **Target completion:** 2026-09-20

**Authors:** Frida Du (Feifan Du) · Helena Cai (Xinyan Cai)
**Affiliation:** LMU Munich, B.Sc. Computational Linguistics

---

## What We Are Doing

Mainstream AI products (Character.ai, Replika, Pi, Maoxiang) are predominantly trained and tuned on English-language data, but increasingly deployed across non-English contexts where communication norms differ substantially. This project builds and validates an evaluation infrastructure to answer three questions:

1. **Diagnostic.** What culturally-mismatched response patterns do mainstream AI systems exhibit when handling Chinese, German, and English input?
2. **Methodological.** Can culture-specific system prompts measurably reduce these mismatches, and can the effect be reliably measured by an automated, reference-free LLM-as-a-Judge pipeline?
3. **Tooling.** Can the resulting evaluation framework be packaged as a reusable, open-source toolkit for testing AI system outputs across languages more broadly — **including a cost-controlled, reproducible evaluation protocol**?

*主流 AI 产品几乎都基于英语数据训练,但被部署到中德文等差异显著的文化场景。本项目搭建并验证一套评估基础设施,从诊断、方法、工具三层回答上述问题——工具层现在也包含一套成本可控、可复现的分级评估协议。*

---

## Engineering Highlights

- **Multi-provider LLM integration:** a single, unified client (`llm_client.py`) abstracts over three LLM providers (OpenAI, Anthropic, DeepSeek), so evaluation logic stays provider-agnostic.
- **Automated, reference-free evaluation pipeline:** an LLM-as-a-Judge system (`run_judge.py`) that scores model outputs against a 7-dimension rubric without gold-standard reference answers, including self-vs-cross evaluation reporting.
- **Cost-controlled, tiered evaluation protocol (★ new, Week 9):** after an uncontrolled first full run (Week 8: 6,165 judge calls) exhausted API budget faster than the built-in cost estimator anticipated, the pipeline was rebuilt around a three-tier protocol — Tier 1 (single-judge smoke test on a 10-item subset), Tier 2 (three-judge confirmation on the same subset), Tier 3 (full 60-item, three-judge run, executed exactly once, with mandatory manual balance checks before/during execution). Judge calls were also restructured from one call per (response × dimension × judge) to one call per (response × judge) returning all 7 dimensions at once — cutting call volume roughly 7×.
- **Reproducible dataset pipeline:** dataset construction, schema validation, and inter-rater reliability computation (Cohen's κ) are fully scripted — see `src/validate_dataset.py` and `src/compute_kappa.py`.
- **Structured, machine-readable rubric:** evaluation dimensions and the 14-token intention taxonomy are defined as code (`eval/rubrics.py`), not just documentation, so they can be consumed programmatically by the pipeline.

---

## Current Progress

| Phase | Weeks | Focus | Status |
|---|---|---|---|
| 1. Foundations | 1–6 | Research questions, MVP, test dataset, eval rubric | ✅ Done |
| 2. Technical Core | 7–15 | Prompt iteration, LLM-as-a-Judge pipeline, RAG, web app | 🔄 In progress — Week 7 (culture-mode prompts v1) and Week 8 (automated evaluation pipeline, first full run) complete. **Week 9: risk-control infrastructure rebuild in progress** (see Engineering Highlights above) |
| 3. Product & Writing | 16–22 | Deployment, paper, arXiv submission | — Week 16 public deployment redesigned as a tiered system: a static pre-recorded case library by default, with an optional, rate-limited, DeepSeek-only live demo layer |

---

## A Note on the Week 8 → Week 9 Transition

The project's first full evaluation run (Week 8) generated 300 model responses and 6,165 judge calls across three LLM providers within roughly a week, and exhausted the API budget faster than the pipeline's cost estimator predicted — the estimator used hard-coded per-token pricing rather than actuals, and the budget cap could be bypassed with a `--yes` flag. No data or account was lost; this was a **billing/cost-control gap**, not a policy violation.

Starting Week 9, the evaluation pipeline runs on a **tiered protocol** (see Engineering Highlights) with a hard, non-bypassable budget cap, actively-throttled call spacing, and mandatory manual balance checks before any full-dataset run. We're documenting this openly because a cost-controlled, auditable evaluation protocol is itself part of what Sub-RQ 3 (tooling) is meant to deliver — not a footnote to hide.

---

## Tech Stack

- **Language:** Python 3.12
- **LLM Providers:** OpenAI (GPT-5.4), Anthropic (Claude Opus 4.6), DeepSeek (V4-Pro)
- **Libraries:** `openai`, `anthropic`, `python-dotenv`, `pandas`, `matplotlib`
- **Planned for later phases:** `chromadb` (Week 10–11, RAG), `streamlit` (Week 15, web app)

---

## Repository Structure

- `docs/` — methodology decisions and research notes
  - `methodology_notes.md` — cross-week methodological decision log (now includes the Week 9 risk-control protocol)
  - `annotation_guidelines_v1_2.md` — annotation guideline (Week 5)
  - `evaluation_dimensions_v1_1.md` — 7-dimension evaluation rubric (Week 6)
  - `七维rubric速查卡.md` — one-page rubric cheat sheet (Week 6)
  - `prompt_engineering_basics.md` / `week4_mvp_notes.md` — Week 4 notes
- `data/`
  - `dataset_draft.json` — the 60-item test dataset (source of truth)
- `annotations/` — annotation CSVs + Kappa pilot rounds (frida/helena r1, r2)
- `src/` — source code
  - `dataset.py` — dataset schema / controlled vocab / loader
  - `validate_dataset.py` — structure & schema validator
  - `fill_annotations.py` / `merge_filled.py` / `make_skeleton.py` — dataset build helpers
  - `compute_kappa.py` / `make_kappa_sheets.py` — inter-rater reliability (Cohen's κ)
  - `inject_design_metadata.py` — scenario design metadata injector
  - `llm_client.py` — unified tri-provider client (Claude / GPT / DeepSeek)
  - `eval/` — evaluation pipeline
    - `rubrics.py` — machine-readable 7-dimension rubric + intention taxonomy
    - `assemble_judge_input.py` — LLM-as-a-Judge input assembler; **as of Week 9, one call per (response × judge) returns all 7 dimensions at once**, rather than one call per (response × dimension × judge)
    - `run_judge.py` — evaluation runner; **as of Week 9, supports `--tier {1,2,3}`, enforces a hard non-bypassable budget cap, and actively throttles calls**
  - `prompts/cultural_prompts.py` — three cultural-mode system prompts (zh / de / en), v1 (Week 7)
  - `cli/empathy_cli.py` — Week 4 CLI: one input → three cultural-mode responses
  - `tests/test_inputs.py` — 5 seed inputs (superseded by the 60-item dataset)
  - `api_calls/mvp.py` — Week 2 tri-provider MVP (superseded by the CLI)
- `results/` — experiment output JSONs, incl. first full evaluation run (Week 8) and the `.budget_ledger.json` cost-tracking log (Week 9+)
- `.env.example` — template for API keys (real `.env` is gitignored)
- `requirements.txt` — Python dependencies

---

## Quick Start

**1. Clone the repo:**

```bash
git clone https://github.com/FridaDu/EmpathyLens.git
cd EmpathyLens
```

**2. Set up Python environment:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Configure API keys:** Copy `.env.example` to `.env` and fill in your own keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

**4. Run the MVP (Week 4 CLI):**

```bash
# Batch: run all 5 test inputs through the three cultural modes, save to results/
python -m src.cli.empathy_cli --batch

# Or respond to a single disclosure interactively
python -m src.cli.empathy_cli --text "我妈又催我相亲了,烦死了。"
```

**5. Validate the dataset & evaluation rubric:**

```bash
python -m src.validate_dataset           # 60 records, schema check (expect 0 errors)
python -m src.eval.rubrics               # 7 dimensions + 14-token intention taxonomy
python -m src.eval.assemble_judge_input  # judge-input assembler self-test
```

**6. Run the evaluation pipeline (tiered, as of Week 9):**

```bash
# Tier 1: single-judge smoke test on the 10-item sanity subset — cheapest, run this first
python -m src.eval.run_judge --tier 1 --gen results/week7_sanity_check_v1.json --judges deepseek-v4-pro

# Tier 2: three-judge confirmation on the same subset
python -m src.eval.run_judge --tier 2 --gen results/week7_sanity_check_v1.json

# Tier 3: full 60-item, three-judge run — intended to be run once per prompt version,
# with manual provider-dashboard balance checks before starting
python -m src.eval.run_judge --tier 3 --gen results/full_gen_v1.json --max-cost-eur 15
```

The budget cap is enforced with no bypass flag. If the estimated cost exceeds `--max-cost-eur`, the run exits without spending; lower the scope (fewer judges, smaller subset) or raise the cap deliberately after checking actual provider pricing.

---

## Citation

Placeholder — to be updated upon paper completion:

> Du, F., & Cai, X. (2026). *EmpathyLens: A Cross-Cultural Evaluation Framework for AI Emotional Companionship.* LMU Munich.

---

## License

MIT License. See [LICENSE](./LICENSE).

---

## Contact

For questions or collaboration: open an issue, or contact the authors via LMU Munich.
