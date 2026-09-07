from pathlib import Path

def test_shared_files_exist():
    base = Path(__file__).resolve().parents[1] / "shared"
    assert (base / "rtl" / "aes128_iterative_mc_boundary.sv").exists()
    assert (base / "tb" / "tb_gate_capture.sv").exists()
    assert (base / "dft" / "run_dc.tcl").exists()
    assert (base / "scripts" / "semantic_reference.py").exists()
