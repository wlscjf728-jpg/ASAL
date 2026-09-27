import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "gate_reference/defense_boundary/results/rtl_golden_matrix_summary.json"


def load():
    return json.loads(SUMMARY.read_text())


def test_all_primary_conditions_match_software_golden():
    doc = load()
    assert doc["summary"]["matched"] == 13
    assert doc["summary"]["incomplete"] == 0
    ids = [row["condition_id"] for row in doc["conditions"]]
    assert len(ids) == 13
    assert "D1b" not in ids
    assert "D3b" not in ids
    assert all(row["status"] == "MATCHED" for row in doc["conditions"])


def test_success_conditions_reuse_only_exact_rtl_transcripts():
    doc = load()
    expected = {"D0", "D1", "D3a", "D5a", "D5b", "D6_valid"}
    for row in doc["conditions"]:
        if row["condition_id"] in expected:
            assert row["rtl_verdict"] == "ATTACK_SUCCESS"
            assert row["solver_evidence"] == "software_proof_on_exact_RTL_transcript"
            assert row["comparisons"]["q128"]["status"] == "MATCHED"
            assert row["comparisons"]["q131"]["status"] == "MATCHED"


def test_boundary_stages_are_preserved():
    doc = load()
    rows = {row["condition_id"]: row for row in doc["conditions"]}
    assert rows["D2"]["first_blocked_stage"] == "phase0_discovery"
    assert rows["D4"]["first_blocked_stage"] == "phase0_query_authorization"
    assert rows["D5c"]["first_blocked_stage"] == "phase0_5_attribution"
    assert rows["D5d"]["first_blocked_stage"] == "phase0_5_attribution"
    assert rows["D6_invalid"]["first_blocked_stage"] == "access"
    assert rows["D7"]["first_blocked_stage"] == "adaptive_query_authorization"
    assert rows["D8_xorhash"]["first_blocked_stage"] == "phase0_5_attribution"
    assert rows["D7"]["comparisons"]["q128"]["status"] == "MATCHED"
    assert rows["D7"]["comparisons"]["q131"]["status"] == "POLICY_DENIED"


def test_representative_slots_and_phase0_boundaries():
    doc = load()
    rows = {row["condition_id"]: row for row in doc["conditions"]}
    assert rows["D0"]["phase0"]["selected_slot"] == 255
    assert rows["D1"]["phase0"]["selected_slot"] == 255
    assert rows["D5a"]["phase0"]["selected_slot"] == 46
    assert rows["D5b"]["phase0"]["selected_slot"] == 255
    assert rows["D2"]["phase0"]["status"] == "no_channel"
    assert rows["D4"]["phase0"]["status"] == "no_channel"
    assert rows["D8_xorhash"]["phase0"]["status"] == "pass"
