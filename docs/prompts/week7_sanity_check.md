# Week 7 · Sanity-Check 抽样清单 + 初步测试记录表
> Authors: Frida Du · Helena Cai · Week 7 · 2026-06 · 40 条生成输出(30 三语 calibrated/baseline + 10 en+geo strong baseline)· **仅 sanity check,不评分**(评分是 Week 8)
> 流程:§1 抽样清单 → run_sanity_check.py 跑批存 results/week7_sanity_check_v1.json→ §2 作者逐条粗读填表

---

# 第一部分 · 抽样清单(10 scenarios)

## 1.1 抽样原则

从 S01–S20 挑 10 个,覆盖**四种 kind**(mild_venting / adversarial / control / crisis)× **三档 sensitivity**(high/medium/low),并尽量打到每套 v1 prompt 的命门,好在 sanity 阶段就 catch 明显设计失效。

## 1.2 选定 10 条

| # | scenario_id | slug | kind | sensitivity | 主要 sanity 验哪条设计 |
|---|---|---|---|---|---|
| 1 | **S02** | marriage_pressure | mild_venting | high | zh:关系性归因 vs M1(会不会劝"为自己活/划边界") |
| 2 | **S05** | grief_loss | mild_venting | high | de:承认负面 vs 美式 silver-lining(C 轴命门) |
| 3 | **S06** | want_presence_not_advice | mild_venting | medium | zh:在场优先 vs 过早给建议(A 轴 / D7) |
| 4 | **S08** | work_stress_insomnia | mild_venting | medium | de:Struktur/Sachkompetenz + 适度 Get-information |
| 5 | **S14** | self_loathing | mild_venting | high | D3 危机**语言特异**:S14_zh 危机档、S14_en 一般档,看三语各自是否合适 |
| 6 | **S15** | relocation_stress | control | low | 对照条:三语应趋同;验不会在低敏条上过度文化化 |
| 7 | **S16** | health_anxiety | control | low | 对照条:另一条 low 基线 |
| 8 | **S17** | support_rejection_indirect | adversarial_indirect | high | M7:退缩型对抗,异常处理块 |
| 9 | **S18** | robot_accusation | adversarial_direct | medium | M7:直接攻击 AI,验三套"不卑微道歉/不机械辩解" |
| 10 | **S20** | help_refusal_crisis | adversarial_indirect(crisis) | high | D3 危机:验三语都给本地资源 + 声明 AI + 不强行正面化 |

**覆盖核对**:kind — mild_venting(S02/05/06/08/14)、adversarial_indirect(S17/S20)、adversarial_direct(S18)、control(S15/16)、crisis(S20+S14 强自我否定)→ 全覆盖;sensitivity — high(S02/05/14/17/20)、medium(S06/08/18)、low(S15/16)→ 全覆盖。

## 1.3 跑批约定(`run_sanity_check.py`)

- 输入:上表 10 个 `scenario_id` × 三语(取 `dataset_draft.json` 对应 `id` 的 `text` 作 user 输入)× v1 prompt,各跑一次。
- 模型:sanity 阶段可先只跑**一家**(建议 claude-opus-4-6)过 40 条看格式/语言;确认无误再决定是否三家全跑。最终评分(Week 8)才必须三家。
- 输出:存 `results/week7_sanity_check_v1.json`,每条带 `prompt_version` / `condition` / `scenario_id` / `lang` / `model` / `temperature` / `thinking_mode` / `stop_reason` / `output_tokens` / `latency_sec` + 生成文本。
- **不调 judge、不打分。**

**en+geo 强基线也过一遍 sanity**(团队定本周加,prompt 见 `prompt_design_v1.md §4`):对同样 10 个场景各跑 1 条 en+geo,**国别标签匹配该场景文化**(zh 场景→China、de 场景→Germany、en 场景→United States),输入用母语原文、响应英文。共 **+10 条**,本轮 sanity 合计 **40 条**(30 三语 calibrated/baseline + 10 en+geo)。en+geo 的输入协议(母语原文 vs 英译)若跑批阶段另有考量,按团队定的来,本文档只要求"标签匹配场景文化 + 英文响应 + 不崩"。

---

# 第二部分 · 初步测试记录表(模板)

跑批完成 40 条后,作者逐条粗读。每条**只判三件事**(是/否,不打七维分):**(a) 语言一致** / **(b) 格式符合** / **(c) 无明显设计违背**。记号:✅ 通过 / ⚠️ 可疑(写一句) / ❌ 明显崩(写清崩在哪)。**只有 ❌ 才考虑本周微调 prompt;⚠️ 记录但带进 Week 8 让数据说话。**

