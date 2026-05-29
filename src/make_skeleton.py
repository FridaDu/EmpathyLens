"""EmpathyLens — 按 20 情境表生成 60 条骨架 (Week 5). Run: python -m src.make_skeleton"""
import json
from src.dataset import empty_record, LANGS, DATA_PATH

# (scenario_id, scenario_type, kind, stressed_axes, anchor) —— 不含 sensitivity
SCENARIOS = [
  ("S01","breakup_clingy","mild_venting",["B","C"],"§3.1.5"),
  ("S02","marriage_pressure","mild_venting",["A","B"],"§3.1.1"),
  ("S03","career_vs_family","mild_venting",["A"],"§4.1"),
  ("S04","family_disappointment","mild_venting",["B"],"§3.1.4"),
  ("S05","grief_loss","mild_venting",["C"],"§2.4"),
  ("S06","want_presence_not_advice","mild_venting",["A"],"§3.1.1"),
  ("S07","loneliness_abroad","mild_venting",["A","D"],"§3.1.3"),
  ("S08","work_stress_insomnia","mild_venting",["A","C"],"§3.2.4"),
  ("S09","failure_self_doubt","mild_venting",["B"],"§4.1"),
  ("S10","workplace_exclusion","mild_venting",["A","D"],"§5.5 M4"),
  ("S11","decision_paralysis","mild_venting",["A"],"§3.2.1"),
  ("S12","persistent_low_mood","mild_venting",["D"],"§2.3.3"),
  ("S13","partner_conflict","mild_venting",["A","B"],"§5.5 M4"),
  ("S14","self_loathing","mild_venting",["B","C"],"§2.1"),
  ("S15","relocation_stress","mild_venting",[],"§2.4 control"),
  ("S16","health_anxiety","mild_venting",[],"§2.4 control"),
  ("S17","support_rejection_indirect","adversarial_indirect",["D"],"§4.2 / §5.5 M7"),
  ("S18","robot_accusation","adversarial_direct",["D"],"§4.2 / §5.5 M7"),
  ("S19","ai_legitimacy_challenge","adversarial_direct",[],"§5.5 M7"),
  ("S20","help_refusal_crisis","adversarial_indirect",["C"],"§6.4 crisis"),
]

def main():
    if DATA_PATH.exists():
        print(f"✋ {DATA_PATH} 已存在,不覆盖。要重生成先删掉它。"); return
    records = [empty_record(sid, lang, stype, kind, axes, anchor)
              for sid, stype, kind, axes, anchor in SCENARIOS for lang in LANGS]
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 写入 {len(records)} 条骨架 ({len(SCENARIOS)} 场景 × {len(LANGS)} 语言)")

if __name__ == "__main__":
    main()