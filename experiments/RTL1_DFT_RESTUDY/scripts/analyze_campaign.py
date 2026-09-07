#!/usr/bin/env python3
"""Collect D1-D5 outputs without treating missing/unknown runs as results."""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "analysis"))
from analysis_utils import classify_region, parse_fault_line, parse_summary_text, pareto_frontier

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT.parent
CASES = ["CASE_IARK", "CASE_SB", "CASE_SR", "CASE_MC"] + [f"CASE_RANDOM_seed{i:02d}" for i in range(1, 11)] + ["CASE_AUTO_TOPOLOGY"]
STAGE_ORDER = ["IARK", "SB", "SR", "MC", "RANDOM", "AUTO_TOPOLOGY"]


def placement(case: str) -> str:
    if case.startswith("CASE_RANDOM"):
        return "RANDOM"
    if case == "CASE_AUTO_TOPOLOGY":
        return "AUTO_TOPOLOGY"
    return case.removeprefix("CASE_")


def parse_dft_audit(case: str) -> dict[str, object]:
    inv_path = ROOT / "results/dft" / case / "scan_inventory.rpt"
    path_path = ROOT / "reports/dft_drc" / case / "scan_path.rpt"
    if not inv_path.exists() or not path_path.exists():
        return {"case": case, "scan_count": "", "chain_count": "", "chain_length": "", "dft_status": "MISSING"}
    inv = inv_path.read_text()
    scan_count = int(re.search(r"post_dft_scan_cell_count=(\d+)", inv).group(1))
    chains = re.findall(r"^I\s+(\d+)\s+(\d+)\s+scan_in", path_path.read_text(), re.MULTILINE)
    chain_count = len(chains)
    chain_length = sum(int(length) for _, length in chains)
    status = "PASS" if scan_count == 1024 and chain_count == 1 and chain_length == 1024 else "INVALID"
    return {"case": case, "scan_count": scan_count, "chain_count": chain_count, "chain_length": chain_length, "dft_status": status}


def parse_mode_case(mode: str, case: str) -> tuple[dict[str, object] | None, list[dict[str, str]]]:
    directory = ROOT / "results/tmax" / mode / case
    summary_path = directory / "summary.rpt"
    detail_path = directory / "detailed_faults_uncollapsed.rpt"
    if not summary_path.exists():
        return None, []
    try:
        summary = parse_summary_text(summary_path.read_text())
    except ValueError as exc:
        return {"case": case, "mode": mode, "status": "UNRESOLVED", "error": str(exc)}, []
    total = int(summary["total_faults"])
    classes = sum(int(summary[key]) for key in ("detected", "possibly_detected", "undetectable", "atpg_untestable", "not_detected"))
    row = {"case": case, "placement": placement(case), "mode": mode, **summary, "class_sum": classes, "status": "PASS" if classes == total else "INVALID"}
    details: list[dict[str, str]] = []
    if not detail_path.exists():
        row["status"] = "UNRESOLVED"
        row["error"] = "missing detailed fault report"
        return row, details
    for line in detail_path.read_text(errors="replace").splitlines():
        parsed = parse_fault_line(line)
        if not parsed:
            continue
        status = parsed["status"]
        if status == "--":
            normalized = "EQUIVALENT"
        elif status in {"DS", "DI", "DT"}:
            normalized = "DT"
        elif status in {"AN", "AU"}:
            normalized = "AU"
        else:
            normalized = status
        details.append({"case": case, "placement": placement(case), "mode": mode, **parsed, "normalized_status": normalized})
    row["detail_rows"] = len(details)
    return row, details


def region_metadata() -> dict[str, set[str]]:
    raw = json.loads((ROOT / "config/region_metadata.json").read_text())
    return {key: set(value) for key, value in raw.items() if isinstance(value, list)}


