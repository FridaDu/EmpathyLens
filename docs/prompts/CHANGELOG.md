# Cultural Mode Prompts · CHANGELOG

## v1.0.3 — 2026-06 (Week 8) — en native review by Declan Wells
- en_v1: 美式英语母语者 Declan Wells 审校通过,调整 6 处措辞(保持 §3.3.2 未校准基线身份)
  - Role: "the way mainstream English-language emotional support tends to" → "...apps typically do"
  - Behavior: "unconditional positive regard" → "warmth and acceptance";"Move relatively quickly" → "Move fairly quickly";"gentle positive reframing where possible" → "where appropriate, help the person see things in a more positive or constructive light"
  - Output: "A warm, supportive tone; clear and encouraging" → "Use a warm, supportive, clear, and encouraging tone"
  - Exception: "point them to" → "direct them to";"Make clear you are an AI" → "Make it clear that you are an AI"
- 同款改动已同步至 en_geo(保持 en_geo = en + 单一国家标签 的实验不变量)
- 审校备注(留给论文 Discussion):母语者指出 "unconditional positive regard" / "positive reframing" 偏临床,casual app 较少这样说

## v1.0.2 — 2026-06 (Week 8) — de native review by Jens Linden
- de_v1-draft → de_v1:Jens Linden 德语母语审校通过,调整 7 处语言形式(规范结构不变)
  - 常量重命名 `_DE_V1_DRAFT` → `_DE_V1`;`_V1_PROMPTS["de"]` 指向 `_DE_V1`
  - 句首 "auf natürlichem Deutsch" → "in einem natürlichen Deutsch"(母语者建议,语义不变)
  - Rolle "klarer zu sehen" → "sich klarer zu werden";Autonomie "selbst klarer zu sehen" → "sich selbst klarer zu werden"
  - "Silver Lining" → "Lichtblick"(erzwungenes → erzwungener);删去 "amazing";"zielloses, vages Herumschweben" → "Ziellosigkeit";"nummerierten Listen oder Aufzählungspunkte" → "Listen oder Stichpunkte"

## v1.0.1 — 2026-06 (Week 8) — zh native self-audit
- zh_v1:Frida Du、Helena Cai 母语自审通过,调整 4 处用词地道度(规范结构不变)
  - "让情绪先被接住" → "让情绪先被接纳",并加"肯定对方的感受"
  - 含蓄与留白:补具体举例("你现在感觉怎么样？慢慢说,我在听")
  - 长期视角:"silver lining" 改写为"不要立刻给出'天无绝人之路'这种强行乐观的说辞"
  - 边界:"还没被接住时" → "还没感受到有人陪伴、有人能共情他的感受时"

## v1 — 2026-06 (Week 7)
首个正式评估版,四套评估条件:
- zh: calibrated per framework §3.1 + §3.0 axes A/B/C/D + §5.4 intention cluster Support/Cathart/Preserve-Face + §5.5 反向规约 M1/M4/M5/M6/M8
- de_v1-draft: calibrated per framework §3.2; 待 Jens Linden 母语审校通过后升 de_v1
- en: 有意保持 §3.3.2 未校准基线 (uncalibrated baseline),仅做格式整理与 zh/de 平齐
- en_geo: framework §6.2 strong baseline (英文 prompt + 国家标签),回应 CuLEmo Finding 3

设计说明: docs/prompts/prompt_design_v1.md
版本约定: docs/prompts/prompt_versioning_convention.md
依据: framework_CN_v2 + evaluation_dimensions_v1.1

## v0.1 — 2026-05 (Week 4) [Archived Pilot]
非正式 pilot,未经七维评估。归档至 src/prompts/v0/cultural_prompts.py。
