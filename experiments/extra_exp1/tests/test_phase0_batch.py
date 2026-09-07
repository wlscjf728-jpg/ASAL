from pathlib import Path
import json

def test_phase0_discovery_outputs():
    base = Path(__file__).resolve().parents[1] / "cases"
    for i in range(1, 9):
        cname = f"case_{i:02d}_mc"
        matching = list(base.glob(f"{cname}*"))
        assert len(matching) == 1
        cdir = matching[0]
        disc_json = cdir / "results" / "phase_b" / "phase0_discovery.json"
        assert disc_json.exists(), f"Missing phase0_discovery.json in {cdir.name}"
        data = json.loads(disc_json.read_text())
        assert data["total_scan_ff"] == 256
        assert data["aes_dependent_candidate_count"] > 0
        assert data["pre_round_candidate_count"] > 0
        assert data["mc_aware_candidate_count_overlap_ge_3"] >= 1
        assert "final_selected_slot" in data
