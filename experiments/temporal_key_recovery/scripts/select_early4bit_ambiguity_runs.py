"""Select only early-only 4bit topologies that were ambiguous for every seed."""
from __future__ import annotations

import argparse
import collections

from experiment_common import ROOT, read_csv, write_csv


SOURCE = ROOT.parent / "multibit_baselines/results/raw_solver_runs_4bit.csv"
FIELDS = ("source_phase", "tap_count", "source_case_id", "seed", "query_count", "depth", "mode", "cand_a", "cand_b", "cand_c", "cand_d")


def _early_only(row: dict[str, str]) -> bool:
    return all(row[name].startswith(("SB_", "SR_")) for name in ("cand_a", "cand_b", "cand_c", "cand_d"))


def select() -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = collections.defaultdict(list)
    for row in read_csv(SOURCE):
        if _early_only(row):
            groups[tuple(row[name] for name in ("cand_a", "cand_b", "cand_c", "cand_d"))].append(row)
    selected = []
    for taps, runs in groups.items():
        if len(runs) != 3 or not all((row["first_result"], row["second_result"]) == ("sat", "sat") for row in runs):
            continue
        for row in runs:
            selected.append({
                "source_phase": "7", "tap_count": 4, "source_case_id": row["case_id"],
                "seed": int(row["seed"]), "query_count": int(row["query_count"]),
                "depth": int(row["depth"]), "mode": row["mode"],
                **{name: row[name] for name in ("cand_a", "cand_b", "cand_c", "cand_d")},
            })
    return sorted(selected, key=lambda row: (-int(row["query_count"]), row["source_case_id"], int(row["seed"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="configs/early4bit_all_ambiguity_runs.csv")
    args = parser.parse_args()
    rows = select()
    write_csv(ROOT / args.output, rows, FIELDS)
    print(f"wrote {len(rows)} all-ambiguous early-only 4bit runs -> {ROOT / args.output}")


if __name__ == "__main__":
    main()
