"""Validated public entry point for the discovery campaign."""
from __future__ import annotations

import run_discovery_campaign_legacy as _legacy


_original_evaluate_candidate = _legacy.evaluate_candidate


def _evaluate_candidate_if_target_exists(scan_slot, holdout, ground_truth):
    if not ground_truth.get("target_mc_slots"):
        return None
    return _original_evaluate_candidate(scan_slot, holdout, ground_truth)


_legacy.evaluate_candidate = _evaluate_candidate_if_target_exists
main = _legacy.main


if __name__ == "__main__":
    main()
