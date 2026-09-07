from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_analyzer_ranks_hidden_mc_slot_for_positive_control():
    from scan_channel_generator import build_trial
    from discover_mc_channel import analyze_trial

    anonymous, ground_truth = build_trial(11, {"n_scan_ff": 64, "seed": 11})
    result = analyze_trial(anonymous, ground_truth, top_k=10)
    assert result["ranked_slots"]
    assert result["ranked_slots"][0]["scan_slot"] == ground_truth["target_mc_slots"][0]
    assert result["classification"] == "PASS"


def test_control_slots_do_not_have_aes_activity():
    from scan_channel_generator import build_trial
    from discover_mc_channel import analyze_trial

    anonymous, ground_truth = build_trial(13, {"n_scan_ff": 64, "seed": 13})
    result = analyze_trial(anonymous, ground_truth, top_k=10)
    control_slots = set(ground_truth["control_slots"])
    assert all(row["scan_slot"] not in control_slots for row in result["ranked_slots"][:1])

