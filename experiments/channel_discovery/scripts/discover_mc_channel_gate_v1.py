"""Validated anonymous MC-channel analyzer with a support-consistency gate."""
from __future__ import annotations

import discover_mc_channel_legacy as _legacy

MC_COLUMNS = _legacy.MC_COLUMNS
SCHEDULE_ORDER = _legacy.SCHEDULE_ORDER
differential_signatures = _legacy.differential_signatures
score_slots = _legacy.score_slots


def analyze_trial(trial: dict, ground_truth: dict | None = None, top_k: int = 10) -> dict:
    all_rows = score_slots(trial)
    eligible = [
        row for row in all_rows
        if len(row["observed_plaintext_byte_support"]) >= 3
        and row["mc_column_support_score"] >= 0.5
        and row["first_active_capture_schedule"] == "mc_capture"
    ]
    ranked = eligible[:top_k]
    selected = ranked[0] if ranked else None
    if ground_truth is None:
        classification = "UNRESOLVED"
        recall = {f"top_{k}": None for k in (1, 5, 10)}
    else:
        target = set(ground_truth["target_mc_slots"])
        recall = {f"top_{k}": bool(target & {row["scan_slot"] for row in ranked[:k]}) for k in (1, 5, 10)}
        classification = "PASS" if selected is not None and selected["scan_slot"] in target else "FAIL"
    return {
        "schema": "mc-channel-discovery-result-v1",
        "trial_id": trial["trial_id"],
        "scan_ff_count": trial["scan_slot_count"],
        "aes_dependent_candidate_count": sum(row["aes_activity_score"] > 0 for row in all_rows),
        "pre_round_candidate_count": sum(row["first_active_capture_schedule"] == "mc_capture" for row in all_rows),
        "support_consistent_candidate_count": len(eligible),
        "ranked_slots": ranked,
        "selected_slot": selected["scan_slot"] if selected else None,
        "top_k_recall": recall,
        "classification": classification,
    }
