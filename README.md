# EmpathyLens

> A cross-cultural evaluation and prototype system for AI emotional companionship across Chinese, German, and English.
> *跨文化 AI 情感陪伴评估与原型系统(中 / 德 / 英)*

**Status:** Phase 1, Week 4 of 22 (research foundations)
**Started:** 2026-04-20 · **Target completion:** 2026-09-20

**Authors:** Frida Du (Feifan Du) · Helena Cai (Xinyan Cai)
**Affiliation:** LMU Munich, B.Sc. Computational Linguistics

---

## What We Are Doing

Mainstream AI emotional companionship products (Character.ai, Replika, Pi, Maoxiang) are predominantly trained and tuned on English-language data, but increasingly deployed across non-English contexts where empathy norms differ substantially. This project asks:

1. **Diagnostic.** What culturally-mismatched response patterns do mainstream AI companions exhibit when handling Chinese, German, and English emotional disclosures?
2. **Methodological.** Can culture-specific system prompts measurably reduce these mismatches? Can the effect be reliably evaluated by an LLM-as-a-Judge pipeline?
3. **Tooling.** Can we package the resulting evaluation framework as a reusable open-source tool for future cross-cultural AI research?

*主流 AI 情感陪伴产品几乎都基于英语数据训练,但被部署到中德文等差异显著的文化场景。本项目从诊断、方法、工具三层提出研究问题。*

---

## Current Progress

| Phase | Weeks | Focus | Status |
|---|---|---|---|
| 1. Foundations | 1–6 | Research questions, MVP, test dataset | In progress (Week 4) |
| 2. Technical Core | 7–15 | Prompt iteration, LLM-as-a-Judge, RAG, web app | — |
| 3. Product & Writing | 16–22 | Deployment, paper, arXiv submission | — |

---

## Tech Stack

- **Language:** Python 3.12
- **LLM Providers:** OpenAI (GPT-5.4), Anthropic (Claude Opus 4.6), DeepSeek (V4-Pro)
- **Libraries:** `openai`, `anthropic`, `python-dotenv`
- **Planned for later phases:** `chromadb` (Week 10–11, RAG), `streamlit` (Week 15, web app)

---

## Repository Structure

- `docs/` — methodology decisions and research notes
  - `methodology_notes.md` — cross-week methodological decision log
  - `prompt_engineering_basics.md` — prompt-engineering learning note (Week 4)
  - `week4_mvp_notes.md` — Week 4 MVP design decisions
- `src/` — source code
  - `prompts/cultural_prompts.py` — three cultural-mode system prompts (zh / de / en)
  - `cli/empathy_cli.py` — Week 4 CLI: one input → three cultural-mode responses
  - `tests/test_inputs.py` — 5 test inputs (seed for the Week 5–6 dataset)
  - `api_calls/mvp.py` — Week 2 tri-provider MVP (superseded by the CLI)
- `results/` — experiment output JSONs
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

This sends each input through the three cultural-mode system prompts (zh / de / en) using a single provider (Claude Opus 4.6), and writes the full record to `results/`.

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