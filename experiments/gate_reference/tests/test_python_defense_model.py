import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gate_reference.defense_python_matrix.model import load_conditions


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "gate_reference" / "defense_python_matrix" / "configs" / "defense_matrix.json"


REQUIRED_IDS = {
    "D0", "D1", "D1b", "D2", "D3a", "D3b", "D4", "D5a", "D5b",
    "D5c", "D5d", "D6_valid", "D6_invalid", "D7", "D8_xorhash",
}


def test_matrix_contains_all_conditions_without_truth_material():
    conditions = load_conditions(CONFIG)
    assert {item.condition_id for item in conditions} == REQUIRED_IDS
    raw = CONFIG.read_text()
    assert "MC_9" not in raw
    assert "MC9" not in raw
    assert "true_key_hex" not in raw
    assert "scan_slot" not in raw
    assert all(item.secret_id != "hidden_key" for item in conditions)


def test_condition_loader_rejects_duplicate_or_unknown_transform(tmp_path):
    payload = json.loads(CONFIG.read_text())
    payload["conditions"].append(dict(payload["conditions"][0]))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="duplicate condition_id"):
        load_conditions(duplicate)

    payload = json.loads(CONFIG.read_text())
    payload["conditions"][0]["transform"] = "not-a-transform"
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="unknown transform"):
        load_conditions(unknown)
