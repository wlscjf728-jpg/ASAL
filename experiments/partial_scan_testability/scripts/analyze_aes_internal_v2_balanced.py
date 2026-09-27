#!/usr/bin/env python3
"""Analyze the equal-weight four-stage-cone follow-up campaign."""

from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
ANALYSIS = ROOT / "results/analysis"
REPORTS = ROOT / "reports"
STAGES = ["IARK", "SB", "SR", "MC"]
CASES = [f"CASE_{stage}" for stage in STAGES]
CASES += [f"CASE_RANDOM_STAGE_seed{i:02d}" for i in range(1, 11)]
CASES += [f"CASE_MIX_MC_{count:03d}" for count in (0, 32, 64, 96, 128)]
CASES += ["CASE_AUTO_STAGE"]
SUMMARY_PATTERNS = {
    "detected": (r"Detected\s+\S+\s+(\d+)", int),
    "possibly_detected": (r"Possibly detected\s+\S+\s+(\d+)", int),
    "undetectable": (r"Undetectable\s+\S+\s+(\d+)", int),
    "atpg_untestable": (r"ATPG untestable\s+\S+\s+(\d+)", int),
    "not_detected": (r"Not detected\s+\S+\s+(\d+)", int),
    "total_faults": (r"total faults\s+(\d+)", int),
    "coverage_pct": (r"test coverage\s+([\d.]+)%", float),
    "patterns": (r"#internal patterns\s+(\d+)", int),
}


def placement(case: str) -> str:
    if case.startswith("CASE_RANDOM_STAGE"):
        return "RANDOM_STAGE"
    if case.startswith("CASE_MIX_MC_"):
        return "MIX_MC"
    if case == "CASE_AUTO_STAGE":
        return "AUTO_STAGE"
    return case.removeprefix("CASE_")


def parse_summary(path: Path) -> dict[str, object]:
    text = path.read_text(errors="replace")
    row: dict[str, object] = {}
    for key, (pattern, converter) in SUMMARY_PATTERNS.items():
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise ValueError(f"missing {key}")
        row[key] = converter(match.group(1))
    row["class_sum"] = sum(int(row[key]) for key in ("detected", "possibly_detected", "undetectable", "atpg_untestable", "not_detected"))
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CONFIG / "aes_internal_v2_balanced4_fault_manifest.json").read_text())
    all_modes: dict[str, list[dict[str, object]]] = {}
    for mode in ("stuck", "transition"):
        rows: list[dict[str, object]] = []
        for case in CASES:
            path = ROOT / "results/tmax/aes_internal_v2/balanced4" / mode / case / "summary.rpt"
            row: dict[str, object] = {"case": case, "placement": placement(case), "mode": mode, "status": "UNRESOLVED"}
            if not path.exists():
                row["error"] = "missing summary"
            else:
                try:
                    row.update(parse_summary(path))
                    row["status"] = "PASS" if row["class_sum"] == row["total_faults"] else "INVALID"
                except (OSError, ValueError) as exc:
                    row["error"] = str(exc)
            rows.append(row)
        all_modes[mode] = rows
        write_csv(ANALYSIS / f"aes_internal_v2_balanced4_{mode}_summary.csv", rows)

    def summary(mode: str, case: str) -> dict[str, object]:
        return next(row for row in all_modes[mode] if row["case"] == case)

    lines = [
        "# AES-Internal Balanced-Fault Follow-up",
        "",
        "This campaign keeps the existing v2 DFT netlists and scan placements unchanged. It replaces the naturally skewed AES-internal fault weighting with a deterministic balanced universe containing 1,000 fault entries from each of IARK, SB, SR, and MC backward cones.",
        "",
        "## What changed",
        "",
        "- Changed: fault source weighting only.",
        "- Unchanged: functional checkpoint, 896 common scan FFs, 128 variable scan FFs, 1,024 total scan FFs, one chain, SPF, ATPG options, and case list.",
        "- Direct AES FF Q/QN faults remain excluded by the source construction.",
        "- AES control and AES-other regions are intentionally not part of the primary balanced universe because AES control has only eight raw entries; their natural-distribution results remain in the v2 report.",
        f"- Selected entries per mode: {manifest['modes']['stuck']['total_selected_entries']} ({manifest['per_region_entries']} per major stage cone).",
        "",
        "## Stuck-at summary",
        "",
        "| Case | Placement | Total | Detected | AU | UD | ND | Coverage | Patterns | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in all_modes["stuck"]:
        if row["status"] != "PASS":
            lines.append(f"| {row['case']} | {row['placement']} | - | - | - | - | - | - | - | {row['status']} |")
        else:
            lines.append(f"| {row['case']} | {row['placement']} | {row['total_faults']} | {row['detected']} | {row['atpg_untestable']} | {row['undetectable']} | {row['not_detected']} | {row['coverage_pct']:.2f}% | {row['patterns']} | {row['status']} |")

    for mode in ("stuck", "transition"):
        valid = [row for row in all_modes[mode] if row["status"] == "PASS"]
        random_rows = [row for row in valid if str(row["case"]).startswith("CASE_RANDOM_STAGE_")]
        mc_rows = [row for row in valid if row["case"] == "CASE_MC"]
        if random_rows and mc_rows:
            values = [float(row["coverage_pct"]) for row in random_rows]
            mc_cov = float(mc_rows[0]["coverage_pct"])
            lines += ["", f"## {mode.capitalize()} balanced comparison", "", f"- MC coverage: {mc_cov:.3f}%.", f"- Random-stage mean: {statistics.mean(values):.3f}%; range: {min(values):.3f}% to {max(values):.3f}%.", f"- MC minus random-stage mean: {mc_cov - statistics.mean(values):+.3f} percentage points."]
    lines += ["", "## Interpretation", "", "This is a weighting-sensitivity experiment, not a replacement for the natural whole-design fault distribution. A change here answers whether the aggregate MC conclusion was being dominated by the large SB cone. It does not imply that the physical AES netlist contains an equal number of faults in each region.", "", "The MC-cone-local result and the balanced four-cone aggregate must be reported separately: MC can improve observability for MC_CONE while losing upstream IARK/SR observability when only the MC boundary is scanned.", "", "## Artifacts", "", "- `config/aes_internal_v2_balanced4_stuck.list`", "- `config/aes_internal_v2_balanced4_transition.list`", "- `config/aes_internal_v2_balanced4_fault_manifest.json`", "- `results/analysis/aes_internal_v2_balanced4_stuck_summary.csv`", "- `results/analysis/aes_internal_v2_balanced4_transition_summary.csv`", "- `results/tmax/aes_internal_v2/balanced4/`"]
    (REPORTS / "AES_INTERNAL_BALANCED_FAULT_REPORT.md").write_text("\n".join(lines) + "\n")
    validity = {"selected_entries_per_mode": manifest["modes"]["stuck"]["total_selected_entries"], "stuck_complete": all(row["status"] == "PASS" for row in all_modes["stuck"]), "transition_complete": all(row["status"] == "PASS" for row in all_modes["transition"]), "direct_ff_excluded": True, "scan_netlists_reused": True}
    (ANALYSIS / "aes_internal_v2_balanced4_validity.json").write_text(json.dumps(validity, indent=2) + "\n")
    print(json.dumps(validity, indent=2))


if __name__ == "__main__":
    main()
