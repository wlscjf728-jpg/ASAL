"""Normalize proof-grade Phase 7/7_1 early-only ambiguity rows."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from experiment_common import ROOT, read_csv, write_csv


SOURCES = (
    ("7", 2, ROOT.parent / "anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_2bit.csv"),
    ("7", 3, ROOT.parent / "anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_3bit.csv"),
    ("7_1", 2, ROOT.parent / "anonymous_subround_multiround_attack_7_1_oracle/results/raw_solver_runs_2bit_gap_confirmed.csv"),
    ("7_1", 3, ROOT.parent / "anonymous_subround_multiround_attack_7_1_oracle/results/raw_solver_runs_3bit_gap_confirmed.csv"),
)
FIELDS = ("source_phase", "tap_count", "source_case_id", "seed", "query_count", "depth", "mode", "cand_a", "cand_b", "cand_c", "cand_d")


def early_only(row: dict[str, str]) -> bool:
    taps = [row.get(name, "") for name in ("cand_a", "cand_b", "cand_c", "cand_d")]
    taps = [tap for tap in taps if tap]
    return bool(taps) and all(tap.startswith(("SB_", "SR_")) for tap in taps)


def select() -> list[dict[str, object]]:
    selected = []
    for phase, bits, path in SOURCES:
        for row in read_csv(path):
            if not early_only(row) or (row.get("first_result"), row.get("second_result")) != ("sat", "sat"):
                continue
            selected.append({
                "source_phase": phase,
                "tap_count": bits,
                "source_case_id": row.get("case_id") or row.get("pair_id"),
                "seed": int(row["seed"]),
                "query_count": int(row["query_count"]),
                "depth": int(row["depth"]),
                "mode": row["mode"],
                "cand_a": row.get("cand_a", ""),
                "cand_b": row.get("cand_b", ""),
                "cand_c": row.get("cand_c", ""),
                "cand_d": row.get("cand_d", ""),
            })
    return sorted(selected, key=lambda row: (-int(row["query_count"]), int(row["tap_count"]), row["source_phase"], row["source_case_id"], int(row["seed"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="configs/early_only_2_3bit_ambiguity_runs.csv")
    args = parser.parse_args()
    rows = select()
    write_csv(ROOT / args.output, rows, FIELDS)
    print(f"wrote {len(rows)} early-only proof ambiguity tasks -> {ROOT / args.output}")


if __name__ == "__main__":
    main()
