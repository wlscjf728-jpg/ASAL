from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_selector_returns_only_all_ambiguous_early4bit_topologies():
    import select_early4bit_ambiguity_runs as selector

    rows = selector.select()
    assert len(rows) == 69
    assert {row["tap_count"] for row in rows} == {4}
    assert {row["source_phase"] for row in rows} == {"7"}
    assert {row["query_count"] for row in rows} == {128, 192, 255}


def test_pair_unsat_requires_global_unsat_for_nonrecovery(monkeypatch, tmp_path):
    import run_early4bit_pair_rescue as rescue

    task = rescue.RunTask(
        "r", {"seed": "0", "query_count": "128", "depth": "2", "mode": "differential"},
        tuple({"tap_id": f"t{i}", "candidate_id": candidate, "stage": candidate.split("_")[0], "bit_index": int(candidate.split("_")[1])}
              for i, candidate in enumerate(("SB_4", "SB_51", "SB_80", "SR_27"))),
        rescue.test_config(), tmp_path / "checkpoint.json", tmp_path / "result.json",
    )
    ambiguous = {"first_result": "sat", "second_result": "sat", "first_model_hex": bytes(16).hex(), "alternative_model": (bytes([1]) + bytes(15)).hex()}
    monkeypatch.setattr(rescue, "solver_result", lambda *_: ambiguous)
    monkeypatch.setattr(rescue, "generate_observation", lambda *_: {})
    monkeypatch.setattr(rescue, "synthesize_for_candidate_pair", lambda *_: {"status": "unsat"})
    monkeypatch.setattr(rescue, "synthesize_distinguishing_query", lambda *_: {"status": "unsat"})

    result = rescue.run_task(task)
    assert result["terminal_classification"] == "proven_observational_non_recovery"
