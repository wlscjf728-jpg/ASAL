"""Export an anonymous one-slot observation for downstream recovery adapters."""
from __future__ import annotations

import json
from pathlib import Path


def export_observation(result: dict, trial: dict, output_path: str | Path) -> None:
    slot = result["selected_slot"]
    if slot is None:
        raise ValueError("cannot export without selected slot")
    observations = []
    for row in trial["observations"]:
        if row["aes_started"] and row["schedule"] == "mc_capture":
            observations.append({"query_id": row["query_id"], "plaintext_hex": row["plaintext_hex"], "differential_bit": result["ranked_slots"][0]["differential_signatures"]["mc_capture"][int(row["query_id"])]})
    payload = {
        "schema": "anonymous-mc-channel-observation-v1",
        "trial_id": trial["trial_id"],
        "scan_slot": slot,
        "tap_count": 1,
        "capture_schedule": "mc_capture",
        "reference_plaintext_hex": trial["plaintexts"][0]["plaintext_hex"],
        "differential_signatures": observations,
        "semantic_hypotheses": [{"stage": "MC", "column": result["ranked_slots"][0]["closest_mc_column"]}],
        "source": "anonymous_scan_channel_discovery",
    }
    Path(output_path).write_text(json.dumps(payload, indent=2) + "\n")
