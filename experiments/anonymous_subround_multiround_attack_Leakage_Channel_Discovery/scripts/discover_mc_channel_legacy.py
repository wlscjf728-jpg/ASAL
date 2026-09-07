"""Anonymous scan-slot signature extraction and MC-aware ranking."""
from __future__ import annotations

MC_COLUMNS = (
    (0, 5, 10, 15),
    (4, 9, 14, 3),
    (8, 13, 2, 7),
    (12, 1, 6, 11),
)
SCHEDULE_ORDER = ("mc_capture", "round_register_update", "post_update")


def _active_rows(trial: dict, schedule: str) -> list[dict]:
    return [row for row in trial["observations"] if row["aes_started"] and row["schedule"] == schedule]


def _idle_rows(trial: dict, schedule: str) -> list[dict]:
    return [row for row in trial["observations"] if not row["aes_started"] and row["capture_schedule"] == schedule]


def differential_signatures(trial: dict) -> dict[str, dict[int, list[int]]]:
    result = {schedule: {} for schedule in SCHEDULE_ORDER}
    for schedule in SCHEDULE_ORDER:
        rows = _active_rows(trial, schedule)
        base = next(row for row in rows if int(row["query_id"]) == 0)["scan_bits"]
        for row in rows:
            result[schedule][int(row["query_id"])] = [value ^ base[index] for index, value in enumerate(row["scan_bits"])]
    return result


def _plaintext_byte(point_hex: str) -> int | None:
    point = bytes.fromhex(point_hex)
    changed = [index for index, value in enumerate(point) if value]
    return changed[0] if len(changed) == 1 else None


def _support_for_slot(trial: dict, signatures: dict[str, dict[int, list[int]]], slot: int, schedule: str) -> set[int]:
    support = set()
    points = {int(row["query_id"]): row["plaintext_hex"] for row in trial["observations"] if row["aes_started"]}
    for query_id, vector in signatures[schedule].items():
        if query_id and vector[slot]:
            byte_index = _plaintext_byte(points[query_id])
            if byte_index is not None:
                support.add(byte_index)
    return support


def _column_score(support: set[int]) -> tuple[float, int | None]:
    if not support:
        return 0.0, None
    scores = []
    for column, expected in enumerate(MC_COLUMNS):
        expected_set = set(expected)
        scores.append((len(support & expected_set) / len(support | expected_set), column))
    return max(scores)


def _first_active(signatures: dict[str, dict[int, list[int]]], slot: int) -> str | None:
    for schedule in SCHEDULE_ORDER:
        if any(vector[slot] for vector in signatures[schedule].values() if vector):
            return schedule
    return None


def score_slots(trial: dict, weights: dict[str, float] | None = None) -> list[dict]:
    weights = weights or {"stable": 0.20, "activity": 0.25, "timing": 0.30, "support": 0.25}
    signatures = differential_signatures(trial)
    rows = []
    slot_count = int(trial["scan_slot_count"])
    for slot in range(slot_count):
        stable = float(all(len(row["scan_bits"]) == slot_count for row in trial["observations"]))
        activity = sum(bool(vector[slot]) for vector in signatures["mc_capture"].values())
        total_activity = sum(len(vector) for vector in signatures["mc_capture"].values())
        activity_score = activity / max(1, len(signatures["mc_capture"]))
        first_active = _first_active(signatures, slot)
        timing_score = 1.0 if first_active == "mc_capture" else 0.0
        support = _support_for_slot(trial, signatures, slot, "mc_capture")
        support_score, closest_column = _column_score(support)
        score = weights["stable"] * stable + weights["activity"] * activity_score + weights["timing"] * timing_score + weights["support"] * support_score
        rows.append({
            "scan_slot": slot,
            "score": round(score, 8),
            "stable_slot_score": round(stable, 8),
            "aes_activity_score": round(activity_score, 8),
            "pre_round_timing_score": round(timing_score, 8),
            "first_active_capture_schedule": first_active,
            "observed_plaintext_byte_support": sorted(support),
            "closest_mc_column": closest_column,
            "mc_column_support_score": round(support_score, 8),
            "differential_signatures": {schedule: [vector[slot] for _, vector in sorted(signatures[schedule].items())] for schedule in SCHEDULE_ORDER},
            "total_activity": total_activity,
        })
    return sorted(rows, key=lambda row: (-row["score"], row["scan_slot"]))


def analyze_trial(trial: dict, ground_truth: dict | None = None, top_k: int = 10) -> dict:
    ranked = score_slots(trial)
    top = ranked[:top_k]
    selected = ranked[0] if ranked else None
    if ground_truth is None:
        classification = "UNRESOLVED"
        recall = {f"top_{k}": None for k in (1, 5, 10)}
    else:
        target = set(ground_truth["target_mc_slots"])
        recall = {f"top_{k}": bool(target & {row["scan_slot"] for row in ranked[:k]}) for k in (1, 5, 10)}
        selected_is_target = selected is not None and selected["scan_slot"] in target
        classification = "PASS" if selected_is_target and selected["first_active_capture_schedule"] == "mc_capture" else "FAIL"
    return {"schema": "mc-channel-discovery-result-v1", "trial_id": trial["trial_id"], "scan_ff_count": trial["scan_slot_count"], "aes_dependent_candidate_count": sum(row["aes_activity_score"] > 0 for row in ranked), "pre_round_candidate_count": sum(row["first_active_capture_schedule"] == "mc_capture" for row in ranked), "ranked_slots": top, "selected_slot": selected["scan_slot"] if selected else None, "top_k_recall": recall, "classification": classification}
