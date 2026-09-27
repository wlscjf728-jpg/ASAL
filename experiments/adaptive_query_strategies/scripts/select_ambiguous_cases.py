"""Select proof-grade ambiguous Phase 7/7_1 cases for Attack 8 validation."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from experiment_common import PHASE7, PHASE7_1, ROOT, canonical_case_id, proof_class, read_csv, write_csv

SOURCES = {
    ("7", 2): (PHASE7 / "configs" / "selected_2bit_cases_round1.csv", PHASE7 / "results" / "raw_solver_runs_2bit.csv"),
    ("7", 3): (PHASE7 / "configs" / "selected_3bit_hard_cases.csv", PHASE7 / "results" / "raw_solver_runs_3bit.csv"),
    ("7", 4): (PHASE7 / "configs" / "selected_4bit_hard_cases.csv", PHASE7 / "results" / "raw_solver_runs_4bit.csv"),
    ("7_1", 2): (PHASE7_1 / "configs" / "selected_2bit_gap_parallel.csv", PHASE7_1 / "results" / "raw_solver_runs_2bit_gap_confirmed.csv"),
    ("7_1", 3): (PHASE7_1 / "configs" / "selected_3bit_gap_hard_cases.csv", PHASE7_1 / "results" / "raw_solver_runs_3bit_gap_confirmed.csv"),
    ("7_1", 4): (PHASE7_1 / "configs" / "selected_4bit_gap_hard_cases.csv", PHASE7_1 / "results" / "raw_solver_runs_4bit_gap_confirmed.csv"),
}

FIELDS = [
    "attack8_case_id", "source_phase", "source_case_id", "tap_count",
    "cand_a", "cand_b", "cand_c", "cand_d", "stage_pair",
    "topology_class", "expected_risk_class", "source_selection_reason",
    "proof_ambiguity_runs", "proof_unique_runs", "unresolved_runs",
    "source_min_query", "source_max_query", "attack8_selection_reason",
]


def summarize_results(path: Path) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, object]] = defaultdict(
        lambda: {"ambiguity": 0, "unique": 0, "unresolved": 0, "queries": []}
    )
    for row in read_csv(path):
        case_id = canonical_case_id(row)
        classification = proof_class(row)
        grouped[case_id][classification] += 1
        try:
            grouped[case_id]["queries"].append(int(row["query_count"]))
        except (KeyError, TypeError, ValueError):
            pass
    return grouped


def normalized_case(row: dict[str, str], phase: str, bits: int, summary: dict[str, object]) -> dict[str, object]:
    source_case_id = canonical_case_id(row)
    queries = summary["queries"]
    return {
        "attack8_case_id": f"p{phase}_{bits}b_{source_case_id}",
        "source_phase": phase,
        "source_case_id": source_case_id,
        "tap_count": bits,
        "cand_a": row.get("cand_a", ""),
        "cand_b": row.get("cand_b", ""),
        "cand_c": row.get("cand_c", ""),
        "cand_d": row.get("cand_d", ""),
        "stage_pair": row.get("stage_pair", ""),
        "topology_class": row.get("topology_class", row.get("expected_risk_class", "")),
        "expected_risk_class": row.get("expected_risk_class", row.get("topology_class", "")),
        "source_selection_reason": row.get("selection_reason", ""),
        "proof_ambiguity_runs": summary["ambiguity"],
        "proof_unique_runs": summary["unique"],
        "unresolved_runs": summary["unresolved"],
        "source_min_query": min(queries) if queries else "",
        "source_max_query": max(queries) if queries else "",
        "attack8_selection_reason": "all_directly_resolved_runs_ambiguous",
    }


def select(bits: int) -> list[dict[str, object]]:
    selected = []
    seen_tap_sets = set()
    for phase in ("7", "7_1"):
        config_path, results_path = SOURCES[(phase, bits)]
        summaries = summarize_results(results_path)
        for case in read_csv(config_path):
            case_id = canonical_case_id(case)
            summary = summaries.get(case_id)
            if not summary or summary["ambiguity"] == 0 or summary["unique"] != 0:
                continue
            tap_key = tuple(sorted(
                case.get(name, "") for name in ("cand_a", "cand_b", "cand_c", "cand_d") if case.get(name)
            ))
            if tap_key in seen_tap_sets:
                continue
            seen_tap_sets.add(tap_key)
            selected.append(normalized_case(case, phase, bits, summary))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bits", type=int, choices=(2, 3, 4), nargs="+", default=(2, 3, 4))
    parser.add_argument("--output-dir", default="configs")
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir
    total = 0
    for bits in args.bits:
        rows = select(bits)
        path = output_dir / f"selected_{bits}bit_proven_ambiguous.csv"
        write_csv(path, rows, FIELDS)
        total += len(rows)
        print(f"{bits}-bit: selected {len(rows)} proof-grade all-ambiguity cases -> {path}")
    print(f"total selected cases: {total}")


if __name__ == "__main__":
    main()
