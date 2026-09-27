from pathlib import Path
import json

def test_8_cases_generated():
    base = Path(__file__).resolve().parents[1] / "cases"
    expected_cases = [
        ("case_01_mc009", 9, "C0"),
        ("case_02_mc018", 18, "C0"),
        ("case_03_mc036", 36, "C1"),
        ("case_04_mc054", 54, "C1"),
        ("case_05_mc064", 64, "C2"),
        ("case_06_mc082", 82, "C2"),
        ("case_07_mc100", 100, "C3"),
        ("case_08_mc118", 118, "C3"),
    ]
    for cname, bit, col in expected_cases:
        cdir = base / cname
        assert cdir.exists(), f"{cname} does not exist"
        manifest = (cdir / "dft" / "partial_scan_manifest.txt").read_text()
        assert f"target_mc{bit}|aes_core/MC_REG[{bit}]" in manifest
        fcase = json.loads((cdir / "inputs" / "frozen_case.json").read_text())
        assert fcase["tap"]["bit_index"] == bit
        assert fcase["column"] == col
