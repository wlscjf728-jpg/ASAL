#!/usr/bin/env python3
"""Summarize the four-cycle balanced MC-versus-random ATPG campaign."""

from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results/analysis"
REPORT = ROOT / "reports/AES_INTERNAL_BALANCED_MULTICAPTURE4_REPORT.md"
CASES = ["CASE_MC"] + [f"CASE_RANDOM_STAGE_seed{i:02d}" for i in range(1, 11)]
FIELDS = {
    "detected": (r"Detected\s+\S+\s+(\d+)", int),
    "possibly_detected": (r"Possibly detected\s+\S+\s+(\d+)", int),
    "undetectable": (r"Undetectable\s+\S+\s+(\d+)", int),
    "atpg_untestable": (r"ATPG untestable\s+\S+\s+(\d+)", int),
    "not_detected": (r"Not detected\s+\S+\s+(\d+)", int),
    "total_faults": (r"total faults\s+(\d+)", int),
    "coverage_pct": (r"test coverage\s+([\d.]+)%", float),
    "patterns": (r"#internal patterns\s+(\d+)", int),
}


def parse(path: Path) -> dict[str, object]:
    text = path.read_text(errors="replace")
    row: dict[str, object] = {}
    for key, (pattern, conv) in FIELDS.items():
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise ValueError(f"missing {key}")
        row[key] = conv(match.group(1))
    row["class_sum"] = sum(int(row[k]) for k in ("detected", "possibly_detected", "undetectable", "atpg_untestable", "not_detected"))
    return row


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    all_modes: dict[str, list[dict[str, object]]] = {}
    for mode in ("stuck", "transition"):
        rows = []
        for case in CASES:
            path = ROOT / "results/tmax/aes_internal_v2/balanced_multicapture4" / mode / case / "summary.rpt"
            row: dict[str, object] = {"case": case, "placement": "MC" if case == "CASE_MC" else "RANDOM_STAGE", "mode": mode, "status": "UNRESOLVED"}
            if path.exists():
                try:
                    row.update(parse(path))
                    row["status"] = "PASS" if row["class_sum"] == row["total_faults"] else "INVALID"
                except (OSError, ValueError) as exc:
                    row["error"] = str(exc)
            else:
                row["error"] = "missing summary"
            rows.append(row)
        all_modes[mode] = rows
        with (ANALYSIS / f"aes_internal_v2_balanced_multicapture4_{mode}_summary.csv").open("w", newline="") as fh:
            fields = list(rows[0]) if rows else ["case"]
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    lines = [
        "# AES-Internal Balanced Four-Cycle Capture Follow-up",
        "",
        "This campaign reuses the revision-2 DFT netlists and the 4,000-entry balanced AES-internal fault universe. The only ATPG change is `set_atpg -capture_cycles 4`; the original `balanced4/` basic-scan results are retained as a protocol baseline.",
        "",
        "## Purpose",
        "",
        "The one-round pipeline requires up to four clock edges for an IARK-side fault to reach MC_REG. This follow-up tests whether the prior MC-versus-random result was caused by a single-capture observation window.",
        "",
    ]
    for mode in ("stuck", "transition"):
        rows = all_modes[mode]
        valid = [r for r in rows if r["status"] == "PASS"]
        mc = next((r for r in valid if r["case"] == "CASE_MC"), None)
        random_rows = [r for r in valid if r["case"] != "CASE_MC"]
        lines += [f"## {mode.capitalize()} results", "", "| Case | Detected | AU | UD | ND | Total | Coverage | Patterns | Status |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for row in rows:
            if row["status"] != "PASS":
                lines.append(f"| {row['case']} | - | - | - | - | - | - | - | {row['status']} |")
            else:
                lines.append(f"| {row['case']} | {row['detected']} | {row['atpg_untestable']} | {row['undetectable']} | {row['not_detected']} | {row['total_faults']} | {row['coverage_pct']:.2f}% | {row['patterns']} | PASS |")
        if mc and random_rows:
            rc = [float(r["coverage_pct"]) for r in random_rows]
            rd = [int(r["detected"]) for r in random_rows]
            lines += ["", "### MC versus random", "", f"- MC: {mc['detected']}/{mc['total_faults']} detected, {float(mc['coverage_pct']):.3f}%.", f"- Random mean: {statistics.mean(rd):.1f}/{random_rows[0]['total_faults']} detected, {statistics.mean(rc):.3f}%; range {min(rc):.3f}% to {max(rc):.3f}%.", f"- MC minus random mean: {float(mc['coverage_pct']) - statistics.mean(rc):+.3f} percentage points.", "- This result is the protocol-corrected comparison; the earlier basic-scan result remains a sensitivity baseline and is not overwritten.", ""]
            if mode == "transition":
                lines += ["- TetraMAX generated no `fast_sequential` patterns for the transition mode; this mode is retained as a reference run, not as evidence of four-cycle transition propagation.", ""]
    lines += ["## Interpretation rule", "", "A positive MC-minus-random result under four-cycle capture supports an MC advantage that is not explained solely by a one-cycle observation cutoff. A non-positive result means the earlier MC-cone-local gain does not generalize to the balanced upstream-inclusive fault universe, even when the capture window is extended.", "", "## Artifacts", "", "- `scripts/tmax/run_aes_internal_v2_balanced_multicapture_case.tcl`", "- `scripts/run_aes_internal_v2_balanced_multicapture4.sh`", "- `results/analysis/aes_internal_v2_balanced_multicapture4_stuck_summary.csv`", "- `results/analysis/aes_internal_v2_balanced_multicapture4_transition_summary.csv`", "- `results/tmax/aes_internal_v2/balanced_multicapture4/`"]
    REPORT.write_text("\n".join(lines) + "\n")
    validity = {mode: all(row["status"] == "PASS" for row in rows) for mode, rows in all_modes.items()}
    (ANALYSIS / "aes_internal_v2_balanced_multicapture4_validity.json").write_text(json.dumps(validity, indent=2) + "\n")
    print(json.dumps(validity, indent=2))


if __name__ == "__main__":
    main()
