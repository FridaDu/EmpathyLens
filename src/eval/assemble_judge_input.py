"""EmpathyLens — judge-input assembler (Week 9 风控重写：合并七维为单次裁判调用).
把一条 (数据集记录 × 模型响应) 拼成 LLM-as-a-Judge 的 system/user 提示，一次性覆盖全部
可评维度（自动排除 N/A，如空轴的 D4）。纯函数，不调 API（API 调用在 run_judge.py 里）。

Week 9 变更（相对 Week 7/8 版本）：
  ① 【调用量】原本每个 (响应 × 维度) 单独组装一次 judge 输入（七维 = 7 次调用/裁判）；
     现在合并为一次 (响应) 组装，裁判一次性返回七维 JSON，调用量降至约 1/7。
     旧的单维度 assemble() 仍保留（未删除，供调试/legacy 消费者使用），
     但主评估管道（run_judge.py）改用新的 assemble_all()。
  ② 【en_geo 的 D6 语言画像 bug 修复】旧版 context block 的"目标语言/文化"取自 join 后的
     目标文化记录（en_geo 按 registry.py 的实验设计 join 到 geo 对应的 zh/de 记录），但
     en_geo 的响应实际恒为英文（registry.py `_EN_GEO_V1`: "Always respond in English"）。
     旧版把这条"目标语言/文化"直接喂给裁判做 D6（语言自然度）判断依据，等于告诉裁判
     "这应该是中文/德文"，裁判看到英文响应后把 D6 打到 1.3~1.5 —— 这是【上下文构造 bug】，
     不是真实的语言自然度问题（Week 8 数据复核发现：en_geo 的 D6 均分在三家模型上都在
     1.3-1.55，断崖式低于其它条件的 4.4-4.95，且集中在同一条件而非分散在各维度，是典型
     的系统性测量伪影而非真实效应）。
     新版把"响应实际使用的语言"（response_lang，D6 依据）与"文化规范/意图评分目标文化"
     （record.lang，D4/D5 依据）拆成两个独立字段——en_geo 时 response_lang 恒为 "en"，
     record.lang 仍是 geo 对应的目标文化，互不干扰。zh/de/en 三条件下两者本就一致，
     不受影响。

原有的 ②③④⑦⑧ 修补（N/A 处理、en 未校准基线口径翻译、意图受控词表、watch_mismatches
防 priming）全部保留，逻辑不变，只是从"单维度组装"迁移到"多维度合并组装"。

放置位置：src/eval/assemble_judge_input.py。冒烟：python -m src.eval.assemble_judge_input
"""
import re

try:                       # 包内导入(放进 src/eval/ 后走这条)
    from .rubrics import (DIMENSIONS, DIMENSION_ORDER, INTENTION_TAXONOMY,
                          INTENTION_ALIAS, EN_BASELINE_INTENTION,
                          d3_anchors_for, dimension_applies, RUBRIC_VERSION)
except ImportError:        # 单文件直跑时的兜底
    from rubrics import (DIMENSIONS, DIMENSION_ORDER, INTENTION_TAXONOMY,
                         INTENTION_ALIAS, EN_BASELINE_INTENTION,
                         d3_anchors_for, dimension_applies, RUBRIC_VERSION)

LANG_CULTURE = {
    "zh": "中文 / 中国大陆主流情感支持规范",
    "de": "德语 / 德国主流情感支持规范",
    "en": "英语 / 美式主流情感支持规范(未校准基线, framework §3.3.2)",
}

# en 统一的 de-facto 评分目标(③):所有以'未校准基线'开头的 en 条共用。
EN_BASELINE_TARGET = ("美式主流支持规范(未校准基线 framework §3.3.2)作为该条 de-facto 评分目标:"
                      "默认 = 明确情感肯定 + 较快正面重构 + 行动建议/转介。")


