from pathlib import Path


def test_capture_has_no_truth_fields():
    text = Path("extra_exp/defense_boundary/tb/tb_defense_capture.sv").read_text()
    assert "MC_9" not in text
    assert "MC_REG[9]" not in text
    assert "hidden_key" not in text
    assert "scan_path" not in text
