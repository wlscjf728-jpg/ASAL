import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from extra_exp.defense_python_matrix.phase0 import run_phase0_discovery  # noqa: E402
from extra_exp.defense_python_matrix.adapters import transform_capture  # noqa: E402
from extra_exp.defense_python_matrix.scan_bank import (  # noqa: E402
    build_scan_bank,
    write_attack_capture,
)


ROOT = Path(__file__).resolve().parents[2]
PHASE0_INPUT = ROOT / "extra_exp" / "inputs" / "phase0_queries.json"


def test_keyless_scan_bank_reproduces_mc_channel_discovery(tmp_path):
    queries = json.loads(PHASE0_INPUT.read_text())["queries"]
    key = bytes(range(16))
    bank = build_scan_bank(queries, key)
    attack_capture = tmp_path / "capture.txt"
    repeat_capture = tmp_path / "repeat.txt"
    no_start_capture = tmp_path / "no_start.txt"
    write_attack_capture(bank["attack"], attack_capture)
    write_attack_capture(bank["repeat"], repeat_capture)
    write_attack_capture(bank["no_start"], no_start_capture)

    result = run_phase0_discovery(attack_capture, repeat_capture, no_start_capture)

    assert result["total_scan_ff"] == 256
    assert result["query_count"] == 65
    assert result["final_selected_slot"]["scan_out_index"] == 255
    assert result["final_selected_slot"]["nearest_mc_column"] == "C0"
    assert result["final_selected_slot"]["exact_four_byte_support"] is True
    assert result["final_selected_slot"]["repeat_stable"] is True
    assert result["final_selected_slot"]["start_activity_vs_no_start"] is True

    attack_text = attack_capture.read_text()
    assert "MC_9" not in attack_text
    assert "MC9" not in attack_text
    assert key.hex() not in attack_text
    assert "target_slot" not in attack_text


def test_scan_bank_generation_is_deterministic_and_separates_truth():
    queries = json.loads(PHASE0_INPUT.read_text())["queries"]
    first = build_scan_bank(queries, bytes(range(16)))
    second = build_scan_bank(queries, bytes(range(16)))
    assert first["attack"] == second["attack"]
    assert first["repeat"] == second["repeat"]
    assert first["no_start"] == second["no_start"]
    assert first["evaluator"]["target_slot"] == 255
    assert first["evaluator"]["target_bit"] == 9
    assert first["evaluator"]["target_slot"] not in first["attack"]


def test_state_only_protection_removes_round_state_decoy_but_keeps_mc_target():
    from extra_exp.defense_python_matrix.model import DefenseCondition

    queries = json.loads(PHASE0_INPUT.read_text())["queries"]
    raw = build_scan_bank(queries, bytes(range(16)))["attack"]
    protected, _ = transform_capture(raw, DefenseCondition(
        condition_id="D1", family="sensitive_state", description="test",
        transform="state_only", authorization="allow", secret_id=None,
        adaptive_allowed=True, expected_boundary="post_mc_exposed",
    ))
    raw_state = [row for row in raw if int(row["capture_schedule"]) in (2, 3)]
    protected_state = [row for row in protected if int(row["capture_schedule"]) in (2, 3)]
    assert any((int(row["scan_vector_hex"], 16) >> 240) & 1 for row in raw_state)
    assert not any((int(row["scan_vector_hex"], 16) >> 240) & 1 for row in protected_state)
    assert any((int(row["scan_vector_hex"], 16) >> 255) & 1 for row in protected)
