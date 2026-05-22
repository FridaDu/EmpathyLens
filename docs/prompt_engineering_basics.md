# Prompt Engineering Basics — EmpathyLens Learning Note
# Prompt 工程基础 — EmpathyLens 学习笔记

Author: Frida Du · Week 4 · 2026-05

本笔记记录 Prompt Engineering 的核心技术,并说明每一项在 EmpathyLens
的三套文化模式 System Prompt 中**用还是不用、为什么**。
This note records core prompt-engineering techniques and explains, for each,
whether and why we use it in EmpathyLens's three cultural-mode System Prompts.

---

## 0. 三种消息角色 | The Three Message Roles

调用 LLM 时,对话由三种 role 组成(你在 Week 2 的 mvp.py 已经见过):
An LLM conversation is composed of three message roles (seen in Week 2's mvp.py):

- **system**:给模型设定身份、任务、规则的"幕后指令"。用户看不到。
  Behind-the-scenes instruction setting the model's identity, task, and rules. Invisible to the user.
- **user**:用户实际说的话(在我们项目里 = 用户的情感倾诉)。
  What the user actually says (in our project = the user's emotional disclosure).
- **assistant**:模型生成的回复。
  The model's generated reply.

**关键点**:我们三套文化模式的差异,全部写在 **system** 里。同一段 user 倾诉,
配不同的 system,就得到不同文化风格的 assistant 回复。这就是整个 MVP 的机制。
Our three cultural modes differ entirely in the **system** message. The same user
disclosure, paired with different system prompts, yields culturally different replies.

---

## 1. 角色设定 | Role Prompting

**是什么**:给模型一个明确身份,它的输出风格会向这个身份收敛。
What it is: Give the model a clear identity; its output converges toward that identity.

**为什么有效**:模型在海量文本上训练,"扮演 X"会激活与 X 相关的语言模式。
Why it works: Trained on massive text, "act as X" activates language patterns associated with X.

**我们怎么用**:✅ 三套 prompt 都以角色定义开头。
How we use it: ✅ All three prompts open with a role definition.
- 中文:"你是一个深谙中文情感表达习惯的陪伴者"
- 德语:"Du bist ein einfühlsamer Begleiter, der die deutsche Gesprächskultur respektiert"
- 英语:"You are a warm, empathetic companion"

---

## 2. 清晰具体的指令 | Clear & Specific Instructions

**是什么**:与其说"温柔一点",不如说"回应宜短,多轮引导,每次只说一两句"。
What it is: Instead of "be gentle," say "keep replies short, guide over multiple turns, one or two sentences each."

**为什么有效**:模型无法读心。模糊指令 → 模型用它的默认(=美式)风格填空。
Why it works: The model can't read minds. Vague instructions → it fills gaps with its default (American) style.

**我们怎么用**:✅ 这是文化校准的核心手段。中文 prompt 不说"含蓄一点",
而是具体规定"不要强迫对方命名情绪""不要用编号列表回应情感倾诉"。
How we use it: ✅ This is the core mechanism of cultural calibration. The Chinese prompt
gives concrete rules rather than vague adjectives.

---

## 3. Few-shot(给范例) | Few-shot Prompting

**是什么**:在 prompt 里塞 1-N 个"理想输入→理想输出"的例子,模型会模仿。
What it is: Embed 1-N "ideal input → ideal output" examples in the prompt; the model imitates.
- Zero-shot = 不给例子,只给指令(我们 v1 用的就是这个)。
  Zero-shot = instructions only, no examples (what our v1 uses).
- Few-shot = 给若干例子。
  Few-shot = give several examples.

**为什么有效**:例子比抽象描述更能锚定模型的输出风格。
Why it works: Examples anchor output style more concretely than abstract description.

**我们怎么用**:⏸️ v1 暂不用,Week 7-9 再加。
How we use it: ⏸️ Not in v1; added in Week 7-9.
原因:加例子会让 prompt 变长、且把模型"锁定"在特定例子上。framework §3.1.5
有现成的三语理想回应范例,留作 Week 7-9 的实验变量(加 few-shot 是否提升效果)。
Reason: examples lengthen the prompt and over-anchor the model. Framework §3.1.5
provides ready-made trilingual ideal-response anchors, reserved as a Week 7-9 variable.

---

## 4. Chain-of-Thought(思维链) | Chain-of-Thought (CoT)

**是什么**:让模型"先分步推理,再给结论",而不是直接跳到答案。
What it is: Make the model "reason step-by-step, then conclude" rather than jumping to an answer.

**为什么有效**:对复杂任务,显式推理能提升质量。framework §6.2 的四步链
(情感分析→意图推断→策略选择→响应生成)就是 CoT 思路。
Why it works: For complex tasks, explicit reasoning improves quality. Framework §6.2's
four-step chain is a CoT design.

**我们怎么用**:⏸️ v1 不用显式 CoT。
How we use it: ⏸️ No explicit CoT in v1.
原因(重要):我们 Week 2 已关闭 thinking 模式(模拟主流产品的实时部署)。
thinking 关闭时模型没有"内心独白"空间,显式 CoT 要么把推理全打印出来
(不符合陪伴回应),要么被跳过。所以 v1 把四步链的意图**编码成行为准则**,
而非显式推理步骤。"四步链 vs 单步" 的对比正是 framework §6.2 预设的 Week 7-9 实验。
Reason: We disabled thinking mode in Week 2 (to mirror real product deployment). With
thinking off, the model has no hidden-reasoning space, so explicit CoT either prints all
reasoning (unfit for a companion reply) or gets skipped. So v1 encodes the chain's intent
as behavioral guidelines. The "chain vs single-step" comparison is exactly the Week 7-9
experiment framework §6.2 anticipates.

---

## 5. 结构与分隔符 | Structure & Delimiters

**是什么**:用标题、符号(如【】、###)把 prompt 切成清晰的段落。
What it is: Use headers/symbols (【】, ###) to split the prompt into clear sections.

**为什么有效**:结构化的 prompt 让模型更容易分辨"规则""要避免的""底线"。
Why it works: Structured prompts help the model distinguish rules, things to avoid, and bottom lines.

**我们怎么用**:✅ 三套 prompt 都用【】标出规范模块和"绝对要避免""共同底线"。
How we use it: ✅ All three prompts use 【】 to mark norm modules and the avoid / baseline sections.

---

## v1 的技术选择小结 | v1 Technique Choices Summary

| 技术 Technique | v1 是否使用 Used in v1 | 备注 Note |
|---|---|---|
| 角色设定 Role | ✅ 是 Yes | 三套都用 |
| 清晰指令 Clear instructions | ✅ 是 Yes | 文化校准核心 |
| 结构/分隔符 Structure | ✅ 是 Yes | 【】分段 |
| Few-shot | ⏸️ 否 No | Week 7-9 实验变量 |
| 显式 CoT | ⏸️ 否 No | 与 thinking 关闭冲突;Week 7-9 对比 |