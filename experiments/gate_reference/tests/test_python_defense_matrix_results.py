import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "gate_reference" / "defense_python_matrix" / "results"
SUMMARY = RESULTS / "defense_matrix_summary.json"


EXPECTED = {
    "D0": "ATTACK_SUCCESS",
    "D1": "ATTACK_SUCCESS",
    "D1b": "NO_ATTRIBUTABLE_CHANNEL",
    "D2": "NO_ATTRIBUTABLE_CHANNEL",
    "D3a": "ATTACK_SUCCESS",
    "D3b": "NO_ATTRIBUTABLE_CHANNEL",
    "D4": "BLOCKED_BY_POLICY",
    "D5a": "ATTACK_SUCCESS",
    "D5b": "ATTACK_SUCCESS",
    "D5c": "NO_ATTRIBUTABLE_CHANNEL",
    "D5d": "NO_ATTRIBUTABLE_CHANNEL",
    "D6_valid": "ATTACK_SUCCESS",
    "D6_invalid": "BLOCKED_BY_POLICY",
    "D7": "BLOCKED_BY_POLICY",
    "D8_xorhash": "NO_ATTRIBUTABLE_CHANNEL",
}


def test_matrix_has_explicit_verdict_for_every_condition():
    summary = json.loads(SUMMARY.read_text())
    actual = {row["condition_id"]: row["attack_verdict"] for row in summary["results"]}
    assert actual == EXPECTED
    assert summary["condition_count"] == len(EXPECTED)


def test_success_is_backed_by_final_unique_and_no_unknown():
    for condition_id, verdict in EXPECTED.items():
        result = json.loads((RESULTS / condition_id / "attack_result.json").read_text())
        text = json.dumps(result)
        assert "UNKNOWN" not in text
        assert "unknown" not in text.lower() or '"unknown": false' in text.lower()
        if verdict == "ATTACK_SUCCESS":
            assert result["final"]["classification"] == "full_key_unique"
            assert result["fixed"]["classification"] == "ambiguity"
        if verdict == "BLOCKED_BY_POLICY":
            assert result["first_blocked_stage"]


def test_attack_artifacts_do_not_contain_evaluator_truth():
    forbidden = ("true_key_hex", "MC_9", "MC9", "scan_mapping", "response_hiding_secret")
    for path in RESULTS.glob("*/attack_result.json"):
        text = path.read_text()
        for value in forbidden:
            assert value not in text
    for path in RESULTS.glob("*/fixed_transcript.json"):
        text = path.read_text()
        assert "MC_9" not in text
        assert "MC9" not in text


def test_information_flow_audit_passes_and_truth_is_separate():
    audit = json.loads((RESULTS / "information_flow_audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["evaluator_truth_excluded"] is True
    for condition_id in EXPECTED:
        assert (RESULTS / condition_id / "evaluator_truth.json").is_file()
        assert (RESULTS / condition_id / "evaluator_correctness.json").is_file()
