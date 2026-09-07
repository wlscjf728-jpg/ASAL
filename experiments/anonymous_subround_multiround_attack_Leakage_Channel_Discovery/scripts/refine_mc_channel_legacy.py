"""Held-out and joint-response checks for ranked anonymous slots."""
from __future__ import annotations

from discover_mc_channel import differential_signatures


def _signature_for_slot(trial: dict, slot: int) -> tuple:
    signatures = differential_signatures(trial)
    return tuple((schedule, tuple(vector[slot] for _, vector in sorted(signatures[schedule].items()))) for schedule, values in signatures.items() for _ in [values])


def evaluate_candidate(scan_slot: int, holdout: dict, ground_truth: dict) -> dict:
    target_slots = set(ground_truth["target_mc_slots"])
    target = min(target_slots)
    candidate_signature = _signature_for_slot(holdout, scan_slot)
    target_signature = _signature_for_slot(holdout, target)
    candidate_row = next(row for row in holdout["observations"] if row["aes_started"])
    _ = candidate_row
    first_active = None
    signatures = differential_signatures(holdout)
    for schedule in ("mc_capture", "round_register_update", "post_update"):
        if any(vector[scan_slot] for vector in signatures[schedule].values()):
            first_active = schedule
            break
    return {"scan_slot": scan_slot, "heldout_signature_match": candidate_signature == target_signature, "pre_round": first_active == "mc_capture", "is_ground_truth_mc": scan_slot in target_slots, "joint_superposition_match": None}
