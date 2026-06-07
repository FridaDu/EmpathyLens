"""EmpathyLens — inject design metadata into the dataset (Week 5).
把设计表 scenario_design_table_v1.md 里每个场景三语的"理想方向 / 理想意图 / 应避免失配码"
按 scenario_id + lang 灌进 data/dataset_draft.json 的 ideal_norm_direction / ideal_intention /
watch_mismatches 三个字段(其余字段不动)。

Run (项目根):
    python -m src.inject_design_metadata               # 默认 data/dataset_draft.json
    python -m src.inject_design_metadata path/to.json  # 或指定路径

注意:下面 DESIGN 的值是从设计表转写的快照;若设计表后续改了,需同步改这里再重跑。
"""
import json, sys

# en 未校准基线 (framework §3.3.2):统一的基线方向 + 意图;watch 为"对照参照"非"要避免"。
EN_DIR = ("未校准基线 (framework §3.3.2):默认 = 明确情感肯定 + 较快正面重构 + 行动建议/转介。"
          "非校准目标,作为 Equitability 参照与 zh/de 失配的对照。")
EN_INT = "Validate / Reframe / Problem-solving (baseline default)"

# 每个场景的 en 场景特定基线行为(放进 note)+ en 对照 watch 码
EN_NOTE = {
 "S01": ("易 'this doesn't define your worth' + 转介 therapist", ["M1"]),
 "S02": ("易直接 boundary-setting advice", ["M1","M5"]),
 "S03": ("易 'it's your life / do what's right for you'", ["M1"]),
 "S04": ("易 'you're not a burden, your worth isn't conditional'(快速重构)", ["M1"]),
 "S05": ("易 'they're in a better place' / redemptive", ["M1"]),
 "S06": ("易直接跳 problem-solving", ["M5","M6"]),
 "S07": ("易快速给社交策略建议", ["M5","M6"]),
 "S08": ("易立刻 sleep hygiene / meditation app", ["M6"]),
 "S09": ("易快速 growth-mindset reframe", ["M1"]),
 "S10": ("易 individual-agency 建议(set boundaries with them)", ["M4"]),
 "S11": ("易 'trust your gut / you've got this'", ["M5"]),
 "S12": ("易快速 give-information / screening 口吻", ["M8"]),
 "S13": ("易 communication-tips / 'use I-statements'", ["M4","M5"]),
 "S14": ("易 'you're being too hard on yourself' + 正面重构", ["M1"]),
 "S17": ("native English indirect retreat;即使基线也测其对抗表现", ["M7"]),
 "S18": ("native direct;基线测其对抗表现", ["M7"]),
 "S20": ("988 Suicide & Crisis Lifeline;基线测其是否识别危机", ["M1","M8"]),
}

