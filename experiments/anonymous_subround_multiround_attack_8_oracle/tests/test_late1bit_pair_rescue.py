from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_late1bit_pair_rescue as rescue


TAP = {"tap_id": "t0", "candidate_id": "MC_9", "stage": "MC", "bit_index": 9}
CASE = {"case_id": "late1_MC_9", "candidate_id": "MC_9", "stage": "MC", "bit_index": "9"}


def config():
    return yaml.safe_load((ROOT / "configs/late_1bit_pair_rescue.yaml").read_text())


def ambiguous_result():
    return {
        "first_result": "sat",
        "second_result": "sat",
        "classification": "ambiguity",
        "first_model_hex": bytes(16).hex(),
        "alternative_model": (bytes([1]) + bytes(15)).hex(),
    }


def unique_result():
    return {"first_result": "sat", "second_result": "unsat", "classification": "full_key_unique"}


def test_selects_only_q128_finite_ambiguity_runs(tmp_path):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    ambiguous = {
        "schema": "late-1bit-fixed-q128-result-v1", "state": "terminal", "run_id": "a",
        "case_id": CASE["case_id"], "candidate_id": "MC_9", "tap": TAP, "seed": 0,
        "terminal_classification": "finite_query_ambiguity", "query_count": 128,
    }
    unique = {**ambiguous, "run_id": "u", "seed": 1, "terminal_classification": "fixed_query_unique"}
    (baseline / "a.json").write_text(json.dumps(ambiguous))
    (baseline / "u.json").write_text(json.dumps(unique))
    for index in range(1, 32):
        extra = {**ambiguous, "run_id": f"a{index}", "case_id": f"late1_MC_{index}", "seed": index}
        (baseline / f"a{index}.json").write_text(json.dumps(extra))

    tasks = rescue.load_tasks(config(), baseline, tmp_path / "runs", tmp_path / "checkpoints")
    assert len(tasks) == 32
    assert tasks[0].case == CASE
    assert tasks[0].seed == 0
    assert tasks[0].query_count == 128


def test_pair_separator_is_used_without_global_portfolio(monkeypatch, tmp_path):
    point = (bytes([0xA5, 0x5A]) + bytes(14)).hex()
    task = rescue.RunTask("r", CASE, 0, (TAP,), 128, config(), tmp_path / "c.json", tmp_path / "r.json")
    solves = iter([ambiguous_result(), unique_result()])
    global_calls = []
    monkeypatch.setattr(rescue, "solver_result", lambda doc, cfg: next(solves))
    monkeypatch.setattr(rescue, "generate_observation", lambda *args: {})
    monkeypatch.setattr(rescue, "synthesize_for_candidate_pair", lambda *args: {"status": "sat", "plaintext_hex": point})
    monkeypatch.setattr(rescue, "synthesize_distinguishing_query", lambda *args: global_calls.append(True) or {"status": "sat"})

    result = rescue.run_pair_rescue(task)
    assert result["terminal_classification"] == "adaptive_key_recovered"
    assert result["adaptive_query_count"] == 1
    assert global_calls == []


def test_pair_unsat_uses_global_fallback_and_only_global_unsat_is_nonrecovery(monkeypatch, tmp_path):
    task = rescue.RunTask("r", CASE, 0, (TAP,), 128, config(), tmp_path / "c.json", tmp_path / "r.json")
    monkeypatch.setattr(rescue, "solver_result", lambda doc, cfg: ambiguous_result())
    monkeypatch.setattr(rescue, "generate_observation", lambda *args: {})
    monkeypatch.setattr(rescue, "synthesize_for_candidate_pair", lambda *args: {"status": "unsat"})
    monkeypatch.setattr(rescue, "synthesize_distinguishing_query", lambda *args: {"status": "unsat"})

    result = rescue.run_pair_rescue(task)
    assert result["terminal_classification"] == "proven_observational_non_recovery"