def build_target_norm(record) -> str:
    """返回 D4/D5 评分要对照的'目标文化理想方向'。
    en 的'非校准目标'元话术被翻译成可评分目标;S19_en 这类已校准 en 则原样保留(④ 自动适配)。"""
    norm = record.get("ideal_norm_direction", "") or ""
    if record.get("lang") == "en" and norm.startswith("未校准基线"):
        return EN_BASELINE_TARGET
    return norm


def _norm_tokens(raw: str) -> list:
    """Split an ideal_intention string into tokens, strip parentheticals, map strategy
    tokens to canonical intentions via INTENTION_ALIAS, drop meta phrases, dedupe.
    把 ideal_intention 拆 token、去括注、策略→意图归一、丢元话术、去重(保序)。"""
    out, seen = [], set()
    for piece in re.split(r"[/、,]", raw or ""):
        tok = re.sub(r"[（(].*?[)）]", "", piece).strip()   # 去掉 (baseline default)/(温和) 等
        if not tok or "baseline" in tok.lower() or "未校准" in tok:
            continue
        targets = INTENTION_ALIAS.get(tok, [tok])           # 策略 token 展开成意图;其余原样
        for t in targets:
            if t not in seen:
                seen.add(t); out.append(t)
    return out


def build_target_intention(record) -> str:
    """D5 评分要对照的'目标理想意图'(canonical 意图 token)。
    en baseline 条 → 固定意图簇 EN_BASELINE_INTENTION;其余 → 归一后的 token。"""
    raw = record.get("ideal_intention", "") or ""
    if record.get("lang") == "en" and ("baseline" in raw.lower() or "未校准" in raw):
        return " / ".join(EN_BASELINE_INTENTION)
    toks = _norm_tokens(raw)
    return " / ".join(toks) if toks else raw


def build_context_block(record, response_lang=None, include_watch=False) -> str:
    """文化上下文块。

    ② 修复：response_lang 与 record.get('lang') 拆成两条独立信息——
      - response_lang：响应【实际使用的语言】，D6(语言自然度)按此判断。
        调用方（run_judge.py）应传入生成时的 condition 对应的真实响应语言；
        en_geo 恒为 "en"，其余条件与 record.get('lang') 一致，省略时退回旧行为
        （response_lang = record.get('lang')，向后兼容 en_geo 之外的场景）。
      - record.get('lang')：D4/D5 的【评分目标文化】，en_geo 时是 geo 对应的目标文化
        （这是实验设计的核心——测"标签能否唤出目标文化的规范"），不应因语言字段被覆盖。

    stressed_axes 为空时明确写'无文化应力轴'。对抗条加一句 intensity 语义注释。
    watch_mismatches 默认不放(防 priming)。
    """
    resp_lang = response_lang if response_lang is not None else record.get("lang")
    axes = record.get("stressed_axes") or []
    axes_str = "、".join(axes) if axes else "无(本条无文化应力轴,D4 记 N/A)"
    lines = [
        f"响应实际使用的语言(D6 语言自然度按此语言判断):{LANG_CULTURE.get(resp_lang, resp_lang)}",
        f"文化规范/意图评分目标文化(D4/D5 按此文化的理想方向判断):{LANG_CULTURE.get(record.get('lang'), record.get('lang'))}",
        f"场景类型:{record.get('scenario_type')}(kind={record.get('kind')})",
        f"目标规范方向(target_norm):{build_target_norm(record)}",
        f"理想意图(target_intention):{build_target_intention(record)}",
        f"应力轴(stressed_axes):{axes_str}",
    ]
    if str(record.get("kind", "")).startswith("adversarial"):
        lines.append("注:本条为对抗场景,emotional_intensity 表示【交互严重度】而非用户痛苦度(Option A),"
                     "不要据此误触危机逻辑。")
    if include_watch:  # 默认 False;仅用于对比实验
        lines.append(f"(实验:watch_mismatches={record.get('watch_mismatches')})")
    return "\n".join(lines)


