import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE_B = ROOT / "gate_reference" / "results" / "phase_b"


def test_phase0_selected_slot_is_anonymous_and_mc_supported():
    result = json.loads((PHASE_B / "phase0_discovery.json").read_text())
    selected = result["final_selected_slot"]

    assert result["evaluator_target_column_consumed"] is False
    assert result["total_scan_ff"] == 256
    assert result["query_count"] == 65
    assert result["mc_aware_candidate_count_overlap_ge_3"] == 1
    assert selected["scan_out_index"] == 255
    assert selected["nearest_mc_column"] == "C0"
    assert selected["exact_four_byte_support"] is True
    assert selected["repeat_stable"] is True


def test_gate_transcript_matches_semantic_reference():
    for name, expected_count in (
        ("q128_gate_observations_evaluator_reference_check.json", 129),
        ("q129_gate_reference_check.json", 130),
        ("adaptive_separator_q130_gate_observation_reference_check.json", 2),
    ):
        check = json.loads((PHASE_B / name).read_text())
        assert check["query_count"] == expected_count
        assert check["bitwise_match"] is True
        assert check["mismatch_count"] == 0


def test_attack_transcript_withholds_evaluator_key():
    for name, expected_count in (
        ("q128_gate_observations_attack.json", 129),
        ("q129_gate_observations_attack.json", 130),
        ("q130_gate_observations_attack.json", 131),
    ):
        doc = json.loads((PHASE_B / name).read_text())
        assert len(doc["observations"]) == expected_count
        assert "evaluator" not in doc


def test_dft_mapping_exposes_serialized_slot_only_to_evaluator():
    mapping = json.loads(
        (ROOT / "gate_reference" / "results" / "evaluator" / "target_mapping.json").read_text()
    )
    assert mapping["scan_cell_count"] == 256
    assert mapping["target"]["scan_slot"] == 0
    assert mapping["target"]["serialized_scan_out_index"] == 255


def test_adaptive_loop_reaches_key_uniqueness_without_unknown():
    q129 = json.loads((PHASE_B / "q129_gate_adaptive_solver.json").read_text())
    q130 = json.loads((PHASE_B / "q130_gate_adaptive_solver.json").read_text())

    assert q129["first_result"] == "sat"
    assert q129["second_result"] == "sat"
    assert q129["timeout"] is False
    assert q129["z3_reason_unknown"] == ""
    assert q130["first_result"] == "sat"
    assert q130["second_result"] == "unsat"
    assert q130["classification"] == "full_key_unique"
    assert q130["confirmed_unique_candidate"] is True
    assert q130["first_model_correct"] is True
    assert q130["timeout"] is False
    assert q130["z3_reason_unknown"] == ""


def test_phase2a_and_heldout_requirements_pass():
    phase2a = json.loads((PHASE_B / "q129_phase2a_known_separator_solver.json").read_text())
    heldout = json.loads((PHASE_B / "phase0_heldout_check.json").read_text())
    audit = json.loads((ROOT / "gate_reference" / "results" / "evaluator" / "information_flow_audit.json").read_text())

    assert phase2a["first_result"] == "sat"
    assert phase2a["second_result"] == "unsat"
    assert phase2a["classification"] == "full_key_unique"
    assert phase2a["timeout"] is False
    assert heldout["all_match"] is True
    assert heldout["same_slot_across_schedules"] is True
    assert audit["status"] == "PASS"
    assert audit["violations"] == []


def test_anonymous_mc_hypothesis_transcript_has_no_ground_truth_label():
    for name, expected_count in (
        ("q128_mc_hypotheses_attack.json", 129),
        ("q129_mc_hypotheses_attack.json", 130),
        ("q130_mc_hypotheses_attack.json", 131),
    ):
        doc = json.loads((PHASE_B / name).read_text())
        assert len(doc["experiment"]["hypotheses"]) == 32
        assert len(doc["observations"]) == expected_count
        text = (PHASE_B / name).read_text()
        assert "MC_9" not in text
        assert "MC9" not in text
        assert "evaluator" not in text
        assert "true_key_hex" not in text


def test_anonymous_hypothesis_attribution_and_eda_handoff():
    q128 = json.loads((PHASE_B / "q128_mc_hypothesis_solver_attack.json").read_text())
    q129 = json.loads((PHASE_B / "q129_mc_hypothesis_solver_attack.json").read_text())
    q130 = json.loads((PHASE_B / "q130_mc_hypothesis_solver_attack.json").read_text())
    primary = json.loads((PHASE_B / "q130_gate_adaptive_solver.json").read_text())

    assert q128["initial_hypothesis_count"] == 32
    assert q128["surviving_hypothesis_count"] == 1
    assert q128["surviving_hypotheses"][0]["hypothesis_id"] == "h09"
    assert q128["attack_used_ground_truth_mc9"] is False
    assert q128["attack_used_hidden_key"] is False
    assert q128["joint_key_uniqueness"]["first_result"] == "sat"
    assert q128["joint_key_uniqueness"]["second_result"] == "sat"
    assert q128["joint_key_uniqueness"]["classification"] == "ambiguity"
    assert q128["joint_key_uniqueness"]["unknown"] is False
    assert q128["joint_key_uniqueness"]["timeout"] is False
    assert q129["joint_key_uniqueness"]["classification"] == "ambiguity"
    assert q130["joint_key_uniqueness"]["classification"] == "ambiguity"
    q131 = json.loads((PHASE_B / "q131_mc_hypothesis_solver_attack.json").read_text())
    assert q131["joint_key_uniqueness"]["first_result"] == "sat"
    assert q131["joint_key_uniqueness"]["second_result"] == "unsat"
    assert q131["joint_key_uniqueness"]["classification"] == "full_key_unique"
    assert q131["joint_key_uniqueness"]["unknown"] is False
    assert q131["joint_key_uniqueness"]["timeout"] is False

    # Anonymous attribution is handed into the already validated MC9 EDA
    # recovery stream; that primary stream proves the final full-key verdict.
    assert primary["first_result"] == "sat"
    assert primary["second_result"] == "unsat"
    assert primary["classification"] == "full_key_unique"
    assert primary["timeout"] is False
    assert primary["z3_reason_unknown"] == ""
