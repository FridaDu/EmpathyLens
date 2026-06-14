"""EmpathyLens — judge-input assembler (Week 8 地基,Week 6 提前做).
把一条 (数据集记录 × 模型响应 × 维度) 拼成 LLM-as-a-Judge 的 system/user 提示。
纯函数,不调 API(API 调用在 Week 8 的 run_judge.py 里,复用 llm_client.call_model)。

本文件落地了 evaluation_dimensions_v1.1 §7 的接口约定，关键修补:
  ② 空 stressed_axes → D4 记 N/A(rubrics.dimension_applies)。
  ③ en 的'非校准基线'口径 → 翻译成 de-facto 评分目标(build_target_norm)。
  ④ S19_en 若保留校准文本则原样用,若改回 baseline 自动切换(无需改本文件)。
  §2.1 D5 的 ideal_intention 也走 en 翻译 + 策略token归一(build_target_intention),
       否则裁判会收到'Validate/Reframe/Problem-solving (baseline default)'这类没法评分的元话术。
  ⑦ D5 注入意图受控词表(INTENTION_TAXONOMY,14 canonical,已对照 §5.4 定稿)。
  ⑧ watch_mismatches 默认【不喂】裁判(防 priming),需要时显式 include_watch=True。
  宽松偏差:输出契约强制'先列指认到的标记,再给分'。
放置位置建议:src/eval/assemble_judge_input.py。冒烟:python -m src.eval.assemble_judge_input
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
    en baseline 条 → 固定意图簇 EN_BASELINE_INTENTION;其余 → 归一后的 token。
    与 build_target_norm 对称,修掉复核说明 §2.1 的 D5 元话术 bug。"""
    raw = record.get("ideal_intention", "") or ""
    if record.get("lang") == "en" and ("baseline" in raw.lower() or "未校准" in raw):
        return " / ".join(EN_BASELINE_INTENTION)
    toks = _norm_tokens(raw)
    return " / ".join(toks) if toks else raw


def build_context_block(record, include_watch=False) -> str:
    """文化上下文块。stressed_axes 为空时明确写'无文化应力轴'。
    对抗条加一句 intensity 语义注释(⑪)。watch_mismatches 默认不放(⑧)。"""
    axes = record.get("stressed_axes") or []
    axes_str = "、".join(axes) if axes else "无(本条无文化应力轴,D4 记 N/A)"
    lines = [
        f"目标语言/文化:{LANG_CULTURE.get(record.get('lang'), record.get('lang'))}",
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


SYSTEM_PROMPT = (
    "你是跨文化情感支持响应的严格评审。你只评【模型响应】在【单一维度】上的质量,"
    "严格按给定的目标文化规范与打分锚点。"
    "不要被流畅或热情迷惑(LLM 评审有宽松偏差):必须先在响应里指认具体文本标记,再据锚点给分。"
    "只输出 JSON,不要多余解释。"
)

OUTPUT_CONTRACT = (
    '只输出如下 JSON:{"markers": [在响应中指认到的具体片段/行为,字符串数组], '
    '"score": 1-5 的整数, "justification": "一句话:为什么是这个分(引用上面的 markers)"}'
)


def assemble(record, response_text, dim_key, include_watch=False) -> dict:
    """组装一次评分调用。
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
        f"【文化上下文】\n{build_context_block(record, include_watch)}\n\n"
        f"【待评模型响应】\n{response_text}\n\n"
        f"【评分维度与锚点】\n{_rubric_block(record, dim_key)}\n\n"
        f"【输出要求】\n{OUTPUT_CONTRACT}"
    )
    return {"applicable": True, "dim": dim_key, "id": record.get("id"),
            "scenario_id": record.get("scenario_id"), "lang": record.get("lang"),
            "system": SYSTEM_PROMPT, "user": user}


def assemble_all_dims(record, response_text, include_watch=False) -> list:
    """对一条响应,生成七维的全部评分单元(自动跳过 N/A 维度的打分,但保留 N/A 记录)。"""
    return [assemble(record, response_text, dk, include_watch) for dk in DIMENSION_ORDER]


if __name__ == "__main__":
    # 自测:加载真数据集,验证 ②③④ 的行为。
    from src.dataset import load_dataset
    data = {r["id"]: r for r in load_dataset()}
    fake = "我能感觉到你现在很难受。要不你先别急着辞职,列个利弊清单,为自己而活最重要。"

    print(f"=== assembler self-test (rubric {RUBRIC_VERSION}) ===\n")

    # ② 空轴 D4 → N/A(S15 控制条)
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

    # ④ S19_en 保留校准文本时原样用(若团队改回 baseline 会自动切换)
    print("S19_en target_norm:", build_target_norm(data["S19_en"])[:40], "...")

    # §2.1 D5 意图翻译:en 策略/元话术 → canonical 意图簇
    ti = build_target_intention(data["S02_en"])
    print("S02_en target_intention:", ti)
    assert "baseline" not in ti.lower() and "Validate" not in ti
    assert ti == "Feelings / Hope / Give-information / Change"
    # zh 的括注被剥掉(S04_de 'Cognitions(温和)/ Support' → 'Cognitions / Support')
    print("S04_de target_intention:", build_target_intention(data["S04_de"]))
    assert "(" not in build_target_intention(data["S04_de"])

    # D3 危机模式选择:S20 全语言危机 vs S08 一般档
    a20 = d3_anchors_for(data["S20_zh"]); a08 = d3_anchors_for(data["S08_zh"])
    print("S20_zh D3 档数:", len(a20), "| S08_zh D3 档数:", len(a08))
    assert len(a20) == 5 and len(a08) == 3
    assert len(d3_anchors_for(data["S20_en"])) == 5  # S20 三语都危机

    # 语言特异 D3(团队 A+B 决策):S14_zh 危机档,S14_en/de 一般档
    n14 = {lg: len(d3_anchors_for(data[f"S14_{lg}"])) for lg in ("zh", "de", "en")}
    print("S14 D3 档数 (zh/de/en):", n14)
    assert n14 == {"zh": 5, "de": 3, "en": 3}, "S14 语言特异 D3 触发不符"

    # 打印一个完整 user 提示示例
    demo = assemble(data["S02_zh"], fake, "D4")
    print("\n----- 示例 user 提示 (S02_zh × D4) -----\n")
    print(demo["user"])
    print("\n✅ assembler 自测全部通过")
