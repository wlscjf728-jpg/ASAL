"""Build a scan trial with AES-dependent non-MC decoys but no MC target."""
from __future__ import annotations

from scan_channel_generator import build_trial
import scan_channel_generator_legacy as legacy


def build_decoy_trial(seed: int, config: dict) -> tuple[dict, dict]:
    anonymous, ground_truth = build_trial(seed, config)
    sources = [{key: value for key, value in source.items() if key != "scan_slot"} for source in ground_truth["scan_sources"]]
    for source in sources:
        if source["kind"] == "mc":
            source["kind"] = "control"
            source["stage"] = "CONTROL"
            source["round"] = 0
            source["bit_index"] = 0
    points = [bytes.fromhex(row["plaintext_hex"]) for row in anonymous["plaintexts"]]
    anonymous, _ = legacy._render(seed, config, bytes.fromhex(ground_truth["key_hex"]), sources, list(range(len(sources))), points, f"decoy-{seed}")
    anonymous["scan_slots"] = list(range(int(anonymous["scan_slot_count"])))
    ground_truth["trial_id"] = anonymous["trial_id"]
    ground_truth["scan_sources"] = [{**source, "scan_slot": slot} for slot, source in enumerate(sources)]
    ground_truth["target_mc_slots"] = []
    ground_truth["control_slots"] = list(range(len(sources)))
    return anonymous, ground_truth