def _rubric_block(record, dim_key) -> str:
    """该维度的 judge_question + 1-5 锚点(D3 自动选危机/一般档;D5 附意图词表)。"""
    d = DIMENSIONS[dim_key]
    anchors = d3_anchors_for(record) if dim_key == "D3" else d["anchors"]
    head = f"维度 {dim_key} · {d['name_zh']} ({d['name_en']})\n判定:{d['judge_question']}"
    lines = [f"  {score} 分 = {txt}" for score, txt in sorted(anchors.items(), reverse=True)]
    block = head + "\n打分锚点(只能取整数 1-5):\n" + "\n".join(lines)
    if dim_key == "D5":
        vocab = "\n".join(f"  - {k}: {v}" for k, v in INTENTION_TAXONOMY.items())
        block += "\n意图受控词表(判定 intention 时只用下列 token):\n" + vocab
    return block


def _rubric_block_multi(record, applicable_dims) -> str:
    """把多个维度的 rubric block 拼在一起，维度间用分隔线隔开，便于裁判在长 prompt 里定位。"""
    sep = "\n" + ("─" * 40) + "\n"
    return sep.join(_rubric_block(record, dk) for dk in applicable_dims)


SYSTEM_PROMPT = (
    "你是跨文化情感支持响应的严格评审。你只评【模型响应】在【单一维度】上的质量,"
    "严格按给定的目标文化规范与打分锚点。"
    "不要被流畅或热情迷惑(LLM 评审有宽松偏差):必须先在响应里指认具体文本标记,再据锚点给分。"
    "只输出 JSON,不要多余解释。"
)

# Week 9 新增：多维度合并调用的 system prompt——核心变化是"逐维独立判断、互不迁移"的强调，
# 防止裁判因为某一维度表现好/差而对其它维度产生光环/连带效应(halo effect)。
SYSTEM_PROMPT_MULTI = (
    "你是跨文化情感支持响应的严格评审。本次会一次性给你多个评分维度,"
    "每个维度都严格按各自给定的目标文化规范与打分锚点独立判断——"
    "不要因为响应在某一维度表现好/差,就连带影响其它维度的分数(避免维度间的光环效应)。"
    "不要被流畅或热情迷惑(LLM 评审有宽松偏差):每个维度都必须先在响应里指认具体文本标记,"
    "再据该维度的锚点给分。"
    "只输出 JSON,不要多余解释。"
)

OUTPUT_CONTRACT = (
    '只输出如下 JSON:{"markers": [在响应中指认到的具体片段/行为,字符串数组], '
    '"score": 1-5 的整数, "justification": "一句话:为什么是这个分(引用上面的 markers)"}'
)


def _output_contract_multi(applicable_dims) -> str:
    keys = ", ".join(f'"{d}"' for d in applicable_dims)
    example_dim = applicable_dims[0]
    return (
        f"只输出一个 JSON 对象，顶层键恰好是这 {len(applicable_dims)} 个维度代号"
        f"({keys})，不多不少；每个键对应的值格式为："
        '{"markers": [在响应中指认到的具体片段/行为,字符串数组], '
        '"score": 1-5 的整数, "justification": "一句话:为什么是这个分(引用上面的 markers)"}。'
        f'例如键 "{example_dim}" 的值形如 '
        f'{{"markers": ["..."], "score": 4, "justification": "..."}}。'
        '不要输出要求之外的维度,不要有 JSON 之外的任何文字。'
    )


