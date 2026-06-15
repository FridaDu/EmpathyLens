# Cultural Mode Prompts · CHANGELOG

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