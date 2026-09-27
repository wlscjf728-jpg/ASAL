from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_late1bit_campaign as campaign


TAP = {"tap_id": "t0", "candidate_id": "MC_0", "stage": "MC", "bit_index": 0}
CASE = {
    "case_id": "late1_MC_0",
    "candidate_id": "MC_0",
    "stage": "MC",
    "bit_index": "0",
}


def load_config():
    return yaml.safe_load((ROOT / "configs/late_1bit_adaptive.yaml").read_text())


def unique_result():
    return {"classification": "full_key_unique", "first_result": "sat", "second_result": "unsat"}


def ambiguous_result():
    return {
        "classification": "ambiguity",
        "first_result": "sat",
        "second_result": "sat",
        "first_model_hex": bytes(16).hex(),
        "alternative_model": (bytes([1]) + bytes(15)).hex(),
    }


def test_builds_exact_96_immutable_one_tap_runs_and_skips_completed(tmp_path):
    config = load_config()
    result_dir = tmp_path / "runs"
    checkpoint_dir = tmp_path / "checkpoints"
    tasks = campaign.load_tasks(config, result_dir, checkpoint_dir)

    assert len(tasks) == 96
    assert len({task.run_id for task in tasks}) == 96
    assert {task.seed for task in tasks} == {0, 1, 2}
    assert all(len(task.taps) == 1 for task in tasks)
    assert all(isinstance(task.taps, tuple) for task in tasks)

    first = tasks[0]
    result_dir.mkdir()
    first.result_path.write_text(
        json.dumps({"schema": campaign.RESULT_SCHEMA, "run_id": first.run_id, "state": "terminal"})
    )
    assert len(campaign.load_tasks(config, result_dir, checkpoint_dir)) == 95


def test_workers_are_spawn_bounded_and_dry_run_is_explicit():
    config = load_config()
    assert campaign.effective_workers(96, configured=32, requested=64) == 32
    assert campaign.effective_workers(6, configured=32, requested=32) == 6
    assert campaign.dry_run_line(config, pending=96, requested_workers=32) == (
        "cases=32 seeds=3 runs=96 pending=96 workers=32 "
        "bootstrap=q64 max_adaptive_queries=unlimited depth=2 mode=differential"
    )
    source = (ROOT / "scripts/run_late1bit_campaign.py").read_text()
    assert "while True:" in source
    assert 'multiprocessing.get_context("spawn")' in source


def test_fixed_pair_sat_is_checkpointed_then_exactly_recovers(monkeypatch, tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    point = (bytes([0xA5, 0x5A]) + bytes(14)).hex()
    solves = iter([ambiguous_result(), unique_result()])
    observed = []
    writes = []

    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: next(solves))
    monkeypatch.setattr(
        campaign,
        "generate_observation",
        lambda key, taps, plaintexts, depth, mode: observed.append((tuple(taps), len(plaintexts))) or {},
    )
    monkeypatch.setattr(campaign, "synthesize_for_candidate_pair", lambda *args: {"status": "sat", "plaintext_hex": point})
    monkeypatch.setattr(
        campaign,
        "synthesize_distinguishing_query",
        lambda *args: {"status": "sat", "plaintext_hex": point},
    )
    real_write = campaign.write_atomic
    monkeypatch.setattr(
        campaign,
        "write_atomic",
        lambda path, payload: writes.append(list(payload.get("adaptive_plaintexts_hex", []))) or real_write(path, payload),
    )

    result = campaign.run_late1bit(CASE, 0, load_config(), (TAP,), checkpoint)

    assert result["terminal_classification"] == "adaptive_key_recovered"
    assert result["adaptive_query_count"] == 1
    assert result["total_query_count"] == 65
    assert observed == [((TAP,), 65), ((TAP,), 66)]
    assert writes == [[point]]
    assert json.loads(checkpoint.read_text())["adaptive_plaintexts_hex"] == [point]


def test_pair_unsat_uses_global_sat_fallback(monkeypatch, tmp_path):
    point = (bytes([0xA5, 0x5A]) + bytes(14)).hex()
    solves = iter([ambiguous_result(), unique_result()])
    global_calls = []
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: next(solves))
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(campaign, "synthesize_for_candidate_pair", lambda *args: {"status": "unsat"})
    monkeypatch.setattr(
        campaign,
        "synthesize_distinguishing_query",
        lambda *args: global_calls.append(True) or {"status": "sat", "plaintext_hex": point},
    )

    result = campaign.run_late1bit(CASE, 0, load_config(), (TAP,), tmp_path / "c.json")
    assert result["terminal_classification"] == "adaptive_key_recovered"
    assert global_calls == [True]


