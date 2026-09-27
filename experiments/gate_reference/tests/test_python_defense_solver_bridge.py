import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gate_reference.defense_python_matrix.solver_bridge import (  # noqa: E402
    build_q0_transcript,
    classify_solver_result,
)


def _manifest():
    return {
        "queries": [
            {"query_id": 0, "plaintext_hex": "00" * 16},
            {"query_id": 1, "plaintext_hex": "01" + "00" * 15},
        ]
    }


def _capture():
    return [
        {"query_id": 0, "capture_schedule": 1, "scan_vector_hex": "0" * 64},
        {"query_id": 0, "capture_schedule": 3, "scan_vector_hex": "0" * 64},
        {"query_id": 1, "capture_schedule": 1, "scan_vector_hex": f"{1 << 255:064x}"},
        {"query_id": 1, "capture_schedule": 3, "scan_vector_hex": f"{1 << 255:064x}"},
    ]


def test_bridge_builds_anonymous_32_hypothesis_transcript():
    doc = build_q0_transcript(_capture(), _manifest(), 255)
    assert doc["schema"] == "aes-sparse-gate-hypothesis-bridge-v1"
    assert len(doc["experiment"]["hypotheses"]) == 32
    assert len(doc["observations"]) == 2
    assert doc["experiment"]["source"]["scan_slot"] == 255
    text = str(doc)
    assert "MC_9" not in text
    assert "MC9" not in text
    assert "true_key_hex" not in text


def test_solver_classification_uses_both_solves():
    def result(first, second):
        return {"joint_key_uniqueness": {"first_result": first, "second_result": second}}

    assert classify_solver_result(result("sat", "unsat")) == "full_key_unique"
    assert classify_solver_result(result("sat", "sat")) == "ambiguity"
    assert classify_solver_result(result("sat", "unknown")) == "unresolved"
    assert classify_solver_result(result("unsat", "not_run")) == "inconsistent"
