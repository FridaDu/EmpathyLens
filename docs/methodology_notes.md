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

**Decision (2026-05-02).** Every API call is persisted as JSON with content + run-configuration metadata:

```json
{
  "timestamp": "...",
  "provider": "openai | anthropic | deepseek",
  "model": "gpt-5.4 | claude-opus-4-6 | deepseek-v4-pro",
  "thinking_mode": "disabled | enabled",
  "lang": "zh | de | en",
  "user_input": "...",
  "ai_response": "...",
  "status": "success | error"
}
```

**Anticipated additions** as the project scales:
- `prompt_version` (Week 9+)
- `temperature`, `seed` (Week 8+, if Approach (a) is adopted)
- `run_index` (Week 8+, under Approach (b))
- `evaluation_scores` (Week 8+, joined from LLM-as-a-Judge results)

*中文备注:每条调用都把"在什么配置下产生"记进 JSON。这是可复现性的最低门槛。*

---

## 5. Pending Decisions

| # | Decision | Target |
|---|---|---|
| 1 | Final N for repeated sampling | Week 5–6 |
| 2 | Judge model and thinking-mode for LLM-as-a-Judge | Week 8 |
| 3 | Whether to use a second judge (Cohen's κ) | Week 8 |
| 4 | Prompt versioning convention | Week 7 |
| 5 | Inter-rater reliability protocol for human annotation | Week 5 |