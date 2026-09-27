"""Small, deterministic helpers shared by the DFT experiment analyzers."""

from __future__ import annotations

import re
from typing import Iterable

FAULT_LINE = re.compile(r"^\s*(sa[01]|str|stf)\s+(\S+)\s+(\S+)(?:\s+\([^)]*\))?")


def parse_fault_line(line: str) -> dict[str, str] | None:
    match = FAULT_LINE.match(line)
    if not match:
        return None
    polarity, status, site = match.groups()
    return {"polarity": polarity, "status": status, "site": site}


def build_direct_fault_lines(
    selected_cells: Iterable[str], q_sites: dict[str, str]
) -> list[str]:
    """Return a stable TetraMAX delete list for selected FF Q nets."""
    sites = []
    for cell in selected_cells:
        if cell not in q_sites:
            raise KeyError(f"missing Q site for {cell}")
        sites.append(q_sites[cell])
    return [line for site in sorted(set(sites)) for line in (f"sa0 {site}", f"sa1 {site}")]


def classify_region(site: str, metadata: dict[str, set[str]]) -> str:
    if site in metadata.get("direct_sites", set()):
        return "selected_ff_direct"
    if site in metadata.get("mc_cone_sites", set()):
        return "mc_cone"
    if site in metadata.get("aes_sites", set()):
        return "aes_other"
    if site.startswith("u_mor1kx/") or site.startswith("iwb_") or site.startswith("dwb_"):
        return "host"
    return "unresolved"


def parse_summary_text(text: str) -> dict[str, int | float]:
    patterns: dict[str, tuple[str, type[int] | type[float]]] = {
        "detected": (r"Detected\s+\S+\s+(\d+)", int),
        "possibly_detected": (r"Possibly detected\s+\S+\s+(\d+)", int),
        "undetectable": (r"Undetectable\s+\S+\s+(\d+)", int),
        "atpg_untestable": (r"ATPG untestable\s+\S+\s+(\d+)", int),
        "not_detected": (r"Not detected\s+\S+\s+(\d+)", int),
        "total_faults": (r"total faults\s+(\d+)", int),
        "coverage_pct": (r"test coverage\s+([\d.]+)%", float),
        "patterns": (r"#internal patterns\s+(\d+)", int),
        "cpu_seconds": (r"Total CPU time\s+([\d.]+)", float),
    }
    parsed: dict[str, int | float] = {}
    for key, (pattern, converter) in patterns.items():
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            if key == "cpu_seconds":
                continue
            raise ValueError(f"missing TetraMAX summary field: {key}")
        parsed[key] = converter(match.group(1))
    return parsed


def classify_atpg_state(code: str) -> str:
    if code in {"DS", "DI", "DT"}:
        return "DT"
    if code in {"AN", "AU"}:
        return "AU"
    if code == "--":
        return "EQUIVALENT"
    return code


def pareto_frontier(points: list[dict[str, object]]) -> list[dict[str, object]]:
    """Keep points not dominated by higher testability and lower leakage."""
    result = []
    for candidate in points:
        testability = float(candidate["testability"])
        leakage = float(candidate["leakage"])
        dominated = any(
            float(other["testability"]) >= testability
            and float(other["leakage"]) <= leakage
            and (
                float(other["testability"]) > testability
                or float(other["leakage"]) < leakage
            )
            for other in points
            if other is not candidate
        )
        if not dominated:
            result.append(candidate)
    return result
