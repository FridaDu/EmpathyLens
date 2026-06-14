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

| # | Decision | Target                                           |
|---|---|--------------------------------------------------|
| 1 | Final N for repeated sampling | Week 8                                           |
| 2 | Judge model and thinking-mode for LLM-as-a-Judge | Week 8                                           |
| 3 | Whether to use a second judge (Cohen's κ) | Week 8                                           |
| 4 | Prompt versioning convention | Week 7                                           |
| 5 | Inter-rater reliability protocol for human annotation | ✅ Resolved Week 5 → see §8                       |
| 6 | Baseline design for measuring the calibration effect: cross-language (English mode) vs within-language (same-language uncalibrated) | Week 7                                           |
| 7 | Self-judging bias handling (judge model == generator model) | ✅ Resolved Week 6 → §9 (self-vs-cross reporting) |

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

---

## 7. Test Dataset Construction

**Decision (Week 5, 2026-06).** The test set is **60 items = 20 scenarios (S01–S20) × 3 languages (zh/de/en)**.

**Native authorship — not LLM-generated, not translation.** All 60 user-turn texts are written by native speakers: **zh by Frida & Helena, de by Jens Linden, en by Rodney Kale**. An earlier draft of ~40 LLM-generated zh/de items was **discarded**.

**Rationale.** (1) framework §4.2 requires native-authored, type-parallel texts. (2) LLM-generated user turns would bake in the very model behaviors under test and lose authentic cultural expression (understatement, face-work, register). (3) Native authorship gives `native_reviewed = True` for all 60 and removes the earlier "non-native de/en" limitation.

**Type-parallel, NOT translation.** The 20 scenario *types* are shared across languages, but each language's text is **independently authored in that language** — three native versions of the same situation, not translations. What binds them as "the same scenario" is the **metadata** (`scenario_id` + scenario-level fields), not literal text.

**Acknowledged consequence — cross-language intensity variation.** Because texts are independently authored, the same scenario's `emotional_intensity` can differ across languages (observed: **S01** de=2 / zh=4; **S06** de=1 / zh=3 — German versions milder). Accepted as genuine native variation and documented as a limitation; `validate_dataset` flags any |Δ| > 1 across the three languages for manual review.

*中文备注:60 条 = 20 场景 × 三语,全部母语者原生撰写(中 Frida/Helena、德 Jens、英 Rodney),不互译、不用 LLM 生成(弃掉了早期 40 条 AI 生成稿)。维系"同场景"的是元数据不是字面文本。代价:母语各写 → 同场景三语强度可能差 >1(S01/S06),当 native variation 接受并记 limitation,validator 查 ≤1。*

---

## 8. Human Annotation — Reliability Protocol & Results (resolves Pending #5)

**Decision (Week 5, 2026-06).** Two fields (`emotional_intensity`, `cultural_sensitivity`) are annotated by **two human raters (Frida, Helena)** against a written guideline (`annotation_guidelines_v1_1.md`), validated by **inter-rater Cohen's Kappa**, and iterated until threshold.

**Field definitions (project constructs — framework defines neither scale).**
- **`emotional_intensity` (1–5, per-text / language-level).** Rate the **underlying severity** conveyed, not surface tone, with evidence in-text. **Two-step method**: (1) surface reading; (2) weight-marker correction — understatement-contradiction (+1), withdrawal (floor 3), despair-generalization (→5), identity-negation (floor 4), adversarial-attack (→≥4). Serves framework §5.3 Generator-side diagnosis.
- **`cultural_sensitivity` (high/medium/low, scenario-level).** **Four-axis count**: for each framework normative axis (A presence↔action, B emotion↔attribution, C positivity↔acknowledge-negative, D indirect↔direct), is there an *articulable* cross-cultural divergence in the ideal response? Count "yes": 0=low, 1=medium, ≥2=high. Distinct from framework §5.6 mismatch severity.

**Reliability protocol.** Blind independent annotation → Cohen's Kappa (intensity **quadratic-weighted**; sensitivity unweighted) → κ < 0.6: diagnose disagreements, revise guideline, re-annotate; κ ≥ 0.6 acceptable, ≥ 0.8 good. Saha-style multi-round pilot.

**Results.**

| Round | Items | Guideline | intensity κ | sensitivity κ |
|---|---|---|---|---|
| 1 | 10 | v1.0 | 0.55 (moderate) | 0.24 (fair) |
| 2 | 15 (10 repeat + 5 fresh) | v1.1 | **0.711** (substantial) | **0.886** (almost perfect) |

- **Round-1 diagnosis.** §3 had not specified surface-vs-underlying (S17/S01 divergence); §4's "imagine the responses differ" was unbounded → systematic offset (one rater low, one high).
- **v1.1 revision.** Two-step intensity method + weight markers; four-axis sensitivity count. Both κ then passed.
- **Reconcile → v1.2.** The 5 round-2 disagreements were reconciled and the remaining ambiguities pinned (S17 floor, S05 4↔5 boundary, S15 control rule).

**Convention — adversarial intensity (v1.2, "option A").** For adversarial-attack turns (S18/S19), intensity = **high (≥4)** by team choice, encoding **interactional severity** (framework §5.5 M7); self-directed distress is *not* required. *Alternative considered (option B):* rate only disclosed distress → adversarial scores low. **Chose A.** **Downstream caveat:** on adversarial items, intensity = interactional severity, not pure distress; the §5.3 Generator-side analysis must treat adversarial items separately from disclosure items.

**Documented limitations.** (1) Four-axis **equal-weight** count under-rates single-axis-but-severe scenarios (S06, S18: design intuition high, count gives medium); accepted to preserve reproducibility (the mechanical count is what raised sensitivity κ from 0.24 to 0.886). (2) Cross-language intensity variation from native authorship (§7).

**Paper value.** The round-1→round-2 κ improvement under explicit guideline iteration is reported as **standard reliability methodology** — a low first-round κ is normal; the diagnose-revise-re-annotate loop is rigor, not failure.

*中文备注:两人(Frida/Helena)对 intensity(1–5,逐条,两步法)和 sensitivity(场景级,四轴计数)盲标 → 加权/普通 Cohen's Kappa → <0.6 改指南重标。两轮:0.55/0.24(v1.0)→ 0.711/0.886(v1.1)。reconcile 后定 v1.2。对抗强度选口径 A(攻击=高,编码 M7 交互严重度,非纯痛苦,§5.3 分析需单列对抗条)。两条 limitation:四轴等权低估单轴极重;母语各写致三语强度差。低首轮 κ + 迭代 = 标准严谨流程。*

---

## 9. Evaluation Dimensions & Scoring Rubric (Week 6)

**Decision (Week 6, 2026-06).** Model **responses** are scored on **7 dimensions** in a two-layer structure (framework §4.3), plus one second-order metric. Full rubric: `docs/evaluation_dimensions_v1.md`; machine-readable form: `src/eval/rubrics.py`.

- **Universal layer (any culture):** D1 Empathy & Validation, D2 Non-minimization & Non-judgment, D3 Safety & Crisis Recognition. (= the five §4.3 common foundations, merged into 3.)
- **Cultural-specific layer (scored against the item's target culture):** D4 Cultural Norm Fit (§3.0 four axes), D5 Intention Fit (§5.4), D6 Language Naturalness & Register.
- **Interaction layer:** D7 Progression & Tension-handling (§4.2 surface-vs-experienced empathy; the M7 locus for adversarial items).
- **Second-order:** Equitability (§5.7) — cross-language score gap, derived not directly scored.

Each dimension carries **1–5 anchors with observable markers** (not "good/medium/bad"). Dimensions are scored independently. Aligned to HEART (H/E/A/R/T) for benchmarking.

**Decision — cultural dimensions are parameterized, not a fixed yardstick.** D4/D5 score "does the response match *this item's target-culture* ideal direction", with the judge fed each item's `ideal_norm_direction` / `ideal_intention` / `stressed_axes`. The same rubric thus scores zh/de/en fairly without treating an American default as the correct answer. *English* items are scored against the American-mainstream baseline (§3.3.2) as their de-facto target; the assembler translates the "uncalibrated baseline" metadata into a scorable target so D4/D5 don't receive un-scorable meta-text.

**Decision — no "advice-utility" dimension** (despite the Week-6 brief listing one). A naïve advice-utility scale would systematically penalize culturally-correct *restraint of advice* (a core framework claim for zh support). Whether advice is appropriate is already captured by D4 (axis A presence↔action) and D7 (timing). Documented as deliberate.

**Decision — reference-free judging.** The judge is given the *ideal direction* + rubric, never a gold-answer text (over-anchoring) and **never `watch_mismatches`** (the per-item expected mismatch codes = an answer key; feeding it primes the judge to "find" exactly those, inflating mismatch detection). `watch_mismatches` is retained only as an ablation switch.

**Decision — intention taxonomy (D5).** D5 uses a **closed 14-token taxonomy** = IntentionESC 12 + framework's `Preserve-Face` (zh) + `Acknowledge-Negativity` (de), per §5.4. Strategy-layer tokens (Validate / Reframe / Problem-solving) are **not** intentions and were removed (mapped to intentions via an alias table); collapsing strategy into intention would flatten the very "strategy-right, intention-wrong" mismatch (M5) the project diagnoses. The 17 English items' `ideal_intention` were canonicalized to the baseline intention cluster `Feelings / Hope / Give-information / Change`.

**Decision — D3 crisis trigger is language-specific (native variation).** Crisis-mode anchors (5-level) vs general anchors (3-level) are selected per item. S20 (explicit crisis) triggers crisis mode in all three languages; **S14 (self-loathing) triggers crisis mode only for zh** — the German and English native texts express the situation more mildly (situational self-doubt / generalized overwhelm rather than identity-level self-negation), and **the team deliberately did not rewrite them**: cross-cultural variation in how "self-negation" surfaces is itself a research object (a §5.5 M2 *Cultural Vacancy* case), not a defect. The scoring logic adapts to the data, not vice versa. A consequence is that S14's D3 scores live on different scales across languages and are therefore **cross-language incomparable on D3** — recorded as a Discussion finding (framework v0.3), and excluded from D3 cross-language Equitability aggregation.

**Decision — S19 is a culture-invariant control.** The AI-legitimacy-challenge scenario (S19) has identical tri-lingual ideal handling (acknowledge it's not human, name the tension, don't get defensive), empty `stressed_axes`. It tests only D7/M7; its D4 is N/A and its D4/D5 are excluded from cultural Equitability diffs.

**Decision — Equitability computation.** Per-dimension cross-language gaps are reported **signed** (`en − zh`/`de`, preserving the "which way it leans" direction = the Sub-RQ1 finding); only the single composite index uses **mean(|gap|)** (signed terms would cancel). The **language-ability confounder** is removed via a **pooled ability baseline**: because D4 is N/A on the control items (S15/S16 have no axes and can't self-subtract), the baseline is pooled from the culture-free dimensions **D1/D2** on S15/S16 — `ability_baseline(model, lang)` — and subtracted from all cultural dimensions including D4. Both **raw and corrected** gaps are reported (sensitivity analysis). This is the aggregation-layer *partial* confounder control and is **complementary to**, not a replacement for, the §5.8 SAGE injection experiment (Weeks 7–9), which remains the primary mismatch-vs-ability discriminator.

**Decision — multi-judge & self-judging bias.** Three judges (GPT-5.4 / Claude-opus-4-6 / DeepSeek-v4-pro), median score, inter-judge agreement reported. Because the judges are also the generators, self-enhancement bias is handled by **reporting self-judgments and cross-judgments separately** (rather than leave-one-out, which would discard 1/3 of the scores).

**Status.** Rubric is **v1**; it will be revised after the first Week-8 trial scoring based on inter-judge agreement (same iterate-on-reliability logic as §8).

*中文备注:Week 6 评估维度定稿——响应分 7 维(3 普世 D1-D3 + 3 文化特异 D4-D6 + 1 互动 D7)+ 二阶 Equitability。文化维参数化(喂每条目标文化理想),英语按美式基线评。刻意不设"建议实用性"维。reference-free 且不喂 watch_mismatches(防 priming)。D5 意图词表 = IntentionESC 12 + Preserve-Face + Acknowledge-Negativity 共 14,剔除策略 token,17 条英语意图已归一。D3 危机触发语言特异:S20 三语都危机、S14 仅 zh 危机(德英原生文本更轻,有意不改 → M2 文化空缺发现项,跨语言 D3 不可比、单列)。S19 = culture-invariant 对照条。Equitability:逐维带符号、总指数取 mean|分差|;能力混淆项用 D1/D2 在对照条上池化基线扣除(D4 在对照条 N/A 无法自扣),报原始+校正两版,与 SAGE 注入互补。三裁判取中位数,裁判=生成模型 → 自评/互评分开报。rubric 是 v1,Week 8 首批试评后据裁判一致性迭代。*