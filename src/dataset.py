"""EmpathyLens — dataset schema / 受控词表 / loader (Week 5)"""
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent      # src/dataset.py -> 项目根
DATA_PATH = _ROOT / "data" / "dataset_draft.json"

LANGS = ["zh", "de", "en"]
KINDS = ["mild_venting", "adversarial_direct", "adversarial_indirect"]
SENSITIVITY = ["high", "medium", "low"]
AXES = ["A", "B", "C", "D"]
MISMATCH_CODES = [f"M{i}" for i in range(1, 9)]
INTENSITY_RANGE = (1, 5)

def empty_record(scenario_id, lang, scenario_type, kind, stressed_axes, anchor):
    return {
        "scenario_id": scenario_id,
        "id": f"{scenario_id}_{lang}",
        "lang": lang,
        "scenario_type": scenario_type,
        "kind": kind,
        "cultural_sensitivity": "",          # 留空,盲标后回填
        "stressed_axes": stressed_axes,
        "framework_anchor": anchor,
        "text": "",
        "emotional_intensity": None,         # 留空待标
        "cultural_cue": "",
        "ideal_norm_direction": "",
        "ideal_intention": "",
        "watch_mismatches": [],
        "author": "",
        "native_reviewed": False,
        "note": "",
    }

def load_dataset(path: Path = DATA_PATH) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)