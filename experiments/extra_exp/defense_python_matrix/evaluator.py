from __future__ import annotations

from typing import Any

from .model import StageResult


def aggregate_verdict(stages: list[StageResult]) -> str:
    statuses = {stage.status for stage in stages}
    if "access_denied" in statuses or "query_denied" in statuses:
        return "BLOCKED_BY_POLICY"
    if "unresolved" in statuses or "unknown" in statuses or "timeout" in statuses:
        return "UNRESOLVED"
    if "no_channel" in statuses or "identity_unstable" in statuses:
        return "NO_ATTRIBUTABLE_CHANNEL"
    if "full_key_unique" in statuses:
        return "ATTACK_SUCCESS"
    if "ambiguity" in statuses:
        return "AMBIGUOUS_AFTER_ALLOWED_QUERIES"
    if "inconsistent" in statuses:
        return "NO_ATTRIBUTABLE_CHANNEL"
    return "INVALID_EXPERIMENT"


def evaluate_correctness(result: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    phase0 = result.get("phase0", {})
    selected = phase0.get("selected_slot")
    expected = truth.get("expected_output_slot")
    final_solver = result.get("final", {}).get("solver", {})
    joint = final_solver.get("joint_key_uniqueness", {})
    first_model = joint.get("first_model_hex", "")
    true_key = truth.get("true_key_hex", "")
    return {
        "selected_slot": selected,
        "expected_output_slot": expected,
        "slot_match": expected is not None and selected == expected,
        "key_match": bool(first_model and true_key and first_model == true_key),
        "attack_verdict_independent_of_truth": True,
    }

