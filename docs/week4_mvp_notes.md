# Week 4 MVP — 研究决策笔记

> 配套文档:`methodology_notes.md` · `prompt_engineering_basics.md`
> 程序入口:`src/cli/empathy_cli.py`
> 测试数据:`src/tests/test_inputs.py`
> 输出位置:`results/mvp_run_<YYYYMMDD_HHMMSS>.json`

本文档记录 Week 4 MVP 在 prompt、测试输入、输出格式上的关键设计决策,以便 Week 5+ 迭代时溯源。

## 1. 三种文化模式的定位

| 模式 | 状态 | 依据 |
| --- | --- | --- |
| `zh` | **文化校准**(深度版) | framework §3.1 五条规范 + 轴 A/B/C/D 定位 |
| `de` | **文化校准**(扎实初稿) | framework §3.2 五条规范 + §3.2.2 短句与 Konjunktiv II |
| `en` | **未文化校准 baseline**(有意为之) | framework §3.3.2 方法论警示 |

**关键点**:English 模式**不是"标准答案"**,而是主流产品默认的、未校准的美式风格,用于 Phase 2 测量 Equitability 二阶指标(§5.7)。这一点在 `cultural_prompts.py` 头部注释和 CLI 终端输出标签(`🇺🇸 English (uncalibrated baseline)`)中都明确标记,防止后续工作中被误读。

## 2. 5 条测试输入的设计依据

每条都锚定到 framework 的具体段落,**不是互译**(framework §4.2 明确说对抗性文化线索机器翻译/LLM 改写无法保留):

| ID | 语言 | 类型 | framework 锚点 | 测什么 |
| --- | --- | --- | --- | --- |
| T1 | 中 | 温和倾诉 | §3.1.2 / §3.1.5 关系性归因 | 妈妈催相亲 → 关系性 vs 个体归因 |
| T2 | 中 | **对抗性间接** | §4.2 indirect adversarial | "算了,你不会懂的" → 是否退回模板(M7 失配) |
| T3 | 德 | 温和倾诉 | §3.2.4 失眠 + 工作压力 | 是否承认负面 + 结构化询问,而非快速 sleep hygiene 建议 |
| T4 | 德 | **对抗性直接** | §4.2 direct adversarial | "Du klingst wie ein Roboter" → Sie/Du 礼貌层级是否保持 |
| T5 | 英 | 温和倾诉 | §3.1.5 分手案例 | 跨模式对比:EN baseline 快速 reframe + 转介 vs ZH/DE 校准 |

混合温和与对抗的理由(framework §4.2):**HEART(Iyer et al. 2026)证明失配在温和场景被表面共情掩盖,只有对抗性才能暴露**。所以即使是 Week 4 的 MVP 阶段,也必须包含至少 2 条对抗性测试,否则就把 prompt 效果"测假"了。

## 3. 输出 JSON 格式 —— Phase 2 评估管道可直接消费

`results/mvp_run_<时间戳>.json` 顶层是 list,每条记录字段:

| 字段 | 说明 |
| --- | --- |
| `user_text` | 原始输入文本 |
| `timestamp_utc` | ISO 8601 时间戳 |
| `prompt_version` | 来自 `cultural_prompts.py` 的 `PROMPT_VERSION`(目前 `v1`) |
| `model` · `temperature` | 实验配置 |
| `responses` | `{mode: {response_text, model, temperature, max_tokens, stop_reason, input_tokens, output_tokens, latency_sec}}` |
| `test_item` | 测试元数据:`id` / `lang` / `kind` / `anchor`(framework 段落引用)/ `note` |

**为什么这么设计**:
- `prompt_version` 让 Week 7+ 做 prompt 迭代时旧记录仍可溯源
- `test_item.anchor` 让评估时能追溯回 framework 的具体规范,不会失去理论根基
- 单条 record 自包含(含所有元数据 + 输入 + 输出),不需要再 join 别的表

## 4. 关键代码决策

- **Temperature 默认 0.7**,Week 7-9 做消融时经 `--temperature` 切换。
- **`max_tokens=600`**:比典型聊天长,但留出完整情感响应的空间(尤其是 zh 模式的多轮短回应风格)。
- **API 失败容错**:单条 mode 出错只写 `error` 字段,batch 不会中断 —— 跑 5 × 3 = 15 次调用,任何一次失败都不影响其它结果。
- **`call_model` 延迟导入 `anthropic`**:这样即使组员没装 SDK / 没设 API key,也能用 CLI 检查 prompt 内容。
- **`run_one_input` 与 `main` 分离**:Week 5+ 写评估脚本时可以直接 `from src.cli.empathy_cli import run_one_input`,不必走 CLI。

## 5. 单步 prompt vs 四步显式推理链(留待 Week 7-9)

v1 采用**单步"准则"形式**的 prompt,而非 framework §6.2 的显式四步推理链,因为生成阶段已关闭 thinking 模式(Week 2 决策)。

四步链 vs 单步的对比消融是 framework §6.2 已经预期的 Week 7-9 任务,届时需要:
- 写一个 v2 prompt(显式四步链)
- 跑同一测试集对比
- 把对比结果写进论文 Discussion

## 6. 不在 Week 4 范围内的事

为避免范围蔓延,以下明确**留到后续 week**:
- ❌ 评估逻辑(Sub-RQ 1 失配诊断、HEART 五维评分)→ Week 7+
- ❌ SAGE 三级注入(Zero / Weak / Strong)的诊断范式 → Week 7-9
- ❌ 60 条三语测试集设计 → Phase 1(Week 7-9)
- ❌ 主流产品对比(GPT-4o / DeepSeek / Qwen)→ Week 5+
- ❌ pytest 单元测试 → 需要时另开项目根 `tests/` 目录,不与 `src/tests/`(测试数据)冲突