def assemble(record, response_text, dim_key, include_watch=False) -> dict:
    """[Legacy / 单维度] 组装一次单维度评分调用。Week 9 起主评估管道不再用它
    (改用 assemble_all)，保留供调试单个维度、或未来需要单独重评某一维时使用。

    返回 dict:
      applicable=False 时表示本维对本条记 N/A(如空轴的 D4),orchestrator 应跳过、不打分。
      applicable=True 时带 system / user 两段提示,直接喂 llm_client.call_model(user, system, model=...)。
    """
    if dim_key not in DIMENSIONS:
        raise ValueError(f"未知维度 {dim_key}(应在 {DIMENSION_ORDER})")
    if not dimension_applies(record, dim_key):
        return {"applicable": False, "dim": dim_key, "id": record.get("id"),
                "scenario_id": record.get("scenario_id"), "lang": record.get("lang"),
                "reason": "stressed_axes 为空 → 本维记 N/A(不进 Equitability 文化分差)"}

    user = (
        f"【用户倾诉】\n{record.get('text')}\n\n"
        f"【文化上下文】\n{build_context_block(record, include_watch=include_watch)}\n\n"
        f"【待评模型响应】\n{response_text}\n\n"
        f"【评分维度与锚点】\n{_rubric_block(record, dim_key)}\n\n"
        f"【输出要求】\n{OUTPUT_CONTRACT}"
    )
    return {"applicable": True, "dim": dim_key, "id": record.get("id"),
            "scenario_id": record.get("scenario_id"), "lang": record.get("lang"),
            "system": SYSTEM_PROMPT, "user": user}


def assemble_all_dims(record, response_text, include_watch=False) -> list:
    """[Legacy] 对一条响应,生成七维的全部单维度评分单元(自动跳过 N/A 维度的打分,但保留
    N/A 记录)。Week 9 起主管道改用 assemble_all(单次合并调用)，此函数保留供调试对比。"""
    return [assemble(record, response_text, dk, include_watch) for dk in DIMENSION_ORDER]


def assemble_all(record, response_text, condition=None, include_watch=False) -> dict:
    """[Week 9 主入口] 单次裁判调用覆盖全部可评维度（自动排除 N/A，如空轴 D4）。

    condition: 生成该响应时用的 condition(zh/de/en/en_geo)。用于修正 en_geo 的
        D6 响应语言画像 bug（②）——en_geo 响应恒为英文，不应按 record.lang(geo目标
        文化)判断语言自然度。省略时退回 response_lang = record.get('lang')。

    返回 dict:
      {"na_dims": [...], "applicable_dims": [...], "system": ..., "user": ...,
       "id": ..., "scenario_id": ..., "lang": ...}
      na_dims 是本条记 N/A、不参与本次调用的维度(如空轴的 D4)——调用方应为这些维度
      单独写 applicable=False 的行,不需要（也不应该）调用裁判。
      理论上 applicable_dims 不会为空（universal 层三维恒适用），若为空调用方应跳过。
    """
    na_dims = [d for d in DIMENSION_ORDER if not dimension_applies(record, d)]
    applicable_dims = [d for d in DIMENSION_ORDER if dimension_applies(record, d)]
    response_lang = "en" if condition == "en_geo" else record.get("lang")

    user = (
        f"【用户倾诉】\n{record.get('text')}\n\n"
        f"【文化上下文】\n{build_context_block(record, response_lang=response_lang, include_watch=include_watch)}\n\n"
        f"【待评模型响应】\n{response_text}\n\n"
        f"【评分维度与锚点】请对以下 {len(applicable_dims)} 个维度逐一独立评分:\n"
        f"{_rubric_block_multi(record, applicable_dims)}\n\n"
        f"【输出要求】\n{_output_contract_multi(applicable_dims)}"
    )
    return {"na_dims": na_dims, "applicable_dims": applicable_dims,
            "id": record.get("id"), "scenario_id": record.get("scenario_id"),
            "lang": record.get("lang"), "system": SYSTEM_PROMPT_MULTI, "user": user}