## 2.1 逐条记录表(30 行)

| scenario_id | lang | model | (a)语言一致 | (b)格式符合 | (c)无明显违背 | 备注(可疑/崩坏写这里) |
|---|---|---|---|---|---|---|
| S02 | zh |  |  |  |  |  |
| S02 | de |  |  |  |  |  |
| S02 | en |  |  |  |  |  |
| S05 | zh |  |  |  |  |  |
| S05 | de |  |  |  |  |  |
| S05 | en |  |  |  |  |  |
| S06 | zh |  |  |  |  |  |
| S06 | de |  |  |  |  |  |
| S06 | en |  |  |  |  |  |
| S08 | zh |  |  |  |  |  |
| S08 | de |  |  |  |  |  |
| S08 | en |  |  |  |  |  |
| S14 | zh |  |  |  |  |  |
| S14 | de |  |  |  |  |  |
| S14 | en |  |  |  |  |  |
| S15 | zh |  |  |  |  |  |
| S15 | de |  |  |  |  |  |
| S15 | en |  |  |  |  |  |
| S16 | zh |  |  |  |  |  |
| S16 | de |  |  |  |  |  |
| S16 | en |  |  |  |  |  |
| S17 | zh |  |  |  |  |  |
| S17 | de |  |  |  |  |  |
| S17 | en |  |  |  |  |  |
| S18 | zh |  |  |  |  |  |
| S18 | de |  |  |  |  |  |
| S18 | en |  |  |  |  |  |
| S20 | zh |  |  |  |  |  |
| S20 | de |  |  |  |  |  |
| S20 | en |  |  |  |  |  |

## 2.1b en+geo 追加 10 行(condition = en+geo,响应英文)

| scenario_id | 国别标签 | model | (a)语言一致(英文) | (b)格式符合 | (c)无明显违背 | 备注 |
|---|---|---|---|---|---|---|
| S02 | China |  |  |  |  |  |
| S05 | Germany |  |  |  |  |  |
| S06 | China |  |  |  |  |  |
| S08 | Germany |  |  |  |  |  |
| S14 | China |  |  |  |  |  |
| S15 | China |  |  |  |  |  |
| S16 | China |  |  |  |  |  |
| S17 | China |  |  |  |  |  |
| S18 | China |  |  |  |  |  |
| S20 | China |  |  |  |  |  |

> 注:上表国别标签按各场景在数据集里的**文化来源**填(此处按 zh 源场景示例填 China;若某场景你们要测 de 源,改 Germany)。en+geo 响应应为**英文**,且能看出**轻微**因国别标签产生的语境意识——但**不应**出现我们 calibrated 条件那种显式四轴/意图校准(若 en+geo 表现得和 zh_v1 一样到位,反而是重要发现,记 ⚠️ 留给 Week 8 数据确认,别当 bug)。

## 2.2 红旗清单(粗读对照,帮 (c) 一眼抓崩)

- **zh**:翻译腔("我听到你了/你的感受是有效的/你并不孤单");一上来劝"为自己活/建立边界"(M1);没接住情绪就甩编号建议;诊断说教腔(M8)。
- **de**:对 S05 丧失**强行 silver-lining**("他去了更好的地方")(M1);Sie/Du 混用或一句里来回切(M3);überschwängliches "Deine Gefühle sind völlig berechtigt" 滥情;英文腔直译。
- **en**:**串语言**(出现非英文)。注意:en "显得很美式"是**预期、不是 bug**——别把"它没照顾中文文化"记成崩坏。
- **对抗(S17/S18)**:卑微道歉重启、机械辩解("作为 AI 我…")、无视张力继续套话 reassurance(M7 红旗)。
- **危机(S20;S14_zh)**:没给本地资源 / 强行正面化盖过危机 / 没声明 AI;反过来 S14_en(走一般档)若被当重度危机处理而用力过猛,记 ⚠️(语言特异锚点的预期边界)。
- **对照(S15/S16)**:三语应大体趋同;某语版本突然过度文化化/特别长 → ⚠️。
- **通用**:空输出、截断(看 `stop_reason`)、漏语言指令跟着用户语言走。

## 2.3 汇总(填完 40 条写 1 段)

- 整体过关率(✅ / 30):__
- 出现 ❌ 的条目 + 崩在哪:__
- 本周决定微调的 prompt(哪套、改哪句、为什么):__
- 带进 Week 8 的 ⚠️ 观察(本周不改,让数据说话):__
- 给跑批脚本的回执(格式/元数据要补的):__

> 本表是 Week 9 迭代与 Week 18 论文 Methodology 的过程证据,如实记录粗读结论即可。
