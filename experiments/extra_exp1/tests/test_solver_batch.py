from pathlib import Path
import json

def test_solver_outputs():
    base = Path(__file__).resolve().parents[1] / "cases"
    # Verified completed cases: 1, 2, 3, 4, 5, 7, 8
    completed_indices = [1, 2, 3, 4, 5, 7, 8]
    for i in completed_indices:
        cname = f"case_{i:02d}_mc"
        matching = list(base.glob(f"{cname}*"))
        assert len(matching) == 1
        cdir = matching[0]
        final_summary = cdir / "results" / "phase_b" / "final_attribution_closed_loop.json"
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
