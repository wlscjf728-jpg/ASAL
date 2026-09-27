from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_late1bit_fixed_baseline as baseline


def load_config():
    return yaml.safe_load((ROOT / "configs/late_1bit_fixed_q128.yaml").read_text())


def test_builds_96_q128_single_tap_runs_and_skips_terminal_results(tmp_path):
    config = load_config()
    tasks = baseline.load_tasks(config, tmp_path / "runs")

    assert len(tasks) == 96
    assert {task.seed for task in tasks} == {0, 1, 2}
    assert all(len(task.taps) == 1 for task in tasks)
    assert all(task.query_count == 128 for task in tasks)

    completed = tasks[0]
    completed.result_path.parent.mkdir()
    completed.result_path.write_text(json.dumps({
        "schema": baseline.RESULT_SCHEMA,
        "run_id": completed.run_id,
        "state": "terminal",
    }))
    assert len(baseline.load_tasks(config, tmp_path / "runs")) == 95


def test_q128_fixed_query_classifications_are_explicit(monkeypatch, tmp_path):
    task = baseline.load_tasks(load_config(), tmp_path / "runs")[0]
    observed = []
    monkeypatch.setattr(
        baseline,
        "generate_observation",
        lambda key, taps, plaintexts, depth, mode: observed.append((len(taps), len(plaintexts), depth, mode)) or {},
    )

    monkeypatch.setattr(
        baseline,
        "solver_result",
        lambda doc, config: {"first_result": "sat", "second_result": "sat", "classification": "ambiguity"},
    )
    result = baseline.run_fixed_baseline(task)
    assert result["terminal_classification"] == "finite_query_ambiguity"
    assert result["phase2_eligible"] is True
    assert observed == [(1, 129, 2, "differential")]


def test_unknown_is_not_a_terminal_ambiguity(monkeypatch, tmp_path):
    task = baseline.load_tasks(load_config(), tmp_path / "runs")[0]
    monkeypatch.setattr(baseline, "generate_observation", lambda *args: {})
    monkeypatch.setattr(
        baseline,
        "solver_result",
        lambda doc, config: {"first_result": "sat", "second_result": "unknown", "classification": "undecided"},
    )

    result = baseline.run_fixed_baseline(task)
    assert result["state"] == "nonterminal"
    assert result["terminal_classification"] == "solver_unresolved"
    assert result["phase2_eligible"] is False
