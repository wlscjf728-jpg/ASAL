from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_export_has_anonymous_single_slot_observation_only(tmp_path):
    from scan_channel_generator import build_trial
    from discover_mc_channel import analyze_trial
    from export_channel_observation import export_observation

    anonymous, ground_truth = build_trial(19, {"n_scan_ff": 64, "seed": 19})
    result = analyze_trial(anonymous, ground_truth, top_k=5)
    output = tmp_path / "observation.json"
    export_observation(result, anonymous, output)
    data = json.loads(output.read_text())
    assert data["scan_slot"] == ground_truth["target_mc_slots"][0]
    assert "key_hex" not in data
    assert "ground_truth" not in data
    assert data["tap_count"] == 1
    assert data["differential_signatures"]
