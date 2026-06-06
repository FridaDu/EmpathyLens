# Methodology Notes — EmpathyLens

Authors: Frida Du, Helena Cai
Started: 2026-05-02 (Week 2)

A running log of methodological decisions. Each decision records what, why, and what alternatives were considered.

---

## 1. Model Selection

**Decision (2026-05-02).** We use each provider's flagship-tier model:

- OpenAI: `gpt-5.4`
- Anthropic: `claude-opus-4-6`
- DeepSeek: `deepseek-v4-pro`

**Rationale.** All three are positioned by their providers as flagship-tier. DeepSeek's V4 technical report explicitly positions V4-Pro as comparable in performance to GPT-5.4 and Opus 4.6.

**Why not the latest flagships (GPT-5.5, Opus 4.7).** Both released within two weeks of this decision (April 16–23, 2026); DeepSeek has no equivalent at this newer generation. Selecting the previous-flagship tier preserves cross-provider comparability.

**Why not mid- or budget-tier (Sonnet 4.6, GPT-5.4-mini, V4-Flash).** Initial tests with budget-tier models (V4-Flash) produced markedly shorter and stylistically simpler responses, not representative of the capability ceiling consumer companionship products aim to deploy.

**Acknowledged limitation.** Independent assessments (CFR, 2026-04-29) suggest V4-Pro may trail SOTA by 3–6 months on reasoning benchmarks, placing it closer to GPT-5.2 / Opus 4.5 in absolute capability. The paper will frame this as *"each provider's flagship-tier model as positioned by the provider"*, not as a capability-matched comparison.
*中文备注:三家都选自家旗舰主力档,DeepSeek 自己的 paper 把 V4-Pro 与 GPT-5.4/Opus 4.6 对标。GPT-5.5 和 Opus 4.7 不用是因为 DeepSeek 没有对等代际。低档不用是因为输出明显欠缺代表性。*

**References.**
- DeepSeek-AI (2026). *DeepSeek-V4 Technical Report.* https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro
- Chen, C. (2026). Three reasons why DeepSeek's new model matters. *MIT Tech Review*, 2026-04-24.
- Horowitz, M. C. (2026). DeepSeek V4 Signals a New Phase in the U.S.–China AI Rivalry. *CFR*, 2026-04-29.

**Lock-in note (2026-05-28).** During Week 4, teammate code temporarily diverged to `claude-sonnet-4-5`. It was corrected back to `claude-opus-4-6`. The model is a **locked** decision: any change updates this section first, then all code, in sync — never the reverse. Mixing models across runs makes results non-comparable.
*中文备注:Week 4 时有代码一度用了 claude-sonnet-4-5,已改回 claude-opus-4-6。模型是锁定决策——要改先改本节再改代码,两边同步,绝不各写各的。*
---

## 2. Reasoning / Thinking Mode

**Decision (2026-05-02).** For all response generation (Phase 1–2), thinking mode is **disabled**:

- OpenAI: `reasoning_effort="none"`
- Anthropic: thinking parameter not passed (default off)
- DeepSeek: `extra_body={"thinking": {"type": "disabled"}}`

For LLM-as-a-Judge (Week 8), thinking may be re-enabled for the judge. To be decided when the evaluation pipeline is built.

**Rationale.** Mainstream consumer companionship products (Character.ai, Replika, Pi, Maoxiang) deploy without thinking due to (1) latency requirements (<1s first-token), (2) unit economics (thinking generates 10–50× more tokens), and (3) product fit (companionship is intuitive-presence, not deliberative-analysis). Enabling thinking during generation would test a configuration no consumer product actually deploys, conflating model capability with deployment configuration and undermining our research question.

*中文备注:主流产品因延迟、成本、产品定位三方面都不开 thinking。生成阶段如果开 thinking,测的就不是真实部署中的产品行为。*

**Paper draft snippet.**
> "All three providers were configured with reasoning/thinking disabled, to match the typical deployment of consumer-facing emotional companionship products, which prioritize first-token latency and cost predictability over deliberative reasoning."

**Update (2026-06-06).** OpenAI generation uses the **Responses API**, not Chat Completions:
- `reasoning={"effort": "none"}` (thinking off) + `max_output_tokens`; read `response.output_text`.
- Reason: on Chat Completions, gpt-5.4 ignores `reasoning_effort="none"` when `max_completion_tokens` is also set — it reverts to reasoning, burns the token budget, and returns an empty string (documented bug, OpenAI community, 2026-04). OpenAI also recommends the Responses API for reasoning models.
- **temperature**: GPT-5.x reasoning models do not honor `temperature`, so the OpenAI path omits it (runs at model default); Claude and DeepSeek still use 0.7. Documented as a cross-provider comparability limitation.
*中文备注:OpenAI 改走 Responses API(effort=none + max_output_tokens);因 gpt-5.4 在 Chat Completions 上 none+max_completion_tokens 有返回空串 bug。GPT 不传 temperature(reasoning 模型不支持),Claude/DeepSeek 仍用 0.7。*
---

## 3. Sampling Variability — Open Question

**Observation (2026-05-02).** Identical inputs to the same model produce substantively different responses across runs (default temperature ≈ 0.7–1.0). Single runs cannot distinguish between-model differences from within-model sampling variance.

