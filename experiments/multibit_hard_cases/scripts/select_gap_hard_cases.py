import csv
import itertools
import random
from collections import defaultdict
from pathlib import Path


def cand_key(*cands):
    return tuple(sorted(cands))


def load_candidates(base_dir):
    path = base_dir / "results" / "candidate_map_extended512.csv"
    rows = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            rows[row["candidate_id"]] = row
    return rows


def load_existing_higher_order(root_dir):
    existing = {3: set(), 4: set()}
    src = root_dir / "multibit_baselines" / "configs"
    for k, name in [(3, "selected_3bit_hard_cases.csv"), (4, "selected_4bit_hard_cases.csv")]:
        path = src / name
        if not path.exists():
            continue
        with open(path) as f:
            for row in csv.DictReader(f):
                cands = [row["cand_a"], row["cand_b"], row.get("cand_c", ""), row.get("cand_d", "")]
                existing[k].add(cand_key(*[c for c in cands if c]))
    return existing


def add_unique_pair_from_summary(unique_pairs, path):
    if not path.exists():
        return
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                unique_count = int(row["unique_count"])
                seeds_total = int(row["seeds_total"])
            except (KeyError, ValueError):
                continue
            if seeds_total and unique_count / seeds_total >= 0.8:
                unique_pairs.add(cand_key(row["stage_a"] + "_" + row["bit_a"], row["stage_b"] + "_" + row["bit_b"]))


def load_pair_evidence(base_dir, root_dir):
    unique_pairs = set()
    gap_nonunique_pairs = defaultdict(list)
    gap_all_pairs = set()

    add_unique_pair_from_summary(unique_pairs, base_dir / "results" / "prior_2bit_results_imported.csv")
    add_unique_pair_from_summary(unique_pairs, root_dir / "multibit_baselines" / "results" / "two_bit_risk_map.csv")

    raw_path = base_dir / "results" / "raw_solver_runs_2bit_gap_confirmed.csv"
    grouped = defaultdict(lambda: {"unique": 0, "total": 0, "rows": []})
    with open(raw_path) as f:
        for row in csv.DictReader(f):
            pair = cand_key(row["cand_a"], row["cand_b"])
            grouped[pair]["total"] += 1
            grouped[pair]["rows"].append(row)
            gap_all_pairs.add(pair)
            if row["classification"] == "full_key_unique":
                grouped[pair]["unique"] += 1

    for pair, summary in grouped.items():
        if summary["total"] and summary["unique"] / summary["total"] >= 0.8:
            unique_pairs.add(pair)
        else:
            exemplar = summary["rows"][0]
            gap_nonunique_pairs[exemplar["expected_risk_class"]].append((pair, exemplar))

    return unique_pairs, gap_nonunique_pairs, gap_all_pairs


def has_unique_subset(combo, unique_pairs):
    return any(cand_key(*p) in unique_pairs for p in itertools.combinations(combo, 2))


def row_for_combo(prefix, combo, topology_class, reason):
    padded = list(combo) + [""] * (4 - len(combo))
    return {
        "case_id": f"{len(combo)}bit_{prefix}__" + "__".join(combo),
        "cand_a": padded[0],
        "cand_b": padded[1],
        "cand_c": padded[2],
        "cand_d": padded[3],
        "topology_class": topology_class,
        "selection_reason": reason,
    }


def select_with_anchor(anchor_pairs, candidate_pool, k, budget, rng, unique_pairs, existing, seen, prefix, topology_class, reason):
    selected = []
    shuffled = list(anchor_pairs)
    rng.shuffle(shuffled)

    for pair, _row in shuffled:
        if len(selected) >= budget:
            break
        base = list(pair)
        for _ in range(2000):
            extras = [c for c in rng.sample(candidate_pool, k - 2) if c not in base]
            if len(extras) != k - 2:
                continue
            combo = cand_key(*(base + extras))
            if combo in seen or combo in existing:
                continue
            if has_unique_subset(combo, unique_pairs):
                continue
            seen.add(combo)
            selected.append(row_for_combo(prefix, combo, topology_class, reason))
            break
    return selected


def main():
    base_dir = Path(__file__).resolve().parent.parent
    root_dir = base_dir.parent
    candidates = load_candidates(base_dir)
    unique_pairs, gap_nonunique_pairs, _gap_all_pairs = load_pair_evidence(base_dir, root_dir)
    existing = load_existing_higher_order(root_dir)

    early_pool = [c for c, r in candidates.items() if r["stage"] in {"SB", "SR"}]
    late_pool = [c for c, r in candidates.items() if r["stage"] in {"MC", "ARK"}]
    mixed_pool = list(candidates)
    col0_late_pool = [c for c, r in candidates.items() if r["stage"] in {"MC", "ARK"} and r["column"] == "0"]

    early_anchors = gap_nonunique_pairs.get("early_only", [])
    weak_late_anchors = gap_nonunique_pairs.get("weak_same_column", [])
    if not weak_late_anchors:
        weak_late_anchors = [x for cls, vals in gap_nonunique_pairs.items() if cls == "late_only" for x in vals]
    mixed_anchors = gap_nonunique_pairs.get("early_late_mixed", [])

    selected_3 = []
    seen_3 = set()
    rng = random.Random(7103)
    selected_3 += select_with_anchor(early_anchors, early_pool, 3, 60, rng, unique_pairs, existing[3], seen_3, "gap_early", "early_only", "gap_early_only_hard_case")
    selected_3 += select_with_anchor(weak_late_anchors, col0_late_pool or late_pool, 3, 40, rng, unique_pairs, existing[3], seen_3, "gap_weak_late", "weak_same_column", "gap_weak_same_column_hard_case")
    selected_3 += select_with_anchor(mixed_anchors, mixed_pool, 3, 60, rng, unique_pairs, existing[3], seen_3, "gap_mixed", "early_late_mixed", "gap_early_late_mixed_hard_case")

    selected_4 = []
    seen_4 = set()
    rng = random.Random(7104)
    selected_4 += select_with_anchor(early_anchors, early_pool, 4, 30, rng, unique_pairs, existing[4], seen_4, "gap_early", "early_only", "gap_early_only_hard_case")
    selected_4 += select_with_anchor(weak_late_anchors, col0_late_pool or late_pool, 4, 15, rng, unique_pairs, existing[4], seen_4, "gap_weak_late", "weak_same_column", "gap_weak_same_column_hard_case")
    selected_4 += select_with_anchor(mixed_anchors, mixed_pool, 4, 30, rng, unique_pairs, existing[4], seen_4, "gap_mixed", "early_late_mixed", "gap_early_late_mixed_hard_case")

    headers = ["case_id", "cand_a", "cand_b", "cand_c", "cand_d", "topology_class", "selection_reason"]
    out3 = base_dir / "configs" / "selected_3bit_gap_hard_cases.csv"
    out4 = base_dir / "configs" / "selected_4bit_gap_hard_cases.csv"
    for path, rows in [(out3, selected_3), (out4, selected_4)]:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Unique 2-bit subsets excluded: {len(unique_pairs)}")
    print(f"Non-unique gap anchors: early={len(early_anchors)}, weak_late={len(weak_late_anchors)}, mixed={len(mixed_anchors)}")
    print(f"Generated {len(selected_3)} 3-bit gap hard cases -> {out3}")
    print(f"Generated {len(selected_4)} 4-bit gap hard cases -> {out4}")


if __name__ == "__main__":
    main()
