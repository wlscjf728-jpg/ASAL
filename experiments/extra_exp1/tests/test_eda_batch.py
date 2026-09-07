from pathlib import Path

def test_eda_outputs_exist():
    base = Path(__file__).resolve().parents[1] / "cases"
    for i in range(1, 9):
        cname = f"case_{i:02d}_mc"
        matching = list(base.glob(f"{cname}*"))
        assert len(matching) == 1, f"Expected 1 case matching {cname}"
        cdir = matching[0]
        netlist = cdir / "netlist" / "extra_exp_postscan.v"
        assert netlist.exists(), f"Missing postscan netlist in {cdir.name}"
        scan_path = cdir / "results" / "evaluator" / "scan_path.rpt"
        assert scan_path.exists(), f"Missing scan_path.rpt in {cdir.name}"