**Two standard approaches.**

| Approach | Trade-off |
|---|---|
| (a) Fix temperature low + deterministic seed | Reproducible, but tests an idealized base case that diverges from real-world deployment |
| (b) Run each input N times + analyze aggregate | Captures realistic deployed behavior; cost and statistical complexity scale with N |

**Tentative decision.** Approach (b), N = 3–5 per condition. Real-world products deploy with default stochastic sampling, and our RQ targets typical deployed behavior. Reproducibility is preserved by (1) full configuration metadata in every output JSON and (2) public release of the output corpus.

**To resolve.**
- Week 5–6: factor N into total run count when designing the test dataset.
- Week 8: finalize N (3 vs 5) based on observed budget consumption.
- Week 8: implement aggregate analysis (mean, variance, distributional plots).

*中文备注:LLM 默认采样有随机性,同一输入跑两次结果不同。Week 8 之前需要决定:每条输入跑几次。暂定 3-5 次。*

---

## 4. Output Metadata Schema

**Decision (2026-05-02, updated 2026-05-28).** Every run is persisted as JSON with content + full run-configuration metadata.

The Week 2 `mvp.py` used a flat per-call schema (`provider / lang / user_input / ai_response / status`). From Week 4, the canonical format is the one produced by `src/cli/empathy_cli.py` — one record per input, with all three cultural-mode responses nested under it, plus test-item metadata:

```json
{
  "user_text": "...",
  "timestamp_utc": "ISO 8601 (UTC)",
  "prompt_version": "v1",
  "model": "claude-opus-4-6",
  "temperature": 0.7,
  "responses": {
    "zh | de | en": {
      "response_text": "...",
      "model": "claude-opus-4-6",
      "temperature": 0.7,
      "max_tokens": 600,
      "thinking_mode": "disabled",
      "stop_reason": "...",
      "input_tokens": 0,
      "output_tokens": 0,
      "latency_sec": 0.0
    }
  },
  "test_item": {
    "id": "...",
    "lang": "zh | de | en",
    "kind": "mild_venting | adversarial",
    "anchor": "framework §...",
    "note": "..."
  }
}
```

`prompt_version`, `temperature`, and `thinking_mode` — listed as "anticipated" in the original draft — are **now in use**. Each record is self-contained (config + input + all outputs + test metadata), so the Week 8 evaluation pipeline can consume it without joining other tables.

**Still anticipated** as the project scales:
- `seed` (Week 8+, only if a fixed-seed approach is adopted — see §3)
- `run_index` (Week 8+, under repeated-sampling Approach (b))
- `evaluation_scores` (Week 8+, from LLM-as-a-Judge)

*中文备注:Week 2 的 mvp.py 是扁平 schema;Week 4 起以 empathy_cli 的嵌套格式为准。prompt_version / temperature / thinking_mode 已经在用了,不再是"待加"。*

---

## 5. Pending Decisions

| # | Decision | Target |
|---|---|---|
| 1 | Final N for repeated sampling | Week 5–6 |
| 2 | Judge model and thinking-mode for LLM-as-a-Judge | Week 8 |
| 3 | Whether to use a second judge (Cohen's κ) | Week 8 |
| 4 | Prompt versioning convention | Week 7 |
| 5 | Inter-rater reliability protocol for human annotation | Week 5 |
| 6 | Baseline design for measuring the calibration effect: cross-language (English mode) vs within-language (same-language uncalibrated) | Week 7 |

*中文备注:六项待定决策及目标周次;其中 #5(人工标注一致性协议)是 Week 5 要落地的。*
---

## 6. Prompt Engineering Decisions

**Decision (Week 4).** v1 cultural-mode prompts use a **single-step "guideline" form**, not the explicit four-step reasoning chain of framework §6.2.

**Rationale.** Generation runs with thinking disabled (§2). With no hidden-reasoning space, an explicit chain would either print all reasoning (unfit for a companion reply) or be skipped. So the chain's intent is encoded as direct behavioral guidelines. The four-step vs single-step comparison is a Week 7–9 ablation (anticipated by framework §6.2). Week-4 specifics: see `week4_mvp_notes.md §5`.

**Decision (Week 4).** The **English mode is an uncalibrated baseline**, not a gold standard (framework §3.3.2). It represents the model's default American-style behavior and is the reference for the Equitability metric (§5.7). zh/de are deliberately calibrated; en intentionally is not.

**Decision (2026-05-28).** Each prompt carries an **explicit response-language instruction** ("respond in Chinese/German/English regardless of the user's input language").

**Why.** The zh/de prompts, written in their target language, already anchored output strongly; the English prompt (English being the model's neutral register) did not, so the English mode drifted into the user's input language. The explicit instruction makes all three modes language-consistent.

**Nuance for Week 7.** Forcing English output supports the cross-language Equitability comparison (§5.7). But measuring the *within-language* calibration effect (Sub-RQ 2) needs a same-language uncalibrated baseline — a separate baseline to design in Week 7 (§5, pending #6).

*中文备注:v1 用单步准则 prompt(非四步链),因生成关 thinking;英语是未校准基线;每套 prompt 现都加了显式语言指令,修复英语串语言;Week 7 还要定"同语言基线"。*