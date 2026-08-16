# LLM-as-a-Judge · IO 契约（Week 9 风控重写版）

Authors: Frida Du · Helena Cai · Week 7（首版）· Week 9（本次修订：反映合并调用后的新结构）

Week 9 变更提要：评分【调用】单元从"响应 × 维度 × 裁判"合并为"响应 × 裁判"（单次调用
一次性返回七维 JSON），调用量降至约 1/7；但评分【输出行】schema 保持"响应 × 维度 × 裁判"
不变（§4），因此 `aggregate.py` 等下游消费者不需要任何改动——已用真实数据验证过。

放置：`src/eval/JUDGE_INPUT_CONTRACT.md`。

---

## 1. 数据流总览

```
generation (sanity / 全量)              evaluation (run_judge.py, Week 9 结构)
  results/<run>.json  ──────────────►  loader ─► assemble_all（单次覆盖全部可评维度）
   (responses + 生成元数据)                          │
                                          三家裁判各调用一次 ─► 展开为逐维度行
                                                                          │
                                         results/scores_<run>.json ◄──────┘
```

- **被评对象**来自 `results/`（如 `full_gen_v1.json`，或 Tier 1/2 场景下的
  `week7_sanity_check_v1.json`）。
- **评分标尺**来自 `src/eval/rubrics.py` + `assemble_judge_input.py`。
- judge **join** 数据集元数据靠 `(scenario_id, lang)` → `dataset_draft.json` 里
  `id = f"{scenario_id}_{lang}"`。

---

## 2. run_judge.py 的【输入】schema（= 生成脚本的输出，每条一个响应）

每条响应记录至少含以下字段：

| 字段 | 类型 | 说明 | judge 用途 |
|---|---|---|---|
| `prompt_version` | str | `"v1"` | 记录,scores 回写 |
| `condition` | str | `zh`/`de`/`en`/`en_geo` | 决定**目标文化**(见 §3) |
| `scenario_id` | str | `S02`… | join key |
| `lang` | str | 输入文本语言(en_geo=源文化语言) | join key |
| `geo` | str\|null | en_geo 的国别码,否则 null | 决定 en_geo 目标文化 |
| `user_text` | str | 用户倾诉 | 拼进 judge 输入 |
| `response_text` | str | **被评模型响应** | 拼进 judge 输入 |
| `gen_model` **或** `model` | str | 生成模型 | self-vs-cross 判定（见下方 ⚠️ 字段名说明） |
| `run_index` | int，可选 | 重复采样第几次；缺省视为 0 | scores 回写 |
| `temperature` / `thinking_mode` / `stop_reason` / `output_tokens` / `latency_sec` | — | 生成元数据 | 记录/质检 |

> ⚠️ **字段名不一致（Week 9 发现，已在 `run_judge.py` 里做兼容，未改动既有数据文件）**：
> 本文档 Week 7 版原写的字段名是 `model`，`week7_sanity_check_v1.json`（`run_sanity_check.py`
> 的输出）也确实用 `model`；但 `full_gen_v1.json`（全量生成脚本的输出）用的是 `gen_model`。
> `run_judge.py` 现在会依次尝试 `gen_model` → `model`，两种命名都能吃，`run_index` 缺失时
> 按 0 处理（对齐 sanity 阶段 N=1、无重复采样的情况）。**建议后续统一生成脚本的字段命名**
> （在本文档里挑一个定为唯一标准，另一个改成别名或废弃），这条兼容逻辑只是权宜之计。

---

## 3. 目标文化解析（condition → judge 的 target culture）与响应语言解析

assemble_all 需要两个独立的信息（Week 9 起明确拆开，见下方 ⚠️）：

| condition | 用于 join 的 dataset 记录 | D4/D5 评分基准（目标文化） | D6 评分基准（响应实际语言） |
|---|---|---|---|
| `zh` | `{sid}_zh` | 中文理想 | 中文 |
| `de` | `{sid}_de` | 德语理想 | 德语 |
| `en` | `{sid}_en` | 美式基线(assembler 已把"未校准基线"翻成 de-facto 目标) | 英语 |
| `en_geo` | `{sid}_{geo}` | **该国别对应文化**(zh 场景的 en_geo 按**中文理想**评,看它靠国家标签贴到几分) | **恒为英语**（`registry.py` 的 `_EN_GEO_V1`: "Always respond in English"） |

