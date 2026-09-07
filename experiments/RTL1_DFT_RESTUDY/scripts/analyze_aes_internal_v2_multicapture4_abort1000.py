#!/usr/bin/env python3
"""Summarize four-cycle abort=1000 ATPG follow-up runs."""

from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results/analysis"
OUTPUT_ROOT = "multicapture4_abort1000"
CASES = ["CASE_IARK", "CASE_SB", "CASE_SR", "CASE_MC"]
CASES += [f"CASE_RANDOM_STAGE_seed{i:02d}" for i in range(1, 11)]
CASES += [f"CASE_MIX_MC_{i:03d}" for i in (0, 32, 64, 96, 128)]
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
    row["class_sum"] = sum(int(row[k]) for k in (
        "detected", "possibly_detected", "undetectable", "atpg_untestable", "not_detected"
    ))
    row["fast_sequential_patterns"] = len(re.findall(r"fast[_ -]?sequential", text, re.IGNORECASE))
    return row


def read_rows(mode: str) -> list[dict[str, object]]:
    rows = []
    for case in CASES:
        path = ROOT / "results/tmax/aes_internal_v2" / OUTPUT_ROOT / mode / case / "summary.rpt"
        row: dict[str, object] = {"case": case, "mode": mode, "status": "UNRESOLVED"}
        if path.exists():
            try:
                row.update(parse(path))
                row["status"] = "PASS" if row["class_sum"] == row["total_faults"] else "INVALID"
            except (OSError, ValueError) as exc:
                row["error"] = str(exc)
        else:
            row["error"] = "missing summary"
        rows.append(row)
    return rows


def fmt(row: dict[str, object]) -> str:
    if row["status"] != "PASS":
        return f"| {row['case']} | - | - | - | - | - | - | {row['status']} |"
    return f"| {row['case']} | {row['detected']} | {row['atpg_untestable']} | {row['undetectable']} | {row['not_detected']} | {row['total_faults']} | {float(row['coverage_pct']):.2f}% | {row['patterns']} | PASS |"


def write_csv(mode: str, rows: list[dict[str, object]]) -> None:
    path = ANALYSIS / f"aes_internal_v2_{OUTPUT_ROOT}_{mode}_summary.csv"
    keys = list(rows[0]) if rows else ["case"]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    all_rows = {mode: read_rows(mode) for mode in ("stuck", "transition")}
    for mode, rows in all_rows.items():
        write_csv(mode, rows)

    lines = [
        "# AES-Internal Four-Cycle ATPG Follow-up (abort=1000)",
        "",
        "This campaign uses the same pre-DFT checkpoint, DFT netlists, scan protocol, direct-FF exclusion, and AES-internal fault definition as the revision-2 study. The controlled variables are four-cycle Fast-Sequential capture and `set_atpg -abort 1000`. It includes single-boundary stage controls, ten random-stage controls, and the existing MC scan-mix netlists, all against the natural AES-internal source where available.",
        "",
        "## Requested comparisons",
        "",
        "1. `CASE_IARK`, `CASE_SB`, `CASE_SR`, and `CASE_MC` test the same single-boundary condition under four-cycle capture.",
        "2. The natural source contains 73,022 raw entries; the same AES FF Q/QN direct faults are deleted in every case, yielding the common valid natural universe reported by TetraMAX.",
        "3. `CASE_MIX_MC_000` through `CASE_MIX_MC_128` test increasing MC scan share under the same four-cycle protocol. These are scan-placement cases, not manually reweighted fault lists.",
        "",
    ]
    for mode, rows in all_rows.items():
        lines += [f"## {mode.capitalize()} results", "", "| Case | Detected | ATPG untestable | Undetectable | Not detected | Total | Coverage | Patterns | Status |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        lines += [fmt(row) for row in rows]
        valid = [row for row in rows if row["status"] == "PASS"]
        if valid:
            stage = [row for row in valid if row["case"] in {"CASE_IARK", "CASE_SB", "CASE_SR", "CASE_MC"}]
            random_rows = [row for row in valid if str(row["case"]).startswith("CASE_RANDOM_STAGE_")]
            mixes = [row for row in valid if str(row["case"]).startswith("CASE_MIX_MC_")]
            if stage:
                lines += ["", "### Single-boundary stage comparison", "", "| Case | Coverage | Detected | AU | Fast-sequential marker count |", "|---|---:|---:|---:|---:|"]
                for row in stage:
                    lines.append(f"| {row['case']} | {float(row['coverage_pct']):.3f}% | {row['detected']} | {row['atpg_untestable']} | {row['fast_sequential_patterns']} |")
            if random_rows:
                cov = [float(row["coverage_pct"]) for row in random_rows]
                det = [int(row["detected"]) for row in random_rows]
                lines += ["", "### Random-stage distribution", "", f"- Mean: {statistics.mean(det):.1f}/{random_rows[0]['total_faults']} detected, {statistics.mean(cov):.3f}%.", f"- Range: {min(cov):.3f}% to {max(cov):.3f}%."]
            if mixes:
                lines += ["", "### MC scan-mix sweep", "", "| MC variable FF count | Case | Coverage | Detected | AU |", "|---:|---|---:|---:|---:|"]
                for row in sorted(mixes, key=lambda item: str(item["case"])):
                    count = str(row["case"]).rsplit("_", 1)[1]
                    lines.append(f"| {int(count)} | {row['case']} | {float(row['coverage_pct']):.3f}% | {row['detected']} | {row['atpg_untestable']} |")
        if mode == "transition":
            lines += ["", "**Transition caveat:** transition runs are included for completeness. If TetraMAX emits no Fast-Sequential patterns for this model, they are not evidence that transition faults propagated across four active capture cycles; the stuck-at results are the primary four-cycle test."]
        lines.append("")
    lines += [
        "## Interpretation discipline",
        "",
        "The prior balanced four-cycle result is retained as a diagnostic sensitivity baseline. A global MC advantage is only supported if it survives the single-boundary comparison and the natural-fault MC-mix analysis after the abort limit is raised. A negative MC-versus-random result is not discarded; it indicates that distributed observation boundaries or ATPG search accessibility dominate that configuration.",
        "",
        "## Artifacts",
        "",
        "- `scripts/tmax/run_aes_internal_v2_multicapture_abort_case.tcl`",
        "- `scripts/run_aes_internal_v2_multicapture4_abort1000.sh`",
        "- `results/analysis/aes_internal_v2_multicapture4_abort1000_stuck_summary.csv`",
        "- `results/analysis/aes_internal_v2_multicapture4_abort1000_transition_summary.csv`",
        "- `results/tmax/aes_internal_v2/multicapture4_abort1000/`",
    ]
    report = ROOT / "reports/AES_INTERNAL_MULTICAPTURE4_ABORT1000_REPORT.md"
    report.write_text("\n".join(lines) + "\n")
    validity = {mode: all(row["status"] == "PASS" for row in rows) for mode, rows in all_rows.items()}
    (ANALYSIS / "aes_internal_v2_multicapture4_abort1000_validity.json").write_text(json.dumps(validity, indent=2) + "\n")
    print(json.dumps(validity, indent=2))


if __name__ == "__main__":
    main()
