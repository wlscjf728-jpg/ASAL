import json
import sys
from pathlib import Path


EXTRA_EXP = Path(__file__).resolve().parents[1]
ROOT = EXTRA_EXP.parent
sys.path.insert(0, str(EXTRA_EXP / "scripts"))
from build_frozen_inputs import _load_common  # noqa: E402


def test_query_manifest_is_exact():
    manifest = json.loads((EXTRA_EXP / "inputs" / "mc9_seed2_q128.json").read_text())
    common = _load_common()
    expected = [point.hex() for point in common.nested_plaintexts(128, 2)]
    assert len(manifest["queries"]) == 129
    assert [row["plaintext_hex"] for row in manifest["queries"]] == expected


def test_phase0_manifest_is_exactly_65_queries():
    manifest = json.loads((EXTRA_EXP / "inputs" / "phase0_queries.json").read_text())
    assert len(manifest["queries"]) == 65


def test_attacker_manifest_has_no_truth():
    text = (EXTRA_EXP / "inputs" / "mc9_seed2_q128.json").read_text()
    assert "a66f651322597191ab9f8f8af4c2db61" not in text
    assert "MC_REG[9]" not in text
    assert "scan_path" not in text


def test_frozen_case_and_separator():
    case = json.loads((EXTRA_EXP / "inputs" / "frozen_case.json").read_text())
    control = json.loads((EXTRA_EXP / "inputs" / "known_separator_control.json").read_text())
    assert case["case_id"] == "late1_MC_9__seed2"
    assert case["tap"] == {"stage": "MC", "bit_index": 9}
    assert case["depth"] == 2
    assert case["mode"] == "differential"
    assert control["plaintext_hex"] == "f4000000004800d86000586000cb0010"
