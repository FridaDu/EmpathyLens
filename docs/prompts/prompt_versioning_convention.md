# EmpathyLens · Prompt 版本约定 (Prompt Versioning Convention)
> Authors: Frida Du · Helena Cai · Week 7 · 2026-06
> 一页定死:版本号、每版绑什么、技术侧接口 schema。

---

## 1. 为什么要这个约定

Week 4 的 `cultural_prompts.py` 文件头自称 `PROMPT_VERSION = "v1"`,但它其实是未经评估的 pilot。一旦 Week 8 开始正式评估、Week 9 数据驱动迭代,如果版本号含糊,"这张分数是哪版 prompt 跑的"就会变成一笔糊涂账,直接污染论文的可复现性。本约定把版本号从本周立住,**每一张实验分数都能回溯到唯一一版 prompt 文本 + 一份设计说明**。

---

## 2. 版本号阶梯

| 版本 | 时点 | 含义 | 状态 |
|---|---|---|---|
| `v0.1`(及 `v0.x`) | Week 4 | 非正式 pilot。当前 `cultural_prompts.py` 的三套(zh 深度 / de 初稿 / en baseline)。**未经七维评估**,仅用于跑通管道。 | 归档,不再评估 |
| `v1` | **Week 7(本周)** | **首个正式评估版**。zh/de 用 Week 6 七维框架 + §3.0 四轴 + §5.4 意图簇 + §5.5 M码反向规约,深化为 calibrated;en 保持 §3.3.2 未校准基线(只做格式整理)。 | **本周锁定**(de 待母语审校前记 `de_v1-draft`) |
| `en+geo` | **Week 7(本周,团队定加)** | framework §6.2 要求的**强基线**:英文 prompt + 国家情境标签(如 "You live in Germany")。回应 CuLEmo Finding 3。prompt 模板见 `prompt_design_v1.md §4`。 | **本周锁定** |
| `v2` | Week 9 | 据 Week 8 评估数据迭代。 | 待产 |
| `v2+rag` | Week 10 | 在 v2 基础上挂轻量 RAG(检索增强)。 | 待产 |

**写法规范**:版本字符串恒为短横线无空格的 `v0.1` / `v1` / `v2` / `v2+rag`。en 即使不深化也随大版本号走(en 的 `v1` = "格式与 zh/de 平齐、但有意未校准"的基线版),保证三语同版号可比。

---

## 3. 每个版本必须绑定的两样东西

1. **一份设计说明**(三语合并一份,便于对照):`docs/prompts/prompt_design_{version}.md`。结构:总原则 → 每语(理论依据 → prompt 全文 → 五块逐条 → 七维对齐表 → 局限)→ 三套共享与差异 → framework 合规自查。本周交付 `prompt_design_v1.md`（含 zh/de/en/en_geo 四套权威 prompt 文本,源代码同步内嵌于 `src/prompts/registry.py`)。
2. **一条变更日志条目**:集中记在 `docs/prompts/CHANGELOG.md`(每次升版追加一行:版本号、日期、改了什么、依据哪份评估数据)。v1 这条由本周落:"v1 = 首个正式评估版,zh/de calibrated,en uncalibrated baseline,依据 framework_CN_v2 + evaluation_dimensions_v1.1"。

**source of truth 规则**：prompt 的权威文本只存一处 = `src/prompts/registry.py` 的内嵌常量（或未来版本可能采用的 `src/prompts/{version}/{lang}` 文件）。设计说明里的 prompt 文本块是**该权威文本的副本 + 注解**，改 prompt 必须先改权威文件、再同步设计说明，不能反过来（避免两处漂移）。

---

## 4. v1 代码接口 schema

本约定钉死的代码接口约束:

- **目录**:把现 `cultural_prompts.py` 挪到 `src/prompts/v0/` 归档(`PROMPT_VERSION` 已改 `"v0.1"`,纠正错配);v1 四套评估条件(`zh` / `de_v1-draft` 待 Jens Linden 审校 / `en` uncalibrated baseline / `en_geo` country-label strong baseline,参数化,填充表见 `prompt_design_v1.md §4`)**内嵌为 `src/prompts/registry.py` 常量**(`_ZH_V1` / `_DE_V1_DRAFT` / `_EN_V1` / `_EN_GEO_V1`),不分文件存——四套短 prompt 同文件维护更直观;未来某版若 prompt 体量增大,可拆分到 `src/prompts/{version}/{lang}` 文件,约定保留兼容。
- **加载接口**:`src/prompts/registry.py` 提供 `load_prompt(version: str, lang: str) -> str`。`version` ∈ {`v0.1`,`v1`,…},`lang` ∈ {`zh`,`de`,`en`}。非法组合显式报错,不静默回退。
- **元数据字段**:每次生成的输出 JSON 必须带 `prompt_version` 字段(`methodology_notes.md §4` 已留 schema 位,本周真正用起来)。`empathy_cli.py` 加 `--prompt-version` 参数,默认 `v0.1`(向后兼容),传 `v1` 切新版。
- **不可变性**:一旦某版号被任何一次正式评估跑过,该版 prompt 文本即**冻结**;后续修改必须升新版号,不许原地改已评估过的版本(否则分数失去可复现锚点)。

---

## 5. 本周边界(版本约定层面)

v1 锁定 = "首个可被七维裁判正式打分的版本"。本周**只**产出 v1 的文本 + 设计说明 + 10 条 sanity-check;**不**做 v2 的迭代(那要等 Week 8 评估数据)、**不**挂 RAG(v2+rag 是 Week 10)。sanity-check 只验"prompt 没崩 / 格式对 / 语言一致",不是评估打分。

---

*版本约定 v1。拍板后同步技术窗口即可开工目录重构。下次修订:Week 9 出 v2 时追加一行 v2 定义 + 迭代依据。*
