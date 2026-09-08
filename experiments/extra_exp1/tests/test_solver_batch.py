from pathlib import Path
import json

def test_solver_outputs():
    base = Path(__file__).resolve().parents[1] / "cases"
    # All topology cases have terminal completion artifacts.
    completed_indices = list(range(1, 9))
    for i in completed_indices:
        cname = f"case_{i:02d}_mc"
        matching = list(base.glob(f"{cname}*"))
        assert len(matching) == 1
        cdir = matching[0]
        final_summary = cdir / "results" / "phase_b" / "final_attribution_closed_loop.json"
        if i == 6:
            q135 = cdir / "results" / "phase_b" / "q135_mc_hypothesis_solver_attack.json"
            assert q135.exists(), f"Missing Q135 final solver artifact in {cdir.name}"
            data = json.loads(q135.read_text())
            joint = data["joint_key_uniqueness"]
            assert data["surviving_hypothesis_count"] == 1
            assert (joint["first_result"], joint["second_result"]) == ("sat", "unsat")
            assert joint["classification"] == "full_key_unique"
            continue
        assert final_summary.exists(), f"Missing final summary in {cdir.name}"
        data = json.loads(final_summary.read_text())
        assert data["surviving_hypothesis_count"] == 1
        assert data["final_classification"] == "full_key_unique"
        assert data["final_key_match"] is True

def test_attribution_all_cases():
    base = Path(__file__).resolve().parents[1] / "cases"
    # All 8 cases completed Phase 0 scan discovery and 32->1 attribution
    for i in range(1, 9):
        cname = f"case_{i:02d}_mc"
        matching = list(base.glob(f"{cname}*"))
        assert len(matching) == 1
        cdir = matching[0]
        q128_sol = cdir / "results" / "phase_b" / "q128_mc_hypothesis_solver_attack.json"
        assert q128_sol.exists(), f"Missing Q128 attribution in {cdir.name}"
        data = json.loads(q128_sol.read_text())
        assert data["surviving_hypothesis_count"] == 1
