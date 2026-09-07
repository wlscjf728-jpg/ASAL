import json
from pathlib import Path


def test_variant_matrix_is_complete():
    doc = json.loads(Path("extra_exp/defense_boundary/configs/variant_matrix.json").read_text())
    assert [item["id"] for item in doc["variants"]] == [
        "baseline", "state_protected", "round_only", "round_plus_mc", "mode_reset"
    ]
    assert all(item["scan_length"] == 256 for item in doc["variants"])
