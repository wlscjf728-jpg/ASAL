from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_coarse_queries_have_one_base_and_64_single_byte_differentials():
    from scan_channel_generator import coarse_plaintexts

    points = coarse_plaintexts()
    assert len(points) == 65
    assert points[0] == bytes(16)
    assert all(sum(byte != 0 for byte in point) == 1 for point in points[1:])
    assert {point[next(i for i, value in enumerate(point) if value)] for point in points[1:]} == {1, 2, 4, 8}


def test_anonymous_trial_hides_mapping_and_key(tmp_path):
    from scan_channel_generator import build_trial

    anonymous, ground_truth = build_trial(7, {"n_scan_ff": 64, "seed": 7})
    assert "key_hex" not in anonymous
    assert "scan_sources" not in anonymous
    assert "scan_permutation" not in anonymous
    assert len(anonymous["scan_slots"]) == 64
    assert ground_truth["key_hex"]
    assert ground_truth["scan_sources"]
    assert len(ground_truth["scan_permutation"]) == 64
    assert {row["schedule"] for row in anonymous["observations"]} == {"mc_capture", "round_register_update", "post_update", "idle"}