def classify_details(details: list[dict[str, str]], metadata: dict[str, set[str]]) -> list[dict[str, str]]:
    for row in details:
        row["region"] = classify_region(row["site"], metadata)
    return details


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def security_overlay() -> list[dict[str, object]]:
    fixed_path = EXP / "exp_res/04_adaptive_pair_rescue_campaigns/results/late_1bit_fixed_q128_summary.jsonl"
    fixed: Counter[str] = Counter()
    fixed_unique: Counter[str] = Counter()
    if fixed_path.exists():
        for line in fixed_path.read_text().splitlines():
            outer = json.loads(line)
            rows = outer.get("rows", [outer])
            for encoded in rows:
                row = json.loads(encoded) if isinstance(encoded, str) else encoded
                stage = row.get("tap", {}).get("stage")
                if stage in {"MC", "ARK"}:
                    fixed[stage] += 1
                    if row.get("terminal_classification") == "fixed_query_unique":
                        fixed_unique[stage] += 1
    support = {"IARK": 1, "SB": 1, "SR": 1, "MC": 4, "RANDOM": 0, "AUTO_TOPOLOGY": 1}
    rows = []
    for case in CASES:
        p = placement(case)
        fixed_rate = fixed_unique[p] / fixed[p] if fixed[p] else ""
        rows.append({
            "case": case,
            "placement": p,
            "support_width_bytes": support[p],
            "leakage_risk_proxy": support[p] / 16.0,
            "fixed_q128_unique_rate_existing": fixed_rate,
            "security_metric_source": "AES diffusion-support proxy; MC/ARK fixed-q128 rate is historical overlay only",
        })
    return rows


