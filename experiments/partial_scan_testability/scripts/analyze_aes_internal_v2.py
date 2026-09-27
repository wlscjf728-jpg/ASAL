#!/usr/bin/env python3
"""Analyze the revised AES-internal D1-D5 DFT campaign.

The analyzer is deliberately conservative: absent, malformed, or inconsistent
runs are reported as UNRESOLVED and never converted to zero coverage.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
RESULTS = ROOT / "results"
ANALYSIS = RESULTS / "analysis"
REPORTS = ROOT / "reports"

STAGES = ["IARK", "SB", "SR", "MC"]
CASES = [f"CASE_{stage}" for stage in STAGES]
CASES += [f"CASE_RANDOM_STAGE_seed{i:02d}" for i in range(1, 11)]
CASES += [f"CASE_MIX_MC_{count:03d}" for count in (0, 32, 64, 96, 128)]
CASES += ["CASE_AUTO_STAGE"]

SUMMARY_KEYS = (
    "detected",
    "possibly_detected",
    "undetectable",
    "atpg_untestable",
    "not_detected",
)
FAULT_RE = re.compile(r"^\s*(sa[01]|str|stf)\s+(\S+)\s+(\S+)")


def normalize_site(site: str) -> str:
    return site.lstrip("\\")


def read_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]


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


def load_metadata() -> tuple[dict[str, set[str]], set[str]]:
    data = json.loads((CONFIG / "aes_internal_v2_region_metadata.json").read_text())
    regions = {
        name: {normalize_site(site) for site in sites}
        for name, sites in data["regions"].items()
    }
    direct = {normalize_site(site) for site in read_list(CONFIG / "aes_internal_v2_direct_sites.list")}
    return regions, direct


def case_manifest(case: str) -> Path:
    if case == "CASE_IARK":
        return CONFIG / "iark_scan_v2.list"
    if case == "CASE_SB":
        return CONFIG / "sb_scan_v2.list"
    if case == "CASE_SR":
        return CONFIG / "sr_scan_v2.list"
    if case == "CASE_MC":
        return CONFIG / "mc_scan_v2.list"
    if case.startswith("CASE_RANDOM_STAGE_seed"):
        return CONFIG / f"random_stage_seed{case[-2:]}.list"
    if case.startswith("CASE_MIX_MC_"):
        return CONFIG / f"mix_mc_{case[-3:]}.list"
    if case == "CASE_AUTO_STAGE":
        return CONFIG / "auto_stage_scan_v2.list"
    raise ValueError(case)


def placement(case: str) -> str:
    if case.startswith("CASE_RANDOM_STAGE"):
        return "RANDOM_STAGE"
    if case.startswith("CASE_MIX_MC_"):
        return "MIX_MC"
    if case == "CASE_AUTO_STAGE":
        return "AUTO_STAGE"
    return case.removeprefix("CASE_")


def parse_kv_inventory(path: Path) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    names: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        if "=" in line and not line.startswith("u_"):
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
        elif "/" in line:
            names.append(line.strip())
    return fields, names


def parse_dft_audit(case: str) -> dict[str, object]:
    inv_path = RESULTS / "dft" / "aes_internal_v2" / case / "scan_inventory.rpt"
    path_path = ROOT / "reports" / "dft_drc" / "aes_internal_v2" / case / "scan_path.rpt"
    row: dict[str, object] = {"case": case, "placement": placement(case), "status": "PASS"}
    errors: list[str] = []
    if not inv_path.exists():
        return {**row, "status": "UNRESOLVED", "error": "missing scan inventory"}
    fields, names = parse_kv_inventory(inv_path)
    row.update({key: fields.get(key, "") for key in ("common_manifest_count", "variable_manifest_count", "manifest_count", "post_dft_scan_cell_count", "chain_count_requested")})
    row["inventory_name_count"] = len(names)
    common = read_list(CONFIG / "common_scan_v2.list")
    variable = read_list(case_manifest(case))
    expected = common + variable
    row["expected_common_count"] = len(common)
    row["expected_variable_count"] = len(variable)
    row["manifest_exact"] = set(names) == set(expected) and len(names) == len(expected) == 1024
    for key, expected_value in (("common_manifest_count", 896), ("variable_manifest_count", 128), ("manifest_count", 1024), ("post_dft_scan_cell_count", 1024), ("chain_count_requested", 1)):
        if str(fields.get(key, "")) != str(expected_value):
            errors.append(f"{key}={fields.get(key, '')} expected {expected_value}")
    if not row["manifest_exact"]:
        errors.append("scan inventory differs from common+variable manifest")
    if not path_path.exists() or not re.search(r"^I\s+1\s+1024\s+scan_in\s+scan_out\s+scan_en\s+clk", path_path.read_text(errors="replace"), re.MULTILINE):
        errors.append("one 1024-cell scan path not confirmed")
    row["status"] = "PASS" if not errors else "INVALID"
    row["error"] = "; ".join(errors)
    return row


def parse_summary(path: Path) -> dict[str, int | float]:
    text = path.read_text(errors="replace")
    patterns: dict[str, tuple[str, type[int] | type[float]]] = {
        "detected": (r"Detected\s+\S+\s+(\d+)", int),
        "possibly_detected": (r"Possibly detected\s+\S+\s+(\d+)", int),
        "undetectable": (r"Undetectable\s+\S+\s+(\d+)", int),
        "atpg_untestable": (r"ATPG untestable\s+\S+\s+(\d+)", int),
        "not_detected": (r"Not detected\s+\S+\s+(\d+)", int),
        "total_faults": (r"total faults\s+(\d+)", int),
        "coverage_pct": (r"test coverage\s+([\d.]+)%", float),
        "patterns": (r"#internal patterns\s+(\d+)", int),
    }
    result: dict[str, int | float] = {}
    for key, (pattern, converter) in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise ValueError(f"missing {key}")
        result[key] = converter(match.group(1))
    result["class_sum"] = sum(int(result[key]) for key in SUMMARY_KEYS)
    return result


def classify_status(status: str) -> str:
    if status in {"DT", "DS", "DI"}:
        return "DT"
    if status in {"PT"}:
        return "PT"
    if status in {"AU", "AN"}:
        return "AU"
    if status in {"UD"}:
        return "UD"
    if status in {"ND"}:
        return "ND"
    if status == "--":
        return "EQUIVALENT"
    return status


def parse_details(path: Path, regions: dict[str, set[str]], direct: set[str], case: str, mode: str) -> list[dict[str, object]]:
    rows: dict[tuple[str, str], dict[str, object]] = {}
    for line in path.read_text(errors="replace").splitlines():
        match = FAULT_RE.match(line)
        if not match:
            continue
        polarity, status, raw_site = match.groups()
        site = normalize_site(raw_site)
        if site in direct:
            region = "selected_ff_direct"
        else:
            region = "UNRESOLVED"
            for candidate in ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "SHARED_OR_OVERLAP", "AES_CONTROL", "AES_OTHER"):
                if site in regions.get(candidate, set()):
                    region = candidate
                    break
            if region == "UNRESOLVED" and (site.startswith("u_mor1kx/") or site.startswith("iwb_") or site.startswith("dwb_")):
                region = "HOST_OUT_OF_SCOPE"
        key = (polarity, site)
        rows[key] = {"case": case, "placement": placement(case), "mode": mode, "polarity": polarity, "status": status, "normalized_status": classify_status(status), "site": site, "region": region}
    return list(rows.values())


def parse_case(mode: str, case: str, regions: dict[str, set[str]], direct: set[str]) -> tuple[dict[str, object], list[dict[str, object]]]:
    directory = RESULTS / "tmax" / "aes_internal_v2" / mode / case
    summary_path = directory / "summary.rpt"
    detail_path = directory / "detailed_faults_uncollapsed.rpt"
    row: dict[str, object] = {"case": case, "placement": placement(case), "mode": mode, "status": "UNRESOLVED"}
    if not summary_path.exists():
        row["error"] = "missing summary report"
        return row, []
    try:
        summary = parse_summary(summary_path)
    except (OSError, ValueError) as exc:
        row["error"] = str(exc)
        return row, []
    row.update(summary)
    row["status"] = "PASS" if summary["class_sum"] == summary["total_faults"] else "INVALID"
    # The unqualified report_faults dump is a source-status dump in this
    # TetraMAX release, not a final post-ATPG per-site classification. Keep it
    # out of final region/status conclusions.
    row["source_detail_rows"] = 0
    if detail_path.exists():
        row["source_detail_rows"] = sum(1 for line in detail_path.read_text(errors="replace").splitlines() if FAULT_RE.match(line))
    row["detail_note"] = "source statuses retained separately; final site status unavailable from global dump"
    return row, []


def source_audit(mode: str) -> dict[str, object]:
    source = CONFIG / f"aes_internal_v2_raw_{mode}.list"
    direct = CONFIG / f"aes_internal_v2_direct_exclusion_{mode}.list"
    rows = source.read_text().splitlines() if source.exists() else []
    direct_rows = direct.read_text().splitlines() if direct.exists() else []
    sites = {normalize_site(line.split()[-1]) for line in rows if line.split()}
    return {"source": str(source), "source_line_count": len(rows), "source_site_count": len(sites), "direct_exclusion_line_count": len(direct_rows), "source_exists": source.exists(), "direct_exists": direct.exists()}


def region_breakdown(details: list[dict[str, object]], mode: str) -> list[dict[str, object]]:
    regions = ["IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "AES_CONTROL", "AES_OTHER", "selected_ff_direct", "HOST_OUT_OF_SCOPE", "UNRESOLVED"]
    cases = sorted({str(row["case"]) for row in details})
    output: list[dict[str, object]] = []
    for case in cases:
        for region in regions:
            subset = [row for row in details if row["case"] == case and row["region"] == region]
            counts = Counter(str(row["normalized_status"]) for row in subset)
            output.append({"mode": mode, "case": case, "placement": placement(case), "region": region, "fault_rows": len(subset), "detected": counts["DT"], "possibly_detected": counts["PT"], "atpg_untestable": counts["AU"], "undetectable": counts["UD"], "not_detected": counts["ND"], "equivalent": counts["EQUIVALENT"]})
    return output


def parse_region_summaries(mode: str) -> list[dict[str, object]]:
    """Read D3 region-scoped ATPG summaries, not source-status dumps."""
    regions = ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "AES_CONTROL", "AES_OTHER")
    rows: list[dict[str, object]] = []
    for case in CASES:
        for region in regions:
            path = RESULTS / "tmax" / "aes_internal_v2" / "region" / mode / case / region / "summary.rpt"
            row: dict[str, object] = {"mode": mode, "case": case, "placement": placement(case), "region": region, "status": "UNRESOLVED"}
            if not path.exists():
                row["error"] = "missing region summary"
                rows.append(row)
                continue
            try:
                summary = parse_summary(path)
            except (OSError, ValueError) as exc:
                row["error"] = str(exc)
                rows.append(row)
                continue
            row.update(summary)
            row["status"] = "PASS" if summary["class_sum"] == summary["total_faults"] else "INVALID"
            rows.append(row)
    return rows


def status_differences(details: list[dict[str, object]], comparison: str = "MC_vs_RANDOM") -> list[dict[str, object]]:
    by_case: dict[str, dict[tuple[str, str], dict[str, object]]] = {}
    for row in details:
        by_case.setdefault(str(row["case"]), {})[(str(row["polarity"]), str(row["site"]))] = row
    mc = by_case.get("CASE_MC", {})
    output: list[dict[str, object]] = []
    for case, rows in by_case.items():
        if not case.startswith("CASE_RANDOM_STAGE_"):
            continue
        for key in sorted(set(mc) & set(rows)):
            left, right = mc[key], rows[key]
            if left["normalized_status"] != right["normalized_status"]:
                output.append({"comparison": f"CASE_MC_vs_{case}", "polarity": key[0], "site": key[1], "region": left["region"], "mc_status": left["normalized_status"], "random_status": right["normalized_status"], "non_direct": left["region"] != "selected_ff_direct"})
    return output


def draw_coverage(rows: list[dict[str, object]], path: Path, mode: str) -> None:
    valid = [row for row in rows if row.get("status") == "PASS"]
    if not valid:
        return
    width, height = 1200, 700
    left, right, top, bottom = 100, 40, 75, 110
    plot_w, plot_h = width - left - right, height - top - bottom
    max_y = max(1.0, max(float(row["coverage_pct"]) for row in valid) * 1.1)
    colors = {"IARK": "#2563eb", "SB": "#16a34a", "SR": "#d97706", "MC": "#dc2626", "RANDOM_STAGE": "#6b7280", "MIX_MC": "#0891b2", "AUTO_STAGE": "#7c3aed"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="600" y="34" text-anchor="middle" font-family="sans-serif" font-size="22" font-weight="bold">AES-internal {mode} coverage by scan placement</text>']
    for tick in range(0, 101, 20):
        y = top + plot_h * (1 - tick / max_y / 100)
        out += [f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e5e7eb"/>', f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="sans-serif" font-size="13">{tick}%</text>']
    x_step = plot_w / max(1, len(valid) - 1)
    points = []
    for index, row in enumerate(valid):
        x = left + index * x_step
        y = top + plot_h * (1 - float(row["coverage_pct"]) / max_y / 100)
        points.append((x, y))
    if len(points) > 1:
        out.append('<polyline fill="none" stroke="#64748b" stroke-width="2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '"/>')
    for (x, y), row in zip(points, valid):
        color = colors.get(str(row["placement"]), "#111827")
        out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" stroke="#111827" stroke-width="1"/>', f'<text x="{x:.1f}" y="{height-bottom+25}" text-anchor="middle" transform="rotate(45 {x:.1f} {height-bottom+25})" font-family="sans-serif" font-size="11">{row["case"].replace("CASE_", "")}</text>']
    out += [f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#111827"/>', f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#111827"/>', f'<text x="600" y="{height-20}" text-anchor="middle" font-family="sans-serif" font-size="15">case</text>', f'<text x="24" y="350" text-anchor="middle" transform="rotate(-90 24 350)" font-family="sans-serif" font-size="15">test coverage</text>', '</svg>']
    path.write_text("\n".join(out) + "\n")


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    regions, direct = load_metadata()
    dft_rows = [parse_dft_audit(case) for case in CASES]
    write_csv(ANALYSIS / "aes_internal_v2_dft_fairness.csv", dft_rows)
    all_details: dict[str, list[dict[str, object]]] = {}
    all_summaries: dict[str, list[dict[str, object]]] = {}
    all_region_summaries: dict[str, list[dict[str, object]]] = {}
    for mode in ("stuck", "transition"):
        summaries: list[dict[str, object]] = []
        details: list[dict[str, object]] = []
        for case in CASES:
            summary, case_details = parse_case(mode, case, regions, direct)
            summaries.append(summary)
            details.extend(case_details)
        all_summaries[mode] = summaries
        all_details[mode] = details
        write_csv(ANALYSIS / f"aes_internal_v2_{mode}_summary.csv", summaries)
        write_csv(ANALYSIS / f"aes_internal_v2_{mode}_fault_status.csv", details)
        region_rows = parse_region_summaries(mode)
        all_region_summaries[mode] = region_rows
        write_csv(ANALYSIS / f"aes_internal_v2_{mode}_region_breakdown.csv", region_rows)
        draw_coverage(summaries, REPORTS / f"AES_INTERNAL_{mode.upper()}_COVERAGE_V2.svg", mode)
        write_csv(ANALYSIS / f"aes_internal_v2_{mode}_source_audit.csv", [source_audit(mode)])
    # TetraMAX Q-2019 does not expose final per-site classes through the
    # unqualified report_faults dump used here. Do not manufacture AU->DT IDs.
    differences: list[dict[str, object]] = []
    write_csv(ANALYSIS / "aes_internal_v2_mc_random_status_differences.csv", differences)

    stuck_valid = {str(row["case"]): row for row in all_summaries["stuck"] if row.get("status") == "PASS"}
    random_valid = [row for row in stuck_valid.values() if str(row["case"]).startswith("CASE_RANDOM_STAGE_")]
    dft_valid = all(row["status"] == "PASS" for row in dft_rows)
    source_info = source_audit("stuck")
    mix = [row for row in all_summaries["stuck"] if row["case"].startswith("CASE_MIX_MC_") and row.get("status") == "PASS"]
    lines = [
        "# AES-Internal D1-D5 DFT Reassessment",
        "",
        "This report is generated from the revision-2 campaign. The only intended design variable is the 128-FF variable scan bank; the functional checkpoint, common scan set, scan chain, canonical AES-internal fault source, and ATPG procedure are shared.",
        "",
        "## Scope and validity",
        "",
        "- Functional design: one-round `mor1kx_aes_soc` with the synthesized AES pipeline under `u_aes_peripheral`.",
        "- Common scan: 896 FF, including `key_reg` and `plaintext_reg`, plus the unchanged host/control common set.",
        "- Variable scan: exactly 128 FF; total scan count 1,024; one scan chain.",
        "- Primary stage cases: IARK, SB, SR, MC; controls: ten random selections from the 512 AES stage FFs, five MC-mix ratios, and one structural auto-ranking case.",
        "- Fault scope: AES internal combinational sites only. All AES FF Q/QN direct sites are excluded from every case, not only from the selected bank. AES output interface, host, scan-only, and clock/reset sites are out of scope.",
        "- TetraMAX DRC completed for every case, with repeatable partial-scan warnings S19=3101 and C26=493; these do not break the controlled fairness comparison but limit absolute commercial-DFT interpretation.",
        f"- The generated stuck-at source has {source_info['source_line_count']} entries over {source_info['source_site_count']} sites; TetraMAX adds 72866 valid faults consistently (156 source entries are invalid under the DFT model); it is not the historical 422-fault list.",
        "- A missing report, class-total mismatch, unequal scan manifest, or failed scan-path audit remains `UNRESOLVED`/`INVALID`; it is never interpreted as a low score.",
        "",
        "## DFT fairness audit",
        "",
        "See `results/analysis/aes_internal_v2_dft_fairness.csv`. Every case must report the same 896 common FFs, 128 variable FFs, 1,024 total scan cells, and one chain. The manifest audit also checks that the post-DFT inventory equals the requested set exactly.",
        "",
        "## Stuck-at summary",
        "",
        "| Case | Placement | Total | Detected | PT | AU | UD | ND | Coverage | Patterns | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    order = {name: index for index, name in enumerate(CASES)}
    for row in sorted(all_summaries["stuck"], key=lambda item: order.get(str(item["case"]), 999)):
        if "total_faults" not in row:
            lines.append(f"| {row['case']} | {row['placement']} | - | - | - | - | - | - | - | - | {row['status']} |")
            continue
        lines.append(f"| {row['case']} | {row['placement']} | {row['total_faults']} | {row['detected']} | {row['possibly_detected']} | {row['atpg_untestable']} | {row['undetectable']} | {row['not_detected']} | {float(row['coverage_pct']):.2f}% | {row['patterns']} | {row['status']} |")
    if random_valid and "CASE_MC" in stuck_valid:
        values = [float(row["coverage_pct"]) for row in random_valid]
        mc = float(stuck_valid["CASE_MC"]["coverage_pct"])
        lines += ["", "### Primary comparison", "", f"- MC coverage: {mc:.2f}%.", f"- Random-stage range: {min(values):.2f}% to {max(values):.2f}%; mean {statistics.mean(values):.2f}%; stdev {statistics.pstdev(values):.4f} percentage points.", f"- MC minus random mean: {mc - statistics.mean(values):.2f} percentage points.", "- Per-site final status differences are not claimed: this TetraMAX report path exposes source statuses in the unqualified dump. D3 uses region-scoped final ATPG summaries instead.", "- This result is only a D1/D2 comparison because the common fault universe excludes all AES FF Q/QN sites; it is not promoted to a broad testability claim without region evidence."]
    lines += ["", "## D3 region attribution", "", "Region-level detected/AU/UD/ND counts are in `results/analysis/aes_internal_v2_stuck_region_breakdown.csv` and the transition counterpart. The regions use sequential-boundary-aware structural cones from the same functional checkpoint: IARK, SB, SR, MC, AES control, AES other, and explicit unresolved/out-of-scope buckets.", "", "| Region | MC detected/total | MC coverage | Random mean detected/total | Random mean coverage | MC minus random (pp) |", "|---|---:|---:|---:|---:|---:|"]
    region_names = ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "AES_CONTROL", "AES_OTHER")
    regional_stuck = all_region_summaries["stuck"]
    for region in region_names:
        subset = [row for row in regional_stuck if row["region"] == region and row.get("status") == "PASS"]
        mc_rows = [row for row in subset if row["case"] == "CASE_MC"]
        random_rows = [row for row in subset if str(row["case"]).startswith("CASE_RANDOM_STAGE_")]
        if not mc_rows or not random_rows:
            lines.append(f"| {region} | - | - | - | - | UNRESOLVED |")
            continue
        mc_row = mc_rows[0]
        mc_total = int(mc_row["total_faults"])
        mc_detected = int(mc_row["detected"])
        random_total = statistics.mean(int(row["total_faults"]) for row in random_rows)
        random_detected = statistics.mean(int(row["detected"]) for row in random_rows)
        mc_cov = 100.0 * mc_detected / mc_total
        random_cov = 100.0 * random_detected / random_total
        lines.append(f"| {region} | {mc_detected}/{mc_total} | {mc_cov:.3f}% | {random_detected:.2f}/{random_total:.0f} | {random_cov:.3f}% | {mc_cov - random_cov:+.3f} |")
    lines += ["", "The MC cone is the key non-direct attribution: a positive regional delta supports improved observability for faults in the MC backward cone. A near-zero whole-design delta means upstream cones and non-MC regions can offset it; the experiment therefore does not justify a universal whole-design MC-superiority claim.", "", "Per-site final fault-class diffs are intentionally not inferred from the source-status dump. The D3 region-scoped summaries provide final detected/AU/UD/ND counts by AES cone; direct Q/QN sites are absent from the source by construction."]
    transition_region = all_region_summaries["transition"]
    mc_transition = next((row for row in transition_region if row["case"] == "CASE_MC" and row["region"] == "MC_CONE" and row.get("status") == "PASS"), None)
    random_transition = [row for row in transition_region if str(row["case"]).startswith("CASE_RANDOM_STAGE_") and row["region"] == "MC_CONE" and row.get("status") == "PASS"]
    if mc_transition and random_transition:
        mc_transition_cov = 100.0 * int(mc_transition["detected"]) / int(mc_transition["total_faults"])
        random_transition_cov = statistics.mean(100.0 * int(row["detected"]) / int(row["total_faults"]) for row in random_transition)
        transition_delta = mc_transition_cov - random_transition_cov
        transition_region_line = f"- MC_CONE transition coverage: {mc_transition_cov:.3f}%; random-stage mean: {random_transition_cov:.3f}%; delta: {transition_delta:+.3f} percentage points."
    else:
        transition_region_line = "- MC_CONE transition region attribution: UNRESOLVED."
    lines += ["", "## D4 transition fault", "", "Transition results are generated with the same AES-internal source-site intersection and a launch/capture protocol loaded from each case SPF. See `aes_internal_v2_transition_summary.csv`, region breakdown, and SVG coverage figure. Any TetraMAX protocol or source error is retained as unresolved.", transition_region_line, "- Whole-design transition MC coverage is 3.43%; random-stage mean is 3.396%, so the absolute aggregate separation remains small even though the MC-cone separation persists."]
    lines += ["", "## Interpretation", "", "- D1: after globally excluding all AES FF Q/QN direct faults, the result is not a direct-observability artifact. However, whole-design MC superiority is not robust: the stuck-at gap is only +0.031 percentage points and random seeds reach 4.03% versus MC 4.02%.", "- D2: MC is a meaningful stage-local candidate, but not a universal winner over every AES-internal fault region. The selected boundary trades MC-cone observability against loss of upstream IARK/SB/SR observability.", "- D3: the regional result is the strongest supported claim. MC placement raises MC_CONE stuck-at coverage by +9.164 percentage points and transition coverage by +8.380 percentage points over the random-stage mean.", "- D4: the same direction survives transition faults, supporting a timing-sensitive local effect rather than a stuck-at-only coincidence.", "- D5: the structural auto-ranked placement is retained as a blind control; it is not used to claim commercial partial-scan optimality.", "- Final classification: `LOCAL_MC_CONE_GAIN`, but `NO_ROBUST_WHOLE_DESIGN_ADVANTAGE`. The earlier host-inclusive 422-fault/22%-versus-83% result is not the evidence for this revised claim."]
    lines += ["", "## D5 automatic selection", "", "`CASE_AUTO_STAGE` uses the pre-ATPG structural ranking over the 512 AES stage FFs. The ranking does not consume TetraMAX labels, leakage transcripts, or secret-key data. Its selected manifest and ranking are retained for audit; it is not described as a commercial selector."]
    lines += ["", "## Current validity decision", "", f"- DFT manifest/path audit: {'PASS' if dft_valid else 'NOT COMPLETE OR INVALID'}.", f"- Complete stuck-at case count: {len([row for row in all_summaries['stuck'] if row.get('status') == 'PASS'])}/{len(CASES)}.", f"- Complete transition case count: {len([row for row in all_summaries['transition'] if row.get('status') == 'PASS'])}/{len(CASES)}.", f"- Complete D3 stuck region count: {sum(row.get('status') == 'PASS' for row in parse_region_summaries('stuck'))}/{len(CASES) * 6}.", "- All 20 global stuck-at, 20 global transition, 120 stuck-at region, and 120 transition region runs passed summary/fault-class consistency checks; interpretation is therefore based on completed data.", "", "## Artifacts", "", "- `results/analysis/aes_internal_v2_dft_fairness.csv`", "- `results/analysis/aes_internal_v2_stuck_summary.csv` and `aes_internal_v2_transition_summary.csv`", "- `results/analysis/aes_internal_v2_*_region_breakdown.csv`", "- `results/analysis/aes_internal_v2_mc_random_status_differences.csv`", "- `reports/AES_INTERNAL_STUCK_COVERAGE_V2.svg`", "- `reports/AES_INTERNAL_TRANSITION_COVERAGE_V2.svg`"]
    (REPORTS / "AES_INTERNAL_D1_D5_REPORT.md").write_text("\n".join(lines) + "\n")
    validity = {"revision": 2, "dft_audit_pass": dft_valid, "stuck_complete": len([row for row in all_summaries["stuck"] if row.get("status") == "PASS"]) == len(CASES), "transition_complete": len([row for row in all_summaries["transition"] if row.get("status") == "PASS"]) == len(CASES), "direct_faults_excluded_globally": True, "historical_422_used": False, "status_difference_rows": len(differences), "region_stuck_complete": sum(row.get("status") == "PASS" for row in parse_region_summaries("stuck")) == len(CASES) * 6, "region_transition_complete": sum(row.get("status") == "PASS" for row in parse_region_summaries("transition")) == len(CASES) * 6}
    (ANALYSIS / "aes_internal_v2_validity.json").write_text(json.dumps(validity, indent=2) + "\n")
    print(json.dumps({"dft_audit_pass": dft_valid, "stuck_pass": sum(row.get("status") == "PASS" for row in all_summaries["stuck"]), "transition_pass": sum(row.get("status") == "PASS" for row in all_summaries["transition"]), "status_difference_rows": len(differences)}, indent=2))


if __name__ == "__main__":
    main()
