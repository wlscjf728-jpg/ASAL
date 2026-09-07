from __future__ import annotations

from pathlib import Path


COLUMNS = {
    "C0": {0, 5, 10, 15},
    "C1": {4, 9, 14, 3},
    "C2": {8, 13, 2, 7},
    "C3": {12, 1, 6, 11},
}


def _parse(path: Path) -> dict[tuple[int, int], int]:
    rows: dict[tuple[int, int], int] = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) not in (3, 4):
            raise ValueError(f"unexpected capture row: {line}")
        query_id, schedule = int(fields[0]), int(fields[1])
        rows[(query_id, schedule)] = int(fields[-1], 16)
    return rows


def _repeat_stability(path: Path, schedules: list[int]) -> dict[int, bool]:
    rows: dict[int, list[int]] = {schedule: [] for schedule in schedules}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) not in (3, 4):
            continue
        rows[int(fields[1])].append(int(fields[-1], 16))
    return {schedule: len(values) > 0 and len(set(values)) == 1 for schedule, values in rows.items()}


def _query_groups(query_ids: list[int]) -> dict[int, list[int]]:
    groups = {}
    for byte_index in range(16):
        members = [1 + 4 * byte_index + offset for offset in range(4)]
        if all(query_id in query_ids for query_id in members):
            groups[byte_index] = members
    return groups


def run_phase0_discovery(capture: Path, repeat: Path, no_start: Path) -> dict:
    full = _parse(capture)
    repeat_rows = _parse(repeat)
    no_start_rows = _parse(no_start)
    query_ids = sorted({query_id for query_id, _ in full})
    schedules = sorted({schedule for _, schedule in full})
    if query_ids != list(range(65)) or schedules != [1, 2, 3]:
        raise ValueError("expected Phase 0 query IDs 0..64 and schedules 1..3")
    if sorted({query_id for query_id, _ in repeat_rows}) != [0]:
        raise ValueError("repeat control must contain query 0")
    if sorted({query_id for query_id, _ in no_start_rows}) != [0]:
        raise ValueError("no-start control must contain query 0")

    groups = _query_groups(query_ids)
    baseline = {schedule: full[(0, schedule)] for schedule in schedules}
    repeat_ok = _repeat_stability(repeat, schedules)
    no_start_baseline = {schedule: no_start_rows[(0, schedule)] for schedule in schedules}
    candidates = []
    for slot in range(256):
        activity_by_schedule = {}
        support_by_schedule = {}
        for schedule in schedules:
            activity_by_schedule[schedule] = any(
                ((full[(query_id, schedule)] ^ baseline[schedule]) >> slot) & 1
                for query_id in query_ids[1:]
            )
            support = set()
            for byte_index, members in groups.items():
                if any(((full[(query_id, schedule)] ^ baseline[schedule]) >> slot) & 1 for query_id in members):
                    support.add(byte_index)
            support_by_schedule[schedule] = sorted(support)
        first_active = next((schedule for schedule in schedules if activity_by_schedule[schedule]), None)
        if first_active is None:
            continue
        no_start_activity = any(
            ((baseline[schedule] ^ no_start_baseline[schedule]) >> slot) & 1
            for schedule in schedules
        )
        best_column, best_overlap = None, -1
        for name, column in COLUMNS.items():
            overlap = len(set(support_by_schedule[first_active]) & column)
            if overlap > best_overlap:
                best_column, best_overlap = name, overlap
        support_size = len(support_by_schedule[first_active])
        exact_support = best_overlap == 4 and support_size == 4
        score = (2 if all(repeat_ok.values()) else 0)
        score += 2 if no_start_activity else 0
        score += 3 if first_active == 1 else (1 if first_active == 2 else 0)
        score += best_overlap + (2 if exact_support else 0)
        candidates.append({
            "scan_out_index": slot,
            "first_active_capture_schedule": first_active,
            "active_schedules": [s for s in schedules if activity_by_schedule[s]],
            "reaction_plaintext_byte_support": support_by_schedule[first_active],
            "nearest_mc_column": best_column,
            "column_overlap": best_overlap,
            "exact_four_byte_support": exact_support,
            "start_activity_vs_no_start": no_start_activity,
            "repeat_stable": all(repeat_ok.values()),
            "score": score,
        })
    candidates.sort(key=lambda item: (-item["score"], item["scan_out_index"]))
    aes_dependent = [item for item in candidates if item["start_activity_vs_no_start"]]
    pre_round = [item for item in aes_dependent if item["first_active_capture_schedule"] == 1]
    mc_candidates = [item for item in pre_round if item["column_overlap"] >= 3]
    selected = next(
        (item for item in candidates if item["exact_four_byte_support"] and item["first_active_capture_schedule"] == 1 and item["start_activity_vs_no_start"]),
        None,
    )
    if selected is None:
        selected = candidates[0] if candidates else None
    return {
        "attack_input": str(capture),
        "evaluator_target_column_consumed": False,
        "total_scan_ff": 256,
        "query_count": 65,
        "capture_schedules": schedules,
        "aes_dependent_candidate_count": len(aes_dependent),
        "pre_round_candidate_count": len(pre_round),
        "mc_aware_candidate_count_overlap_ge_3": len(mc_candidates),
        "repeat_stability_by_schedule": repeat_ok,
        "top_10_scan_slots": candidates[:10],
        "final_selected_slot": selected,
        "ground_truth_evaluator_check": "separate evaluator artifact; not used by discovery",
    }

