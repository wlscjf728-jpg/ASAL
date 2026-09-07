import re
from pathlib import Path


def test_profiles_have_stable_external_ports():
    text = Path("extra_exp/defense_boundary/rtl/defense_exp_top.sv").read_text()
    for port in ("clk", "reset_n", "start", "plaintext", "key", "test_mode", "scan_en", "scan_in", "scan_capture", "scan_out", "ciphertext"):
        assert re.search(rf"\b{port}\b", text)


def test_mc_protection_scope_is_explicit():
    text = Path("extra_exp/defense_boundary/rtl/defense_control.sv").read_text()
    assert "PROFILE_ROUND_ONLY" in text
    assert "PROFILE_ROUND_PLUS_MC" in text
    assert "PROFILE_MODE_RESET" in text