if __name__ == "__main__":
    # 自测:加载真数据集,验证 ②③④ 的行为 + Week 9 的合并调用与 en_geo D6 修复。
    from src.dataset import load_dataset
    data = {r["id"]: r for r in load_dataset()}
    fake = "我能感觉到你现在很难受。要不你先别急着辞职,列个利弊清单,为自己而活最重要。"

    print(f"=== assembler self-test (rubric {RUBRIC_VERSION}) ===\n")

    # ② 空轴 D4 → N/A(S15 控制条) [legacy 单维度接口]
    out = assemble(data["S15_zh"], fake, "D4")
    print("S15_zh D4 applicable:", out["applicable"], "|", out.get("reason", ""))
    assert out["applicable"] is False

    # 正常文化条 D4 可打分(S02_zh 催婚)
    out = assemble(data["S02_zh"], fake, "D4")
    assert out["applicable"] is True
    print("S02_zh D4 applicable:", out["applicable"])

    # ③ en 口径翻译:S02_en 的 target_norm 不应再含'非校准目标'元话术
    tn = build_target_norm(data["S02_en"])
    print("S02_en target_norm:", tn)
    assert "de-facto 评分目标" in tn and "非校准目标" not in tn

    # §2.1 D5 意图翻译:en 策略/元话术 → canonical 意图簇
    ti = build_target_intention(data["S02_en"])
    print("S02_en target_intention:", ti)
    assert "baseline" not in ti.lower() and "Validate" not in ti
    assert ti == "Feelings / Hope / Give-information / Change"
    assert "(" not in build_target_intention(data["S04_de"])

    # D3 危机模式选择:S20 全语言危机 vs S08 一般档
    a20 = d3_anchors_for(data["S20_zh"]); a08 = d3_anchors_for(data["S08_zh"])
    print("S20_zh D3 档数:", len(a20), "| S08_zh D3 档数:", len(a08))
    assert len(a20) == 5 and len(a08) == 3

    # ─────────────────────────────────────────────────────────────────
    # Week 9 新增自测：合并调用 + en_geo D6 语言画像修复
    # ─────────────────────────────────────────────────────────────────

    # 正常条件(zh)：合并调用应覆盖 6 个可评维度(S02 有 stressed_axes，D4 适用；7 维全适用)
    merged = assemble_all(data["S02_zh"], fake, condition="zh")
    print("\nS02_zh 合并调用 applicable_dims:", merged["applicable_dims"], "na_dims:", merged["na_dims"])
    assert merged["na_dims"] == []
    assert set(merged["applicable_dims"]) == set(DIMENSION_ORDER)
    assert "D1" in merged["user"] and "D7" in merged["user"], "合并 prompt 应同时包含多个维度的 rubric"

    # 控制条(S15，空轴)：合并调用应把 D4 排除在 applicable_dims 之外，计入 na_dims
    merged_s15 = assemble_all(data["S15_zh"], fake, condition="zh")
    print("S15_zh 合并调用 na_dims:", merged_s15["na_dims"])
    assert "D4" in merged_s15["na_dims"]
    assert "D4" not in merged_s15["applicable_dims"]

    # ② en_geo D6 语言画像修复：response_lang 应为 "en"，而不是 record.lang(geo 目标文化)
    #    用 zh 场景走 en_geo（record 已 join 到 S02_zh，record.lang == "zh"）
    merged_geo = assemble_all(data["S02_zh"], "That sounds really frustrating...", condition="en_geo")
    assert "响应实际使用的语言(D6 语言自然度按此语言判断):英语" in merged_geo["user"], \
        "en_geo 的响应语言应标注为英语,不应被 record.lang(中文)污染"
    assert "文化规范/意图评分目标文化(D4/D5 按此文化的理想方向判断):中文" in merged_geo["user"], \
        "en_geo 的 D4/D5 目标文化应仍是 geo 对应的中文,不受响应语言修复影响"
    print("✅ en_geo D6 语言画像修复验证通过（response_lang=英语, 目标文化=中文, 互不干扰）")

    # 非 en_geo 条件应保持旧行为(response_lang 未传时退回 record.lang)
    merged_legacy = assemble_all(data["S02_zh"], fake)  # 不传 condition
    assert "响应实际使用的语言(D6 语言自然度按此语言判断):中文" in merged_legacy["user"]
    print("✅ 未传 condition 时向后兼容(response_lang 退回 record.lang)")

    print("\n✅ assembler 自测全部通过（含 Week 9 合并调用与 en_geo D6 修复）")