> ⚠️ **en_geo 的 D6 语言画像 bug（Week 9 修复）**：旧版 `assemble()` 只把 join 后的目标
> 文化记录的 `lang` 字段喂给裁判做全部维度（含 D6）的语言/文化框定，对 en_geo 而言这个
> `lang` 是 geo 对应的中文/德文——但 en_geo 响应实际恒为英文。裁判被告知"这应该是中文"
> 却看到英文响应，把 D6（语言自然度）系统性打到 1.3~1.5（Week 8 数据复核发现，三家模型
> 上高度一致，是典型的测量伪影而非真实的语言质量问题）。新版 `assemble_all()` 拆成
> `response_lang`（D6 依据，en_geo 恒为 "en"）与 `record.get('lang')`（D4/D5 依据，
> en_geo 时仍是 geo 对应文化）两个独立字段，互不污染。zh/de/en 三条件下两者本就一致，
> 不受影响。**Week 9 用小样本子集重评后，应重点核对 en_geo 的 D6 分数是否回升到合理区间
> ——这是判断"标签能否唤出目标文化"这一研究问题的一个必要前提清理，不是终点。**

---

## 4. run_judge.py 的【输出】schema（scores 回写，Week 9 未变）

`results/scores_<run>.json`，**评分单元 = (一条响应 × 一个维度 × 一个 judge)**——
注意这是【输出行】的粒度，不是【调用】的粒度（调用粒度见 §5）：

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

聚合规则（`aggregate.py`，未改动）：
- **三家裁判取中位数**；记录三家分歧(>1 分人工抽查)。
- **self_judge 标志**：`judge_model == gen_model` → True。
- `applicable=false`：N/A 维度（空轴 D4 等），不进 Equitability 文化分差。

---

## 5. 【Week 9 新增】评分【调用】的合并结构

- 单次裁判调用覆盖【一条响应的全部可评维度】（自动排除 N/A，如空轴 D4），而非逐维度单独
  调用。原始用户倾诉文本、文化上下文块在一次调用里只出现一次（而非随维度数重复 7 次）。
- 裁判被要求输出**一个 JSON 对象**，顶层键为该次要求评分的维度代号（如 `"D1"`,`"D2"`…），
  每个键对应 `{"markers": [...], "score": 1-5, "justification": "..."}`。
- `run_judge.py` 解析后**展开**成 §4 描述的逐维度行——所以 `aggregate.py` 完全不需要
  改动，已用真实数据验证。
- **断点续跑**按"该(响应×裁判)组合是否还有缺失维度"判断：若有，发起（一次）调用补齐所有
  缺失维度；若该组合下所有维度都已完成，跳过，不重复调用。

---

## 6. 【Week 9 新增】分级评估协议（Tier 1/2/3）

| Tier | 数据范围 | 裁判 | 何时用 |
|---|---|---|---|
| 1 | `TIER_SUBSET_SCENARIOS`（10 条，同 `week7_sanity_check.md` §1.2） | 单裁判（默认 deepseek-v4-pro） | Prompt 改动后第一步冒烟 |
| 2 | 同上 10 条 | 三裁判 | Tier 1 通过后定量确认 |
| 3 | 60 条全量 | 三裁判 | 论文最终数据，计划内仅执行一次，强制要求 `--balance-checked` |

`--tier 1`/`--tier 2` 会自动把 `--gen` 指向的文件过滤到这 10 条 `scenario_id` 范围内，
不论来源文件本身覆盖了多少条——对已经只含 10 条的 `week7_sanity_check_v1.json` 是无害的
幂等操作。

---

## 7. 【Week 9 新增】预算与节流

- 单次跑批硬顶 `--max-cost-eur`，按日累计硬顶 `--daily-cap-eur`（基于本地
  `results/.budget_ledger.json` 台账）——两者都是**强制拒绝，无绕过参数**。
- `--sleep-sec` 控制每次调用后的强制间隔（不论成功失败），默认 1.5 秒。
- Tier 3 必须显式传 `--balance-checked`（代表已人工登录三家平台后台核对过实时余额），
  否则拒绝启动。
- ⚠️ 预算台账目前基于字符数估算成本，不是 provider 返回的真实 token 用量（`llm_client`
  尚未返回 usage 字段）。团队仍需坚持每周六 checkpoint 的三家后台余额人工核对，不要只信任
  台账数字。

---

## 8. 本次修订边界

Week 9 只重写了 `run_judge.py` / `assemble_judge_input.py` / 新增 `budget_ledger.py`，
`aggregate.py` / `week8_plots.py` 未改动（已验证兼容）。`PRICING` 常量仍是估算占位符，
需要团队用三家平台真实账单校准后才能视为可信——这是这次重写唯一没有能力独立完成的一步。
