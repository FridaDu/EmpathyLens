# EmpathyLens 标注指南 v1 (Annotation Guidelines)

> Authors: Frida Du, Helena Cai · Week 5 · 2026-06
> 配套:`scenario_design_table_v1.md`(设计真相源)· `data/dataset_draft.json`(数据集)

---

## 0. 这份指南做什么 | Purpose

给两位标注者统一的判据,保证标注一致性(用 Cohen's Kappa 量化)。
**v1 聚焦本周 Kappa 实测的两个字段:`emotional_intensity` 和 `cultural_sensitivity`。**
其余字段(M1–M8 失配标注、四轴)是 Week 7+ 的深度标注,本指南只在 §6/§7 列作参考。

---

## 1. 核心原则:type-parallel ≠ 互译 | Type-parallel, NOT translation

- 20 个情境**类型**三语共享,但每条文本由母语者**原生撰写,不互译**(framework §4.2)。
- 维系"是同一场景"的是**元数据**(`scenario_id` + 场景级字段),**不是字面文本**。
- 标注时记住:同一个 `scenario_id` 的 zh/de/en 是"同一种情境的三个母语版本",彼此不是翻译。

---

## 2. 数据集结构速览 | Dataset at a glance

- 60 条 = 20 场景(S01–S20)× 3 语(zh/de/en)。
- **已填**:`text`、场景级字段(`scenario_type / kind / stressed_axes / framework_anchor`)、`ideal_norm_direction / ideal_intention / watch_mismatches`。
- **待标(本指南目标)**:`emotional_intensity`、`cultural_sensitivity`。

---

## 3. ★ emotional_intensity(情感强度,1–5)—— 本周 Kappa 标的

**判据**:这段倾诉**实际传达**的情绪痛苦 / 紧迫程度。**只读文本判**,不看场景"本应多严重"。

| 档 | 含义 | generic 示例(仅示意,非数据集条目) |
|---|---|---|
| 1 | 平静,几乎无情绪,陈述性 | "下周要搬去新城市,还在慢慢收拾。" |
| 2 | 轻度困扰 / 日常烦躁 | "今天又被催进度,有点烦。" |
| 3 | 明显负面情绪,但仍在掌控 | "最近压力好大,晚上总睡不好,有点扛不住。" |
| 4 | 强烈痛苦 / 激动 / 自我否定 | "我觉得自己什么都做不好,越想越难受。" |
| 5 | 极端痛苦 / 绝望 / 危机信号 | "我真的撑不下去了,不知道还有什么意义。" |

**判定提示**:看情绪词强度、是否有无助/绝望表达、是否出现危机信号;**不要**被"这个场景应该很严重"带偏,只评这条文本写出了多少。

> **来源说明**:framework **未定义**情感强度量表。这套 1–5 分档是**本项目的标注构件**(schema `INTENSITY_RANGE=(1,5)` + 本指南的档位定义),是方法论选择,由团队自行 own / 评审,不是从 framework 抄来的。

---

## 4. ★ cultural_sensitivity(文化敏感度,high / medium / low)—— 本周 Kappa 标的

**判据**:在这个**情境类型**下,中 / 德 / 英三种文化各自"理想的回应"**分歧有多大**。
这是**场景级**判断 —— 读任一语言版本都能判,因为它问的不是"这条文本多有文化味",而是"理想回应跨文化差多少"。

| 档 | 含义 |
|---|---|
| high | 三语理想回应**分歧大**(诊断核心):一个理想的中文回应、德文回应、英文回应会明显不同。 |
| medium | 有分歧,但不算大。 |
| low | 分歧小,三语理想回应**基本趋同**(equitability 对照组)。 |

**判定方法**:设想"针对这个情境,最理想的中文 / 德文 / 英文回应分别长什么样"——三者差异越大越靠 high,越接近越靠 low。

**注意**:判的是"**理想回应的跨文化分歧**",不是"这条文本本身多有文化特色"。

> **来源说明**:`cultural_sensitivity`(场景级、三语理想回应分歧度)是**本项目的设计构件**(见设计表),**不同于** framework §5.6 的"失配严重度"(High/Medium/Low/Marginal —— 那是对**某条实际回应**里失配的严重度评级,Week 7+ 才用)。两者别混。

---

## 5. 盲标协议(Kappa 流程)—— 必须严格遵守

1. 两人**各自独立**填 `annotations/frida.csv` 与 `annotations/helena.csv`:**不商量、不看对方、不看 JSON 里任何草拟值**。
2. 试标 **10 条**,用 **zh 版**(两人都中文母语,理解力对等)。
3. 填完跑 `python -m src.compute_kappa annotations/frida.csv annotations/helena.csv`。
   - `emotional_intensity`:**加权** Cohen's Kappa(相邻档分歧惩罚小)。
   - `cultural_sensitivity`:普通 Cohen's Kappa。
4. **结果处理**:
   - Kappa **< 0.6**:一起看分歧条 → 找出本指南哪一档**判据模糊** → 修订 §3/§4 的定义 → 重标。
   - Kappa **≥ 0.6** 可接受,**≥ 0.8** 良好。
5. 达标后,把两人 reconcile 的最终 `intensity / sensitivity` 回填进 `dataset_draft.json`。

---

## 6. M1–M8 失配分类(framework §5.5)—— 参考,Week 7+ 才标

现在**不标**,只是写文本 / 读 `watch_mismatches` 时心里有数:

- **M1** 价值预设错位:用一种文化的核心价值默认另一种(如强行正面化、个体主义归因)
- **M2** 文化空缺(Cultural Vacancy):对目标文化特有概念无表征(想开/看淡/缘分/Schadenfreude)
- **M3** 语体 / 敬语错位(德语 Du/Sie 误用、中文翻译腔或不当口语化)
- **M4** 关系动态忽视:对不同关系(朋友↔长辈↔陌生人)用同一策略
- **M5** 意图层错位:策略对但底层意图错(中文场景误用 Change/Self-control 而非 Cathart/Support/Preserve-Face)
- **M6** 时机错位:策略对但用错对话阶段(中文过早进入 Action;德语过晚进入结构化)
- **M7** 对抗性场景退化:遇抗拒/愤怒退回模板(重复 reassurance/problem-solving,缺文化特异的 tension-naming)
- **M8** 西方临床框架越界:把西方危机干预/诊断标准直接套用;过度 reasoning 让用户感到被审视

---

## 7. 失配 vs 能力(framework §5.8)—— 判别法,Week 7+

区分"**文化失配**"(模型有能力,但没恰当运用文化规范)和"**能力不足**"(任何文化下都做不好)。
framework §5.8 的判别法是 **SAGE 三级注入对比**(Zero / Weak / Strong injection):
- **Zero injection**(不告知任何文化规范)测模型自发的文化适配;
- **Strong injection**(注入完整文化规范)后再测;
- 强注入后失配**消失** → "懂但不会用"的**运用困难**(真正的文化失配,Sub-RQ 2 的 Prompt 工程有作用空间);
- 强注入后**仍失配** → **能力不足或表征缺失**(Cultural Vacancy)。

(低敏感度对照组 S15/S16 是 §5.7 Equitability 的对照 sanity check,**不是** §5.8 的核心判别法 —— 别混淆。)

---

*v1 will be revised after the first Kappa run (per §5.4). 一致性差的档位定义会据 Kappa 结果修订。*
