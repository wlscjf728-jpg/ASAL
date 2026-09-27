import json
from pathlib import Path

from scripts.phase_alpha_tracking import (
    fingerprint,
    make_permutation,
    parse_capture,
    run_experiment,
    transformed_rows,
)


ROOT = Path(__file__).resolve().parents[1]


def test_existing_capture_has_expected_shape():
    rows = parse_capture(ROOT / "inputs/phase0_gate_scan_attack.txt")
    assert len(rows) == 65 * 3
    assert len({q for q, _ in rows}) == 65
    assert len({schedule for _, schedule in rows}) == 3


def test_identity_preserves_selected_slot_fingerprint():
    rows = parse_capture(ROOT / "inputs/phase0_gate_scan_attack.txt")
    baseline = {q: rows[(q, 1)] for q in range(65)}
    expected = fingerprint(baseline, 255, range(16))
    identity = transformed_rows(rows, 1, make_permutation(None))
    assert fingerprint(identity, 255, range(16)) == expected


def test_alpha_has_stable_pass_and_independent_negative_control():
    result = run_experiment(ROOT / "configs/phase_alpha.json")
    assert result["summary"]["alpha_verdict"] == "PASS"
    assert result["summary"]["stable_all_correct"] is True
    negative = result["scenarios"]["negative_independent_probe_permutation"]
    assert negative["expected_verdict"] == "FAIL_EXPECTED"
    assert negative["all_trials_non_unique"] is True


def test_initial_collision_refinement_is_visible():
    result = run_experiment(ROOT / "configs/phase_alpha.json")
    epochs = result["scenarios"]["stable_refresh_65"]["epochs"]
    assert epochs[0]["initial_match_count"] > 1
    assert epochs[0]["final_match_count"] == 1
    assert epochs[0]["additional_probe_count"] > 0
