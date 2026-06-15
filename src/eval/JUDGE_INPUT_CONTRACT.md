# Week 8 LLM-as-a-Judge · IO 契约（提前可见，本周只文档不写代码）

Authors: Frida Du · Helena Cai · Week 7 · 2026-06。目的:让 Week 7 的 sanity 产物格式与 Week 8 run_judge.py 的输入预期**提前对齐**,避免下周返工。本文件**不写 judge 代码**(judge 是 Week 8),只钉死 IO schema。

放置:`src/eval/JUDGE_INPUT_CONTRACT.md`。

---

## 1. 数据流总览

```
generation (Week7 sanity / Week8 full)        evaluation (Week8 run_judge.py)
  results/<run>.json  ──────────────►  loader ─► assemble_judge_input ─► 3 judges
   (responses + 生成元数据)              join dataset_draft.json          median
                                                                          │
                                         results/scores_<run>.json ◄──────┘
```

- **被评对象**来自 `results/`(本周 = `week7_sanity_check_v1.json`;Week 8 = 正式跑批,三家模型 × 四条件 × N 次采样)。
- **评分标尺**来自 `src/eval/rubrics.py` + `assemble_judge_input.py`(已建)。
- judge **join** 数据集元数据靠 `(scenario_id, lang)` → `dataset_draft.json` 里 `id = f"{scenario_id}_{lang}"`。

---

## 2. run_judge.py 的【输入】schema（= 生成脚本的输出，每条一个响应）

每条响应记录至少含以下字段(`run_sanity_check.py` 已按此写出):

| 字段 | 类型 | 说明 | judge 用途 |
|---|---|---|---|
| `prompt_version` | str | `"v1"` | 记录,scores 回写 |
| `condition` | str | `zh`/`de`/`en`/`en_geo` | 决定**目标文化**(见 §3) |
| `scenario_id` | str | `S02`… | join key |
| `lang` | str | 输入文本语言(en_geo=源文化语言) | join key |
| `geo` | str\|null | en_geo 的国别码,否则 null | 决定 en_geo 目标文化 |
| `user_text` | str | 用户倾诉 | 拼进 judge 输入 |
| `response_text` | str | **被评模型响应** | 拼进 judge 输入 |
| `model` | str | 生成模型(Week8 三家之一) | self-vs-cross 判定 |
| `temperature` / `thinking_mode` / `stop_reason` / `output_tokens` / `latency_sec` | — | 生成元数据 | 记录/质检(空输出、截断) |

> Week 8 正式跑批会在每条上再加 `run_index`(重复采样第几次,§3 methodology)。sanity 阶段 N=1,无此字段。

---

## 3. 目标文化解析（condition → judge 的 target culture）

assemble_judge_input 需要"这条响应该按哪种文化的理想评 D4/D5"。映射规则:

| condition | 用于 join 的 dataset 记录 | 目标文化(D4/D5 评分基准) |
|---|---|---|
| `zh` | `{sid}_zh` | 中文理想(dataset 的 zh `ideal_norm_direction` 等) |
| `de` | `{sid}_de` | 德语理想 |
| `en` | `{sid}_en` | 美式基线(assembler 已把"未校准基线"翻成 de-facto 目标) |
| `en_geo` | `{sid}_{geo}` | **该国别对应文化**(zh 场景的 en_geo 按**中文理想**评,看它靠国家标签贴到几分) |

注意 en_geo 的 join 用 `geo` 语言(源文化),不是 `en`——这正是"标签能否替代显式校准"的检验点(prompt_design_v1.md §4.5)。

---

## 4. run_judge.py 的【输出】schema（scores 回写）

`results/scores_<run>.json`,**评分单元 = (一条响应 × 一个维度 × 一个 judge)**:

```json
{
  "scenario_id": "S02", "lang": "zh", "condition": "zh",
  "prompt_version": "v1", "gen_model": "claude-opus-4-6", "run_index": 0,
  "dimension": "D4",
  "judge_model": "gpt-5.4",
  "score": 2, "markers": ["..."], "justification": "...",
  "applicable": true,
  "self_judge": false
}
```

聚合规则(写进 scores 或单独 `scores_agg`):
- **三家裁判取中位数**;记录三家分歧(>1 分人工抽查)。
- **self_judge 标志**:`judge_model == gen_model` → True。按 Week 6 决策**自评/互评分开报**(不丢数据,不留一)。
- `applicable=false`:N/A 维度(空轴 D4 等),不进 Equitability 文化分差。
- **强制输出契约**:judge 先列 `markers` 再给 `score`(抑制宽松偏差)。

---

## 5. Week 8 要补的两个小工具（本周只挂号，不写）

1. `src/eval/run_judge.py`:loader(读 §2)→ 对每条响应 × 每维 `assemble_judge_input.assemble()` → 三家 `llm_client.call_model` → 解析 JSON 打分 → 写 §4。
2. `src/eval/aggregate_equitability.py`:从 scores 算 §6 Equitability——**per-dim 带符号**、总指数 `mean(|分差|)`、**D1/D2 池化能力基线**扣除;跳过 S14 的 D3(跨语言不可比)与 S19 的 D4/D5(culture-invariant)。

---

## 6. 本周边界

本文件是**契约文档**,不是实现。Week 7 只保证 `run_sanity_check.py` 的输出**字段齐、命名稳**,使 Week 8 的 `run_judge.py` 能零改动地吃它。判分逻辑、三家循环、Equitability 聚合都是 Week 8。
