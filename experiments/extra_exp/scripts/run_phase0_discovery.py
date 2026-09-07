"""Keyless Phase 0 MC leakage-channel discovery.

The attack path consumes only plaintext labels, capture schedules, and anonymous
256-bit scan vectors. Evaluator-only target columns in the four-field simulator
output are parsed and discarded. No key, scan map, or RTL name is used.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

COLUMNS = {
    "C0": {0, 5, 10, 15},
    "C1": {4, 9, 14, 3},
    "C2": {8, 13, 2, 7},
    "C3": {12, 1, 6, 11},
}

def parse(path: Path):
    rows = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 4:
            q, schedule, _evaluator_target, vector = fields
        elif len(fields) == 3:
            q, schedule, vector = fields
        else:
            raise ValueError(f"unexpected capture row: {line}")
        rows[(int(q), int(schedule))] = int(vector, 16)
    return rows

def query_groups(qids):
    groups = {}
    for byte_index in range(16):
        members = [1 + 4 * byte_index + d for d in range(4)]
        if all(q in qids for q in members):
            groups[byte_index] = members
    return groups

def bits(v):
    return [(v >> i) & 1 for i in range(256)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--repeat", required=True, type=Path)
    ap.add_argument("--no-start", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--attack-out", required=True, type=Path)
    args = ap.parse_args()
    full = parse(args.capture)
    repeat = parse(args.repeat)
    no_start = parse(args.no_start)
    qids = sorted({q for q, _ in full})
    schedules = sorted({s for _, s in full})
    if qids != list(range(65)) or schedules != [1, 2, 3]:
        raise ValueError(f"expected qids 0..64 and schedules 1..3, got {qids[:3]}..{qids[-3:]} / {schedules}")
    if sorted({q for q, _ in repeat}) != [0] or sorted({q for q, _ in no_start}) != [0]:
        raise ValueError("control captures must contain qid 0")
    groups = query_groups(qids)
    baseline = {s: full[(0, s)] for s in schedules}
    repeat_ok = {s: repeat[(0, s)] == repeat[(0, s)] for s in schedules}
    # The supplied repeat manifest has two identical q0 rows per schedule; parser
    # intentionally keeps the last row, so stability is checked from the two raw rows.
    repeat_rows = {}
    for line in args.repeat.read_text().splitlines():
        q, s, *rest = line.split()
        repeat_rows.setdefault(int(s), []).append(int(rest[-1], 16))
    repeat_ok = {s: len(set(repeat_rows.get(s, []))) == 1 for s in schedules}
    no_start_baseline = {s: no_start[(0, s)] for s in schedules}
    candidates = []
    for slot in range(256):
        activity_by_schedule = {}
        support_by_schedule = {}
        for s in schedules:
            activity_by_schedule[s] = any(((full[(q, s)] ^ baseline[s]) >> slot) & 1 for q in qids[1:])
            support = set()
            for byte_index, members in groups.items():
                if any(((full[(q, s)] ^ baseline[s]) >> slot) & 1 for q in members):
                    support.add(byte_index)
            support_by_schedule[s] = sorted(support)
        first_active = next((s for s in schedules if activity_by_schedule[s]), None)
        if first_active is None:
            continue
        no_start_activity = any(((baseline[s] ^ no_start_baseline[s]) >> slot) & 1 for s in schedules)
        best_column, best_overlap = None, -1
        for name, column in COLUMNS.items():
            overlap = len(set(support_by_schedule[first_active]) & column)
            if overlap > best_overlap:
                best_column, best_overlap = name, overlap
        support_size = len(support_by_schedule[first_active])
        exact_support = best_overlap == 4 and support_size == 4
        score = 0
        score += 2 if all(repeat_ok.values()) else 0
        score += 2 if no_start_activity else 0
        score += 3 if first_active == 1 else (1 if first_active == 2 else 0)
        score += best_overlap
        score += 2 if exact_support else 0
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
    candidates.sort(key=lambda c: (-c["score"], c["scan_out_index"]))
    aes_dependent = [c for c in candidates if c["start_activity_vs_no_start"]]
    pre_round = [c for c in aes_dependent if c["first_active_capture_schedule"] == 1]
    mc_candidates = [c for c in pre_round if c["column_overlap"] >= 3]
    selected = next((c for c in candidates if c["exact_four_byte_support"] and c["first_active_capture_schedule"] == 1 and c["start_activity_vs_no_start"]), None)
    if selected is None:
        selected = candidates[0] if candidates else None
    attack_lines = []
    for line in args.capture.read_text().splitlines():
        fields = line.split()
        attack_lines.append(" ".join(fields[:2] + [fields[-1]]))
    args.attack_out.write_text("\n".join(attack_lines) + "\n")
    result = {
        "attack_input": str(args.attack_out),
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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