def test_only_global_unsat_is_nonrecovery(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: ambiguous_result())
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(campaign, "synthesize_for_candidate_pair", lambda *args: {"status": "unsat"})
    monkeypatch.setattr(campaign, "synthesize_distinguishing_query", lambda *args: {"status": "unsat"})

    result = campaign.run_late1bit(CASE, 0, load_config(), (TAP,), tmp_path / "c.json")
    assert result["terminal_classification"] == "proven_observational_non_recovery"
    assert result["attack_success"] is False


@pytest.mark.parametrize(
    "result",
    [
        {"first_result": "unknown", "second_result": "not_run", "classification": "undecided"},
        {"first_result": "unsat", "second_result": "not_run", "classification": "inconsistent"},
        {"first_result": "sat", "second_result": "unknown", "classification": "undecided"},
    ],
)
def test_unresolved_solver_status_never_becomes_a_verdict(monkeypatch, tmp_path, result):
    checkpoint = tmp_path / "c.json"
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: result)
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})

    with pytest.raises(campaign.NonTerminalState):
        campaign.run_late1bit(CASE, 0, load_config(), (TAP,), checkpoint)
    assert json.loads(checkpoint.read_text())["state"] == "solver_unresolved"


def test_pair_unknown_is_nonterminal_not_global_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: ambiguous_result())
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(campaign, "synthesize_for_candidate_pair", lambda *args: {"status": "unknown"})
    monkeypatch.setattr(
        campaign,
        "synthesize_distinguishing_query",
        lambda *args: pytest.fail("global fallback is allowed only after pair UNSAT"),
    )

    with pytest.raises(campaign.NonTerminalState):
        campaign.run_late1bit(CASE, 0, load_config(), (TAP,), tmp_path / "c.json")


def test_resume_reuses_checkpoint_without_duplicate_query(monkeypatch, tmp_path):
    checkpoint = tmp_path / "c.json"
    point = (bytes([0xA5, 0x5A]) + bytes(14)).hex()
    checkpoint.write_text(
        json.dumps(
            {
                "schema": campaign.CHECKPOINT_SCHEMA,
                "run_id": campaign.run_id(CASE, 0),
                "case_id": CASE["case_id"],
                "candidate_id": CASE["candidate_id"],
                "seed": 0,
                "tap": TAP,
                "bootstrap_query_count": 64,
                "adaptive_plaintexts_hex": [point],
                "steps": [],
                "state": "running",
            }
        )
    )
    observed = []
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: unique_result())
    monkeypatch.setattr(
        campaign,
        "generate_observation",
        lambda key, taps, plaintexts, depth, mode: observed.append([p.hex() for p in plaintexts]) or {},
    )
    monkeypatch.setattr(
        campaign,
        "synthesize_for_candidate_pair",
        lambda *args: pytest.fail("no new separator is needed after resumed recovery"),
    )

    result = campaign.run_late1bit(CASE, 0, load_config(), (TAP,), checkpoint)
    assert result["adaptive_query_count"] == 1
    assert observed[0].count(point) == 1
    assert len(observed[0]) == 66


def test_checkpoint_rejects_a_changed_tap(tmp_path):
    checkpoint = tmp_path / "c.json"
    checkpoint.write_text(
        json.dumps(
            {
                "schema": campaign.CHECKPOINT_SCHEMA,
                "run_id": campaign.run_id(CASE, 0),
                "case_id": CASE["case_id"],
                "candidate_id": CASE["candidate_id"],
                "seed": 0,
                "tap": {**TAP, "bit_index": 1},
                "bootstrap_query_count": 64,
                "adaptive_plaintexts_hex": [],
                "steps": [],
                "state": "running",
            }
        )
    )
    with pytest.raises(ValueError, match="checkpoint identity mismatch"):
        campaign.run_late1bit(CASE, 0, load_config(), (TAP,), checkpoint)


def test_public_launcher_uses_current_python_and_fresh_output():
    import importlib.util
    import sys
    path = ROOT.parents[1] / 'scripts/reproduce.py'
    spec = importlib.util.spec_from_file_location('public_reproduce', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.PYTHON == Path(sys.executable)
    assert module.EXP / 'temporal_key_recovery' == ROOT
    assert 'run-output/one-bit-96' in path.read_text()
