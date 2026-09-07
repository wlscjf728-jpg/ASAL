#!/usr/bin/env python3
"""Summarize the legacy 422-fault companion runs separately from D1-D5."""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
from analysis_utils import parse_summary_text  # noqa: E402

CASES = ["CASE_IARK", "CASE_SB", "CASE_SR", "CASE_MC"] + [f"CASE_RANDOM_seed{i:02d}" for i in range(1, 11)] + ["CASE_AUTO_TOPOLOGY"]


def placement(case: str) -> str:
    if case.startswith("CASE_RANDOM"):
        return "RANDOM"
    if case == "CASE_AUTO_TOPOLOGY":
        return "AUTO_TOPOLOGY"
    return case.removeprefix("CASE_")


def main() -> None:
    analysis = ROOT / "results/analysis"
    rows: list[dict[str, object]] = []
    for tag, policy in (("collapsed422_included", "direct_included"), ("collapsed422_direct_excluded", "direct_excluded")):
        for case in CASES:
            path = ROOT / "results/tmax" / tag / case / "summary.rpt"
            summary = parse_summary_text(path.read_text())
            classes = sum(int(summary[key]) for key in ("detected", "possibly_detected", "undetectable", "atpg_untestable", "not_detected"))
            rows.append({"tag": tag, "policy": policy, "case": case, "placement": placement(case), **summary, "class_sum": classes, "status": "PASS" if classes == int(summary["total_faults"]) else "INVALID"})
    analysis.mkdir(parents=True, exist_ok=True)
    with (analysis / "collapsed422_comparison.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Collapsed-422 High-Coverage Companion Report",
        "",
        "This is a supplementary comparison using the historical 422-entry collapsed stuck-at list. It is intentionally separate from the raw uncollapsed D1-D5 universe.",
        "",
        "## Conditions",
        "",
        "- The same 15 post-DFT cases and the same current 1,024-FF/one-chain checkpoint were used.",
        "- `direct_included` reads all 422 entries.",
        "- `direct_excluded` deletes the common 2,622-entry direct Q/QN list; only 256 entries overlap this 422-entry list, leaving 166 faults.",
        "- Coverage is TetraMAX detected faults divided by the reported total fault count.",
        "",
        "## Results",
        "",
        "| Policy | Placement | Total | Detected | AU | ND | Coverage | Patterns | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['policy']} | {row['placement']} | {row['total_faults']} | {row['detected']} | {row['atpg_untestable']} | {row['not_detected']} | {float(row['coverage_pct']):.2f}% | {row['patterns']} | {row['status']} |")

    for policy in ("direct_included", "direct_excluded"):
        subset = [r for r in rows if r["policy"] == policy]
        mc = next(r for r in subset if r["placement"] == "MC")
        randoms = [r for r in subset if r["placement"] == "RANDOM"]
        vals = [float(r["coverage_pct"]) for r in randoms]
        lines += [
            "",
            f"### {policy}",
            "",
            f"- MC: {mc['detected']}/{mc['total_faults']} ({float(mc['coverage_pct']):.2f}%).",
            f"- Random range: {min(vals):.2f}%–{max(vals):.2f}% (mean {statistics.mean(vals):.2f}%).",
            f"- MC minus random mean: {float(mc['coverage_pct']) - statistics.mean(vals):.2f} percentage points.",
        ]

    lines += [
        "",
        "## Interpretation",
        "",
        "The direct-included run reproduces the historical 82.70% versus 22.04% contrast. However, after removing the direct output faults that account for the MC-only detections, all placements converge to 93/166 (56.02%) in this legacy list. Therefore the historical 422-list result is not evidence of a residual MC-specific gain. The raw D1-D5 result remains the complementary evidence because it uses a much larger common uncollapsed universe and observes a residual MC advantage after direct-fault exclusion.",
        "",
        "This companion must not be presented as a replacement for D1. It is a denominator/attribution control that explains why the legacy 22% versus 83% plot is visually strong but dominated by direct selected-output faults.",
    ]
    (ROOT / "reports/COLLAPSED422_HIGH_COVERAGE_REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"rows={len(rows)}")
    for policy in ("direct_included", "direct_excluded"):
        subset = [r for r in rows if r["policy"] == policy]
        mc = next(r for r in subset if r["placement"] == "MC")
        randoms = [r for r in subset if r["placement"] == "RANDOM"]
        print(policy, "mc", mc["detected"], mc["total_faults"], mc["coverage_pct"], "random_mean", round(statistics.mean(float(r["coverage_pct"]) for r in randoms), 2))


if __name__ == "__main__":
    main()
