import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "extra_exp/defense_boundary/results/rtl_vs_software_summary.json"


def test_rtl_report_contains_only_primary_rtl_conditions():
    doc = json.loads(SUMMARY.read_text())
    ids = [row["condition_id"] for row in doc["conditions"]]
    assert ids == ["D0", "D1", "D2", "D3a"]
    assert "D1b" not in ids
    assert "D3b" not in ids


def test_state_only_rtl_result_matches_software_golden():
    doc = json.loads(SUMMARY.read_text())
    row = next(row for row in doc["conditions"] if row["condition_id"] == "D1")
    assert row["technique"] == "State-centric protection (post-MC exposed)"
    assert row["software_verdict"] == "ATTACK_SUCCESS"
    assert row["rtl_verdict"] == "ATTACK_SUCCESS"
    assert row["q128_transcript"]["status"] == "MATCHED"
    assert row["q131_transcript"]["status"] == "MATCHED"
    assert row["comparison_status"] == "MATCHED"


def test_rtl_success_is_not_claimed_without_final_golden_proof():
    doc = json.loads(SUMMARY.read_text())
    for row in doc["conditions"]:
        if row["software_verdict"] == "ATTACK_SUCCESS":
            assert row["golden_final"] == "full_key_unique"
            assert row["solver_evidence"] == "software_proof_on_exact_RTL_transcript"


def test_mode_reset_matches_software_block_boundary():
    doc = json.loads(SUMMARY.read_text())
    row = next(row for row in doc["conditions"] if row["condition_id"] == "D2")
    assert row["software_verdict"] == "NO_ATTRIBUTABLE_CHANNEL"
    assert row["rtl_verdict"] == "NO_ATTRIBUTABLE_CHANNEL"
    assert row["first_blocked_stage"] == "phase0_discovery"
    assert row["comparison_status"] == "MATCHED"
