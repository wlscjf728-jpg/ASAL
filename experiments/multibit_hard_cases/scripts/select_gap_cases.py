import csv
import random
from collections import defaultdict
from pathlib import Path


SOURCE_7_DIR = Path(__file__).resolve().parents[2] / "multibit_baselines"

STAGE_BUDGETS = {
    "SB-MC": 28,
    "SR-MC": 28,
    "SB-ARK": 24,
    "SR-ARK": 24,
    "MC-ARK": 24,
    "MC-MC": 22,
    "ARK-ARK": 22,
    "SB-SR": 10,
    "SB-SB": 8,
    "SR-SR": 8,
}

RISK_WEIGHTS = {
    "early_late_mixed": 4,
    "weak_same_column": 4,
    "redundant_late": 4,
    "late_only": 3,
    "early_only": 1,
}


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def candidate_index(base_dir):
    out = {}
    for row in read_csv(base_dir / "results" / "candidate_map_extended512.csv"):
        out[row["candidate_id"]] = {
            "stage": row["stage"],
            "bit_index": int(row["bit_index"]),
            "byte_index": int(row["byte_index"]),
            "row": int(row["row"]),
            "column": int(row["column"]),
            "bit_in_byte": int(row["bit_in_byte"]),
            "class": row["class"],
        }
    return out


def existing_pair_ids(base_dir):
    ids = set()
    selected = SOURCE_7_DIR / "configs" / "selected_2bit_cases_round1.csv"
    if selected.exists():
        for row in read_csv(selected):
            ids.add(row["pair_id"])

    # Exclude all prior imported exact anchors so this run spends time on new positions.
    prior = base_dir / "results" / "prior_2bit_results_imported.csv"
    if prior.exists():
        for row in read_csv(prior):
            c1 = f"{row['stage_a']}_{row['bit_a']}"
            c2 = f"{row['stage_b']}_{row['bit_b']}"
            ids.add("__".join(sorted([c1, c2], key=stage_sort_key)))
    return ids


def stage_sort_key(candidate_id):
    stage, bit = candidate_id.split("_", 1)
    return ({"SB": 0, "SR": 1, "MC": 2, "ARK": 3}[stage], int(bit))


def distance_bucket(value):
    value = abs(value)
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3plus"


def cyclic_column_distance(a, b):
    raw = abs(a - b)
    return min(raw, 4 - raw)


def structural_cell(row, cands):
    a = cands[row["cand_a"]]
    b = cands[row["cand_b"]]
    byte_gap = abs(a["byte_index"] - b["byte_index"])
    bit_gap = abs(a["bit_in_byte"] - b["bit_in_byte"])
    row_gap = abs(a["row"] - b["row"])
    col_gap = cyclic_column_distance(a["column"], b["column"])
    return (
        row["stage_pair"],
        row["expected_risk_class"],
        row["same_byte"],
        row["same_row"],
        row["same_column"],
        row["same_bit_in_byte"],
        row["same_byte_farbit"],
        row["same_col_samebit"],
        row["same_col_diagbit"],
        row["distinct_row"],
        row["distinct_diag"],
        row["scatter"],
        row["potentially_redundant"],
        distance_bucket(byte_gap),
        distance_bucket(bit_gap),
        distance_bucket(row_gap),
        distance_bucket(col_gap),
    )


def covered_cells(base_dir, cands):
    cells = set()
    selected = SOURCE_7_DIR / "configs" / "selected_2bit_cases_round1.csv"
    for path in [selected]:
        if path.exists():
            for row in read_csv(path):
                cells.add(structural_cell(row, cands))
    return cells


def row_score(row, cell_is_new):
    score = 10 if cell_is_new else 0
    score += RISK_WEIGHTS.get(row["expected_risk_class"], 1)
    if row["stage_pair"] in {"SB-MC", "SR-MC", "SB-ARK", "SR-ARK"}:
        score += 3
    if row["stage_pair"] in {"MC-ARK", "ARK-ARK"}:
        score += 2
    if row["expected_risk_class"] in {"weak_same_column", "redundant_late"}:
        score += 3
    return score


def select_rows(base_dir):
    rng = random.Random(7101)
    cands = candidate_index(base_dir)
    excluded_ids = existing_pair_ids(base_dir)
    seen_cells = covered_cells(base_dir, cands)

    pair_rows = read_csv(base_dir / "results" / "pair_structural_map_extended512.csv")
    groups = defaultdict(list)
    for row in pair_rows:
        if row["pair_id"] in excluded_ids:
            continue
        if row["stage_pair"] not in STAGE_BUDGETS:
            continue
        cell = structural_cell(row, cands)
        enriched = dict(row)
        enriched["_cell"] = cell
        enriched["_score"] = row_score(row, cell not in seen_cells)
        groups[row["stage_pair"]].append(enriched)

    selected = []
    selected_ids = set()
    selected_cells = set()

    for stage_pair, budget in STAGE_BUDGETS.items():
        rows = groups[stage_pair]
        rng.shuffle(rows)
        rows.sort(key=lambda r: r["_score"], reverse=True)

        by_cell = defaultdict(list)
        for row in rows:
            by_cell[row["_cell"]].append(row)

        # First pass: one representative per highest-value uncovered cell.
        cell_order = list(by_cell)
        rng.shuffle(cell_order)
        cell_order.sort(
            key=lambda cell: max(r["_score"] for r in by_cell[cell]),
            reverse=True,
        )
        for cell in cell_order:
            if len([r for r in selected if r["stage_pair"] == stage_pair]) >= budget:
                break
            if cell in selected_cells:
                continue
            row = by_cell[cell][0]
            if row["pair_id"] in selected_ids:
                continue
            row["selection_reason"] = "gap_uncovered_structural_cell"
            selected.append(row)
            selected_ids.add(row["pair_id"])
            selected_cells.add(cell)

        # Second pass: fill remaining budget with high-risk boundary diversity.
        for row in rows:
            if len([r for r in selected if r["stage_pair"] == stage_pair]) >= budget:
                break
            if row["pair_id"] in selected_ids:
                continue
            row["selection_reason"] = (
                "gap_boundary_risk_sample"
                if row["expected_risk_class"] != "early_only"
                else "gap_early_control_sample"
            )
            selected.append(row)
            selected_ids.add(row["pair_id"])

    return selected


def write_selection(base_dir, rows):
    out = base_dir / "configs" / "selected_2bit_gap_parallel.csv"
    headers = [
        "pair_id", "cand_a", "cand_b", "stage_pair", "same_stage", "same_byte",
        "same_row", "same_column", "same_bit_in_byte", "same_byte_farbit",
        "same_col_samebit", "same_col_diagbit", "distinct_row", "distinct_diag",
        "scatter", "potentially_redundant", "expected_risk_class",
        "selection_reason",
    ]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in rows:
            w.writerow({h: row[h] for h in headers})
    return out


def main():
    base_dir = Path(__file__).resolve().parent.parent
    rows = select_rows(base_dir)
    out = write_selection(base_dir, rows)
    print(f"selected {len(rows)} gap cases -> {out}")


if __name__ == "__main__":
    main()
