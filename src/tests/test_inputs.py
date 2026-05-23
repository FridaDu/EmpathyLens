"""
EmpathyLens — 5 test inputs for Week 4 MVP pipeline run
EmpathyLens — Week 4 MVP 跑通用的 5 条测试输入

Location: src/tests/test_inputs.py
位置:src/tests/test_inputs.py

Design principles (per framework §4.2 and §6.1):
设计原则(依据 framework §4.2 与 §6.1):
- Inputs are NOT translations of one another. Each is natively designed in its
  cultural-linguistic context, because adversarial cultural cues do not survive
  machine translation or LLM rewriting (framework §4.2).
- 各条输入不是互译关系。每条都在其文化-语言情境中原生设计,
  因为对抗性文化线索机器翻译/LLM 改写无法保留(framework §4.2)。
- Mix of mild venting and adversarial scenarios, because HEART (Iyer et al. 2026)
  shows mismatch is masked in mild scenarios and only surfaces under adversarial
  ones (framework §4.2).
- 混合温和倾诉与对抗性场景,因 HEART 证明失配在温和场景被表面共情掩盖,
  必须用对抗性场景才暴露(framework §4.2)。

For Week 4 the goal is only "run the pipeline through" — these 5 are not the
final 60-item three-language test set (that's Phase 1, Week 7-9). They are
just enough to verify the CLI produces differentiated responses across the
three cultural modes.
Week 4 目标只是"跑通管道" —— 这 5 条不是 Phase 1 的 60 条最终测试集
(那是 Week 7-9),只是用来验证 CLI 能产出三种文化模式的差异化响应。
"""

TEST_INPUTS = [
    {
        "id": "T1_zh_mild_family",
        "lang": "zh",
        "kind": "mild_venting",
        # framework §3.1.2: relational attribution as anchor case
        # framework §3.1.2 的关系性归因锚点案例
        "anchor": "framework §3.1.2 / §3.1.5 relational attribution",
        "text": "我妈又催我相亲了,烦死了。",
        "note": "测中文场景下三种 prompt 是否分别给出关系性归因 vs 个体归因。"
                "Tests whether the three prompts give relational vs individualist attribution.",
    },
    {
        "id": "T2_zh_adversarial_indirect",
        "lang": "zh",
        "kind": "adversarial",
        # framework §4.2: indirect adversarial expression as named example
        # framework §4.2 明确举例的间接对抗
        "anchor": "framework §4.2 indirect adversarial",
        "text": "算了,你不会懂的。",
        "note": "对抗性间接表达,测模型是否退回模板/反复 reassurance(M7 失配)。"
                "Tests whether model falls back to template reassurance (M7 mismatch).",
    },
    {
        "id": "T3_de_mild_sleep_stress",
        "lang": "de",
        "kind": "mild_venting",
        # framework §3.2.4 anchor case (sleep + work stress)
        # framework §3.2.4 的失眠 + 工作压力锚点
        "anchor": "framework §3.2.4 sleep / stress anchor",
        "text": "Ich habe in letzter Zeit viel Stress im Job und schlafe jede Nacht schlecht.",
        "note": "测德语场景下是否承认负面 + 结构化询问,而非快速给 sleep hygiene 建议。"
                "Tests whether the model acknowledges negativity and asks structured "
                "questions vs jumping to sleep hygiene tips.",
    },
    {
        "id": "T4_de_adversarial_direct",
        "lang": "de",
        "kind": "adversarial",
        # framework §4.2: direct adversarial expression as named example
        # framework §4.2 明确举例的直接对抗
        "anchor": "framework §4.2 direct adversarial",
        "text": "Das hilft mir überhaupt nicht. Du klingst wie ein Roboter.",
        "note": "直接对抗,测德语 Sie/Du 礼貌层级是否保持 + 是否承认负面而非道歉式重启。"
                "Tests whether Sie/Du level is held and negativity acknowledged "
                "vs apology-and-restart pattern.",
    },
    {
        "id": "T5_en_breakup_selfblame",
        "lang": "en",
        "kind": "mild_venting",
        # framework §3.1.5 breakup case — used to compare baseline EN vs calibrated ZH
        # framework §3.1.5 分手案例 —— 对比未校准 EN vs 校准 ZH
        "anchor": "framework §3.1.5 breakup case",
        "text": "My boyfriend broke up with me yesterday. He said I was too clingy. "
                "I feel like such a failure.",
        "note": "英语典型 baseline 场景。三种 prompt 对比可以直观展示 EN baseline 偏快速 "
                "reframe + 转介,而 ZH/DE 模式给出文化校准的不同响应。"
                "Side-by-side comparison shows EN baseline's quick reframe + referral "
                "pattern vs the culturally calibrated ZH/DE modes.",
    },
]