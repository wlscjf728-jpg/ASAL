from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_heldout_refinement_preserves_selected_mc_slot():
    from scan_channel_generator import build_trial, build_holdout
    from discover_mc_channel import analyze_trial
    from refine_mc_channel import evaluate_candidate

    anonymous, ground_truth = build_trial(17, {"n_scan_ff": 64, "seed": 17})
    result = analyze_trial(anonymous, ground_truth, top_k=5)
    holdout = build_holdout(17, {"n_scan_ff": 64, "seed": 17}, ground_truth)
    metrics = evaluate_candidate(result["ranked_slots"][0]["scan_slot"], holdout, ground_truth)
    assert metrics["scan_slot"] == ground_truth["target_mc_slots"][0]
    assert metrics["heldout_signature_match"] is True
    assert metrics["pre_round"] is True

