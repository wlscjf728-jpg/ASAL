import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dft_report_has_target_and_256_cells_after_dft():
    report_path = ROOT / "results" / "evaluator" / "target_mapping.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["scan_cell_count"] == 256
    assert report["target"]["rtl_signal"] == "aes_core.MC_REG[9]"
    assert 0 <= report["target"]["scan_slot"] < 256


def test_scan_path_excludes_key_cells_after_dft():
    report_path = ROOT / "results" / "evaluator" / "scan_path.rpt"
    assert report_path.exists()
    text = report_path.read_text()
    assert "key_reg" not in text
    assert "round_key" not in text
    assert "Scan_path     Cell_#" in text
