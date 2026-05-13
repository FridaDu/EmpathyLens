# EmpathyLens

> A cross-cultural evaluation and prototype system for AI emotional companionship across Chinese, German, and English.
> *跨文化 AI 情感陪伴评估与原型系统(中 / 德 / 英)*

**Status:** Phase 1, Week 2 of 22 (research foundations)
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
| 1. Foundations | 1–6 | Research questions, MVP, test dataset | In progress (Week 2) |
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

- `docs/` — methodology decisions, research notes
  - `methodology_notes.md` — Methodological decision log
- `src/` — source code
  - `api_calls/mvp.py` — Tri-provider tri-language MVP
- `results/` — experiment output JSONs (auto-generated)
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

**4. Run the MVP:**

```bash
python src/api_calls/mvp.py
```

This generates emotional-companionship responses in three languages (zh/de/en) using three providers, and writes the full record to `results/`.

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