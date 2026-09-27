"""Ground-truth-only evaluation for anonymous MC channel rankings."""
from __future__ import annotations


def evaluate_result(result: dict, ground_truth: dict, refinement: dict | None = None) -> dict:
    targets = set(ground_truth.get("target_mc_slots", []))
    ranked = result.get("ranked_slots", [])
    selected = result.get("selected_slot")
    recall = {f"top_{k}": bool(targets & {row["scan_slot"] for row in ranked[:k]}) if targets else False for k in (1, 5, 10)}
    selected_row = next((row for row in ranked if row["scan_slot"] == selected), None)
    if not targets:
        classification = "FAIL" if selected_row and selected_row["first_active_capture_schedule"] == "mc_capture" else "PASS"
        false_positive = classification == "FAIL"
    else:
        heldout_ok = refinement is None or bool(refinement.get("heldout_signature_match"))
        classification = "PASS" if selected in targets and selected_row and selected_row["first_active_capture_schedule"] == "mc_capture" and heldout_ok else "FAIL"
        false_positive = False
    return {"classification": classification, "target_mc_slots": sorted(targets), "selected_slot": selected, "top_k_recall": recall, "false_positive": false_positive, "refinement": refinement}