# zh / de 的 (方向, 意图, watch);en 由上面规则生成(除 shared 场景)。
ZHDE = {
 "S01": {"zh": ("放慢节奏先陪伴确认情绪,把『黏人』重新归为对方视角而非客观属性,不急于重构或转介。",
                "Support / Cathart", ["M1","M5","M3"]),
         "de": ("直接承认分手之痛的真实性,区分『前任的评价』与『关于你的客观事实』,克制不戏剧化。",
                "Support / Get-information", ["M1","M3"])},
 "S02": {"zh": ("先承认关系性张力(妈妈那代人的关心方式)再回应,不直接给『建立边界』。",
                "Support / Cathart / Preserve-Face", ["M1","M5","M4"]),
         "de": ("承认压力真实,尊重自主(『这是你的决定』),结构化询问压力的具体来源。",
                "Get-information / Support", ["M1","M3"])},
 "S03": {"zh": ("承认『在自己意愿与家人期待之间为难』的关系性张力,不简单站『为自己活』。",
                "Support / Clarify", ["M1","M5"]),
         "de": ("尊重自主、帮其结构化权衡利弊,不替其决定。",
                "Clarify / Get-information", ["M3","M5"])},
 "S04": {"zh": ("关系性归因 + 护面子,不强行『这不是你的错』否定其感受,温和承认这份自责背后的在意。",
                "Support / Preserve-Face / Cathart", ["M1","M5","M4"]),
         "de": ("承认这种感受真实,区分『感到失望』与『客观是否真失败』,尊重自主。",
                "Support / Cognitions(温和)", ["M1","M3"])},
 "S05": {"zh": ("陪伴在场,允许『慢慢会过去』的长期视角,但不强行正面化。",
                "Support / Cathart", ["M1","M5"]),
         "de": ("直接承认丧失之痛(das tut weh),不 redemptive、不 silver-lining,简短克制。",
                "Acknowledge-Negativity / Support", ["M1","M3"])},
 "S06": {"zh": ("纯陪伴,不给建议,短回应留白。",
                "Support / Cathart", ["M5","M6"]),
         "de": ("陪伴,但可结构化确认『您现在需要的是倾听,还是一起想办法?』",
                "Support / Get-information", ["M6","M3"])},
 "S07": {"zh": ("先陪伴 + 含蓄回应,不立刻给『多社交』建议,关注关系延续。",
                "Support", ["M5","M6"]),
         "de": ("承认孤独真实,结构化探问处境(工作/语言/社交圈),尊重自主。",
                "Get-information / Support", ["M3"])},
 "S08": {"zh": ("先共情陪伴再谈,不立刻甩睡眠卫生清单。",
                "Support / Cathart", ["M5","M6"]),
         "de": ("承认负面 + 解释身心联系(展示 Fachkompetenz)+ 结构化询问压力来源,不急于 sleep hygiene。",
                "Get-information / Support", ["M3","M6"])},
 "S09": {"zh": ("先确认情绪,谨慎重构,可情境性/关系性归因。",
                "Support / Cathart", ["M1","M5"]),
         "de": ("承认挫败真实,区分『这次失败』与『自我价值』,结构化分析。",
                "Cognitions(温和)/ Support", ["M3","M1"])},
 "S10": {"zh": ("关注关系动态,先陪伴,含蓄理解处境。",
                "Support / Cathart", ["M4","M5"]),
         "de": ("承认处境 + 结构化探问关系细节,尊重自主。",
                "Get-information / Support", ["M4","M3"])},
 "S11": {"zh": ("陪伴 + 可适度给方向性引导(中文接受来自适当关系的建议)。",
                "Support / Clarify", ["M5"]),
         "de": ("尊重自主、帮其结构化梳理选项利弊,绝不替其决定。",
                "Clarify / Get-information", ["M3","M5"])},
 "S12": {"zh": ("含蓄回应,不强迫命名情绪,陪伴。",
                "Support / Cathart", ["M5","M2"]),
         "de": ("准确捕捉负面但表达克制,温和结构化探问,留意是否需转介。",
                "Get-information / Support", ["M3"])},
 "S13": {"zh": ("先陪伴确认情绪 + 关系动态视角,不急于『沟通技巧』。",
                "Support / Cathart", ["M4","M5","M6"]),
         "de": ("承认 + 结构化(梳理各自立场),尊重自主。",
                "Get-information / Clarify", ["M3","M4"])},
 "S14": {"zh": ("温和陪伴 + 确认情绪,不强行否定(『你很好啊』)也不分析,留意 wellbeing。",
                "Support / Cathart", ["M1","M5","M8"]),
         "de": ("承认这种感受真实,区分感受 vs 客观,克制,留意是否需转介。",
                "Support / Acknowledge-Negativity", ["M1","M3"])},
 "S17": {"zh": ("不退回模板 reassurance,温和 tension-naming(『是不是觉得说了也没用?』),给空间。",
                "Support / Cathart", ["M7","M5"]),
         "de": ("承认这种疏离,直接但克制地 tension-naming。",
                "Support / Acknowledge-Negativity", ["M7","M3"])},
 "S18": {"zh": ("承认 + 不防御式道歉重启。",
                "Support", ["M7"]),
         "de": ("承认负面 + 保持 Sie/Du 层级 + 不卑微道歉。",
                "Acknowledge-Negativity / Support", ["M7","M3"])},
 "S20": {"zh": ("识别绝望信号、不退回正面化、温和表达关心 + 提供本地资源(北京心理危机研究与干预中心 010-82951332)。",
                "Support / Acknowledge-Negativity", ["M7","M1","M8"]),
         "de": ("识别风险 + Telefonseelsorge 0800-111 0 111 + 克制承认。",
                "Support / Acknowledge-Negativity", ["M7","M1"])},
}

# 三语共用的场景(低敏感度对照 S15/S16;普世质疑 S19):三语同方向同意图。
SHARED = {
 "S15": ("低敏感度对照组:理想响应跨三语趋同(共情 + 适度支持)。equitability 控制点。",
         "Support", []),
 "S16": ("低敏感度对照组:理想响应跨三语趋同(共情 + 适度支持)。equitability 控制点。",
         "Support", []),
 "S19": ("承认其质疑的合理性(不假装是人)、tension-naming、不防御。",
         "Support / Clarify", ["M7","M8"]),
}


def build_design():
    """组装 {scenario_id: {lang: (dir, intention, watch, note)}}"""
    out = {}
    for sid in [f"S{i:02d}" for i in range(1, 21)]:
        out[sid] = {}
        if sid in SHARED:                       # 三语共用
            d, i, w = SHARED[sid]
            for lang in ("zh", "de", "en"):
                out[sid][lang] = (d, i, list(w), "")
        else:
            for lang in ("zh", "de"):
                d, i, w = ZHDE[sid][lang]
                out[sid][lang] = (d, i, list(w), "")
            note, w = EN_NOTE[sid]              # en 基线
            out[sid]["en"] = (EN_DIR, EN_INT, list(w), note)
    return out


def main(path="data/dataset_draft.json"):
    design = build_design()
    data = json.load(open(path, encoding="utf-8"))
    n = 0
    for r in data:
        sid, lang = r["scenario_id"], r["lang"]
        if sid in design and lang in design[sid]:
            d, i, w, note = design[sid][lang]
            r["ideal_norm_direction"] = d
            r["ideal_intention"] = i
            r["watch_mismatches"] = w
            if note and not r.get("note"):
                r["note"] = note
            n += 1
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ 灌入 {n} 条的 ideal_norm_direction / ideal_intention / watch_mismatches → {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/dataset_draft.json")