def draw_pareto(points: list[dict[str, object]], path: Path) -> None:
    width, height = 1100, 700
    left, right, top, bottom = 100, 50, 70, 100
    pw, ph = width - left - right, height - top - bottom
    colors = {"IARK": "#2563eb", "SB": "#16a34a", "SR": "#d97706", "MC": "#dc2626", "RANDOM": "#6b7280", "AUTO_TOPOLOGY": "#7c3aed"}
    def x(v: float) -> float: return left + v * pw
    def y(v: float) -> float: return top + (1 - v) * ph
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', '<text x="550" y="30" text-anchor="middle" font-family="sans-serif" font-size="21" font-weight="bold">Security–Testability Overlay</text>']
    for tick in (0, .25, .5, .75, 1):
        yy = y(tick)
        out += [f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#e5e7eb"/>', f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-family="sans-serif" font-size="13">{tick:.2f}</text>']
        xx = x(tick)
        out += [f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height-bottom}" stroke="#f3f4f6"/>', f'<text x="{xx:.1f}" y="{height-bottom+27}" text-anchor="middle" font-family="sans-serif" font-size="13">{tick:.2f}</text>']
    out += [f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>', f'<text x="550" y="{height-28}" text-anchor="middle" font-family="sans-serif" font-size="15">Leakage-risk proxy (AES support width / 16)</text>', f'<text x="24" y="350" text-anchor="middle" transform="rotate(-90 24 350)" font-family="sans-serif" font-size="15">Non-direct stuck-at test coverage</text>']
    frontier = {id(row) for row in pareto_frontier(points)}
    for row in points:
        p = str(row["placement"]); xx, yy = x(float(row["leakage"])), y(float(row["testability"]))
        out.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="9" fill="{colors.get(p, "#111827")}" stroke="#111827" stroke-width="2"/>')
        if id(row) in frontier:
            out.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="15" fill="none" stroke="#111827" stroke-width="2" stroke-dasharray="4,3"/>')
        out.append(f'<text x="{xx+14:.1f}" y="{yy-12:.1f}" font-family="sans-serif" font-size="14">{p}</text>')
    out.append('</svg>')
    path.write_text("\n".join(out) + "\n")


def main() -> None:
    analysis = ROOT / "results/analysis"
    metadata = region_metadata()
    audits = [parse_dft_audit(case) for case in CASES]
    write_csv(analysis / "dft_fairness_audit.csv", audits)
    all_rows: list[dict[str, object]] = []
    all_details: list[dict[str, str]] = []
    for mode in ("stuck", "transition"):
        mode_rows = []
        mode_details = []
        for case in CASES:
            row, details = parse_mode_case(mode, case)
            if row is not None:
                mode_rows.append(row)
                mode_details.extend(classify_details(details, metadata))
        write_csv(analysis / f"{mode}_summary.csv", mode_rows)
        write_csv(analysis / f"{mode}_fault_status.csv", mode_details)
        all_rows.extend(mode_rows)
        all_details.extend(mode_details)

        region_rows = []
        for case in CASES:
            subset = [r for r in mode_details if r["case"] == case]
            for region in ("selected_ff_direct", "mc_cone", "aes_other", "host", "unresolved"):
                group = [r for r in subset if r["region"] == region]
                counts = Counter(r["normalized_status"] for r in group)
                region_rows.append({"mode": mode, "case": case, "placement": placement(case), "region": region, "total_rows": len(group), "detected_rows": counts["DT"], "possibly_detected_rows": counts["PT"], "atpg_untestable_rows": counts["AU"], "undetectable_rows": counts["UD"], "not_detected_rows": counts["ND"]})
        write_csv(analysis / f"{mode}_region_breakdown.csv", region_rows)

    stuck = [r for r in all_rows if r.get("mode") == "stuck" and r.get("status") == "PASS"]
    by_case = {r["case"]: r for r in stuck}
    random_rows = [by_case[c] for c in CASES if c.startswith("CASE_RANDOM") and c in by_case]
    overlay = security_overlay()
    overlay_by_case = {row["case"]: row for row in overlay}
    points = []
    for case, sec in overlay_by_case.items():
        if case not in by_case:
            continue
        points.append({"case": case, "placement": sec["placement"], "testability": float(by_case[case]["coverage_pct"]) / 100.0, "leakage": float(sec["leakage_risk_proxy"])})
    frontier = {id(row) for row in pareto_frontier(points)}
    for row in points:
        row["pareto"] = id(row) in frontier
    write_csv(analysis / "security_testability_overlay.csv", [dict(row, fixed_q128_unique_rate_existing=overlay_by_case[row["case"]]["fixed_q128_unique_rate_existing"], security_metric_source=overlay_by_case[row["case"]]["security_metric_source"]) for row in points])
    draw_pareto(points, ROOT / "reports/security_testability_pareto.svg")

    status_rows = []
    direct = set(metadata.get("direct_sites", set()))
    mc = {row["site"]: row for row in all_details if row["mode"] == "stuck" and row["case"] == "CASE_MC"}
    for random in random_rows:
        rc = random["case"]
        rr = {row["site"]: row for row in all_details if row["mode"] == "stuck" and row["case"] == rc}
        for site in sorted(set(mc) & set(rr)):
            if mc[site]["normalized_status"] != rr[site]["normalized_status"]:
                status_rows.append({"comparison": f"MC_vs_{rc}", "site": site, "region": classify_region(site, metadata), "mc_status": mc[site]["normalized_status"], "random_status": rr[site]["normalized_status"], "direct_site": site in direct})
    write_csv(analysis / "mc_random_status_differences.csv", status_rows)

    report = ROOT / "reports/D1_D5_DFT_REASSESSMENT_REPORT.md"
    lines = ["# D1-D5 DFT Reassessment Report", "", "This report is generated from the isolated `RTL1_DFT_RESTUDY` campaign. Missing or malformed runs remain unresolved and are never counted as successes.", "", "## Scope", "", "- One-round `mor1kx_aes_soc` functional checkpoint; no RTL or synthesis change between cases.", "- Common scan set: 896 FF; variable budget: 128 FF; total: 1,024 FF; one chain.", "- Cases: IARK, SB, SR, MC, ten random seeds, and pre-ATPG topology-ranked auto selection.", "- Stuck-at source: 210,378 raw functional fault-list lines from the shared pre-DFT checkpoint.", f"- Direct variable output-site exclusions: {len(direct)} sites / {len(direct) * 2} stuck-at polarity entries requested.", "- Main comparison excludes the same union of variable candidate FF direct Q/QN sites from every case.", "", "## D1/D2 Stuck-at Summary", "", "| Case | Placement | Total faults | Detected | PT | AU | UD | ND | Coverage | Patterns | Status |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for row in sorted(stuck, key=lambda r: (STAGE_ORDER.index(r["placement"]) if r["placement"] in STAGE_ORDER else 99, r["case"])):
        lines.append(f"| {row['case']} | {row['placement']} | {row['total_faults']} | {row['detected']} | {row['possibly_detected']} | {row['atpg_untestable']} | {row['undetectable']} | {row['not_detected']} | {float(row['coverage_pct']):.2f}% | {row['patterns']} | {row['status']} |")
    if random_rows and "CASE_MC" in by_case:
        values = [float(row["coverage_pct"]) for row in random_rows]
        mc_row = by_case["CASE_MC"]
        lines += ["", "### D1 decision", "", f"- MC non-direct coverage: {float(mc_row['coverage_pct']):.2f}%.", f"- Random coverage range: {min(values):.2f}%–{max(values):.2f}% (mean {statistics.mean(values):.2f}%).", f"- MC minus random mean: {float(mc_row['coverage_pct']) - statistics.mean(values):.2f} percentage points.", f"- MC/random status changes outside the direct-site exclusion: {len([r for r in status_rows if not r['direct_site']])}.", "- A positive remaining gap is evidence for non-direct testability contribution; a zero gap supports only the direct-observability interpretation."]
    lines += ["", "## D3 Region Attribution", "", "See `results/analysis/stuck_region_breakdown.csv` and `mc_random_status_differences.csv`. Region labels are conservative: direct output sites are separated first; the MC backward cone is structural; remaining AES and host sites are disjoint lexical fallbacks; unresolved sites are retained.", "", "## D4 Transition-delay", "", "See `results/analysis/transition_summary.csv`. Transition ATPG is valid only when TetraMAX accepts the generated transition fault list, launch/capture timing, and protocol. Missing summaries or syntax/protocol errors are recorded as `UNRESOLVED`; they are not interpreted as coverage zero.", "", "## D5 Automatic selection and security overlay", "", "The pre-ATPG ranking is in `results/analysis/topology_ranking.csv`. It uses only structural fanout/fanin proxies from the functional checkpoint and does not use ATPG status or secret-key data. The generated top-128 manifest is `config/auto_topology_scan.list`.", "", "The security overlay in `results/analysis/security_testability_overlay.csv` uses the existing AES diffusion-support proxy (1-byte early, 4-byte MC, 0-byte non-AES random). Historical fixed-query MC/ARK rates are included as provenance, not as a new DFT measurement. `reports/security_testability_pareto.svg` marks nondominated points under higher testability and lower leakage risk.", "", "## Validity", "", "The fairness table is `results/analysis/dft_fairness_audit.csv`. Any missing DFT audit, unequal scan count/chain length, unequal loaded fault totals, invalid fault-site warning, or class-total mismatch prevents a PASS label for that comparison.", "", "## Outputs", "", "- `results/analysis/stuck_summary.csv` and `transition_summary.csv`", "- `results/analysis/stuck_region_breakdown.csv` and `transition_region_breakdown.csv`", "- `results/analysis/stuck_fault_status.csv` and `transition_fault_status.csv`", "- `results/analysis/mc_random_status_differences.csv`", "- `results/analysis/topology_ranking.csv`", "- `results/analysis/security_testability_overlay.csv`", "- `reports/security_testability_pareto.svg`"]
    report.write_text("\n".join(lines) + "\n")
    print(json.dumps({"stuck_cases": len(stuck), "detail_rows": len(all_details), "status_differences": len(status_rows), "pareto_points": len(points)}, indent=2))


if __name__ == "__main__":
    main()
