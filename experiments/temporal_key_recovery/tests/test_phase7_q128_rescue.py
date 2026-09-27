from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT.parent / "multibit_baselines"
sys.path.insert(0, str(ROOT / "scripts"))

import run_phase8_campaign as campaign
import run_phase7_q128_rescue as rescue


EXPECTED = {
    ("SB_10__MC_16", 0),
    ("SB_13__MC_14", 0),
    ("SB_17__ARK_92", 2),
    ("SB_37__MC_78", 2),
    ("SB_5__MC_75", 2),
    ("SR_111__MC_6", 1),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_manifest_is_exact_six_direct_q128_ambiguities():
    manifest = rows(ROOT / "configs/phase7_q128_rescue_cases.csv")
    assert {(r["source_case_id"], int(r["seed"])) for r in manifest} == EXPECTED
    assert all(int(r["tap_count"]) == 2 for r in manifest)
    assert all(int(r["source_query_count"]) == 128 for r in manifest)

    raw = rows(PHASE7 / "results/raw_solver_runs_2bit.csv")
    source = {
        (r["case_id"], int(r["seed"]), int(r["query_count"])): r for r in raw
    }
    for case_id, seed in EXPECTED:
        row = source[(case_id, seed, 128)]
        assert row["first_result"] == "sat"
        assert row["second_result"] == "sat"
        assert row["classification"] == "ambiguity"
        assert row["timeout"] == "False"


def test_config_spans_q128_through_q255_with_six_workers():
    config = yaml.safe_load((ROOT / "configs/phase7_q128_rescue.yaml").read_text())
    assert config["campaign"]["workers"] == 6
    assert config["attack"]["initial_query_count"] == 128
    assert config["adaptive_query"]["max_adaptive_queries"] == 127
    assert 128 + 127 == 255
    assert config["solver"]["first_timeout_ms"] == 0
    assert config["solver"]["second_timeout_ms"] == 0
    assert config["adaptive_query"]["separability_timeout_ms"] == 0


def minimal_case():
    return {
        "attack8_case_id": "guard_case",
        "source_phase": "7",
        "source_case_id": "SB_10__MC_16",
        "tap_count": "2",
    }


def mock_unique_solver(monkeypatch):
    monkeypatch.setattr(campaign, "key_for_seed", lambda seed: bytes(16))
    monkeypatch.setattr(
        campaign,
        "nested_plaintexts",
        lambda count, seed: [bytes(16)] * (count + 1),
    )
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(
        campaign,
        "solver_result",
        lambda doc, config: {
            "classification": "full_key_unique",
            "first_result": "sat",
            "second_result": "unsat",
            "first_time": 0.0,
            "second_time": 0.0,
        },
    )


def minimal_config():
    return {
        "attack": {
            "initial_query_count": 128,
            "depth": 2,
            "mode": "differential",
        },
        "adaptive_query": {
            "max_adaptive_queries": 127,
            "query_domain": "unrestricted",
        },
    }


def test_required_initial_ambiguity_rejects_unique_baseline(monkeypatch):
    mock_unique_solver(monkeypatch)
    with pytest.raises(RuntimeError, match="initial transcript is not ambiguous"):
        campaign.sound_adaptive_run(
            minimal_case(),
            0,
            minimal_config(),
            [],
            run_tag="phase7_q128_rescue",
            require_initial_ambiguity=True,
        )


def test_custom_run_tag_is_recorded(monkeypatch):
    mock_unique_solver(monkeypatch)
    result = campaign.sound_adaptive_run(
        minimal_case(),
        0,
        minimal_config(),
        [],
        run_tag="phase7_q128_rescue",
    )
    assert result["run_id"] == "guard_case__seed0__phase7_q128_rescue"


def test_rescue_task_builder_plans_exactly_six(tmp_path):
    config = yaml.safe_load((ROOT / "configs/phase7_q128_rescue.yaml").read_text())
    tasks = rescue.load_tasks(config, tmp_path)
    assert len(tasks) == 6
    assert {seed for _, seed, _, _ in tasks} == {0, 1, 2}
    assert all(int(case["source_query_count"]) == 128 for case, _, _, _ in tasks)
