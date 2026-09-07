#!/usr/bin/env python3
"""Build sequential-boundary-aware AES region and connectivity metadata."""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from aes_internal_prepare import parse_netlist_instances, read_lines  # noqa: E402

ROOT = SCRIPT_DIR.parent
CONFIG = ROOT / "config"
CHECKPOINT = ROOT / "results/checkpoint/mor1kx_aes_soc_pre_dft.v"
STAGES = ("IARK", "SB", "SR", "MC")
DATA_OUTPUT_PINS = {"Z", "ZN", "Y", "CO", "O", "SO"}
CONTROL_PINS = {"CP", "CD", "CK", "CLK", "RESET", "RST", "SE", "SI", "SD"}


def norm(value: str) -> str:
    return value.strip().lstrip("\\")


def stage_cells() -> dict[str, set[str]]:
    return {
        stage: set(read_lines(CONFIG / f"{stage.lower()}_scan.list"))
        for stage in STAGES
    }


def backward_cone_until_sequential(
    instances: dict[str, dict[str, str]],
    driver: dict[str, str],
    target_nets: set[str],
    sequential_cells: set[str] | None = None,
) -> set[str]:
    """Return normalized nets and pins reached before sequential boundaries."""
    seen_nets: set[str] = set()
    seen_cells: set[str] = set()
    queue = deque(target_nets)
    sites: set[str] = set()
    sequential_prefixes = ("FD", "TLAT", "LAT")
    sequential_cells = sequential_cells or set()
    while queue:
        net = queue.popleft()
        if not net or net in seen_nets:
            continue
        seen_nets.add(net)
        sites.add(norm(net))
        cell = driver.get(net)
        if cell is None or cell in seen_cells:
            continue
        seen_cells.add(cell)
        pins = instances.get(cell, {})
        if cell in sequential_cells or cell.startswith(sequential_prefixes):
            continue
        sites.update(norm(f"{cell}/{pin}") for pin in pins if pin not in CONTROL_PINS)
        for pin, source in pins.items():
            if pin in DATA_OUTPUT_PINS or pin in CONTROL_PINS or not source:
                continue
            queue.append(source)
    return sites


def build_region_metadata(checkpoint: Path = CHECKPOINT) -> dict[str, object]:
    instances, driver, consumers = parse_netlist_instances(checkpoint)
    sequential_cells = set(read_lines(checkpoint.parent / "register_inventory.rpt"))
    stages = stage_cells()
    stage_cones: dict[str, set[str]] = {}
    stage_q_nets: dict[str, set[str]] = {}
    stage_d_nets: dict[str, set[str]] = {}
    stage_d_raw_nets: dict[str, set[str]] = {}
    for stage in STAGES:
        q_nets = {instances[cell].get("Q", instances[cell].get("QN", "")) for cell in stages[stage]}
        d_nets = {instances[cell].get("D", "") for cell in stages[stage]}
        if not q_nets or not d_nets or "" in q_nets or "" in d_nets:
            raise ValueError(f"missing Q/D net in {stage} stage")
        stage_q_nets[stage] = {norm(net) for net in q_nets}
        stage_d_raw_nets[stage] = set(d_nets)
        stage_d_nets[stage] = {norm(net) for net in d_nets}
        stage_cones[stage] = backward_cone_until_sequential(instances, driver, d_nets, sequential_cells)

    source_sites = {
        norm(line.split()[2])
        for line in read_lines(CONFIG / "aes_internal_v2_raw_stuck.list")
        if len(line.split()) >= 3
    }
    memberships: dict[str, list[str]] = {}
    for site in source_sites:
        memberships[site] = [stage for stage in STAGES if site in stage_cones[stage]]

    regions: dict[str, set[str]] = {
        "IARK_CONE": set(),
        "SB_CONE": set(),
        "SR_CONE": set(),
        "MC_CONE": set(),
        "SHARED_OR_OVERLAP": set(),
        "AES_CONTROL": set(),
        "AES_OTHER": set(),
        "UNRESOLVED": set(),
    }
    control_words = ("start", "valid", "done", "busy", "ready", "enable", "state")
    for site, members in memberships.items():
        if len(members) > 1:
            regions["SHARED_OR_OVERLAP"].add(site)
        elif len(members) == 1:
            regions[f"{members[0]}_CONE"].add(site)
        elif any(word in site.lower() for word in control_words):
            regions["AES_CONTROL"].add(site)
        elif site.startswith("u_aes_peripheral/"):
            regions["AES_OTHER"].add(site)
        else:
            regions["UNRESOLVED"].add(site)

    predecessor_edges: dict[str, dict[str, object]] = {}
    for index, stage in enumerate(STAGES):
        d_nets = stage_d_nets[stage]
        d_raw_nets = stage_d_raw_nets[stage]
        drivers = sorted({driver.get(net, "") for net in d_raw_nets})
        predecessor = STAGES[index - 1] if index else "INPUT_OR_KEY"
        if index:
            expected_q = stage_q_nets[STAGES[index - 1]]
            observed = sorted(expected_q & stage_cones[stage])
        else:
            input_markers = sorted(
                site for site in stage_cones[stage]
                if "plaintext_reg" in site or "key_reg" in site
            )
            observed = input_markers
        predecessor_edges[stage] = {
            "predecessor": predecessor,
            "d_net_count": len(d_nets),
            "driver_count": len([cell for cell in drivers if cell]),
            "missing_driver_count": len([cell for cell in drivers if not cell]),
            "observed_predecessor_sites": observed[:16],
            "observed_predecessor_site_count": len(observed),
            "connectivity_pass": bool(drivers) and not any(not cell for cell in drivers) and bool(observed),
        }

    metadata = {
        "revision": 2,
        "checkpoint": str(checkpoint),
        "region_site_count": {name: len(values) for name, values in regions.items()},
        "regions": {name: sorted(values) for name, values in regions.items()},
        "stage_cone_site_count": {stage: len(stage_cones[stage] & source_sites) for stage in STAGES},
        "stage_cone_raw_site_count": {stage: len(stage_cones[stage]) for stage in STAGES},
        "predecessor_edges": predecessor_edges,
        "control_pins_excluded": sorted(CONTROL_PINS),
        "sequential_boundary_rule": "stop at FD/TLAT/LAT and never enqueue CP/CD/CK/SE/SI/SD",
        "allowed_source_site_count": len(source_sites),
        "connectivity_pass": all(bool(row["connectivity_pass"]) for row in predecessor_edges.values()),
        "functional_equivalence": "not run by graph preflight; must be checked after DFT insertion",
    }
    (CONFIG / "aes_internal_v2_region_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    analysis = ROOT / "results/analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "aes_internal_v2_connectivity.json").write_text(json.dumps({
        "connectivity_pass": metadata["connectivity_pass"],
        "predecessor_edges": predecessor_edges,
        "functional_equivalence": metadata["functional_equivalence"],
    }, indent=2) + "\n")
    return metadata


def classify_aes_region(site: str, metadata: dict[str, object]) -> str:
    normalized = norm(site)
    for region, sites in metadata.get("regions", {}).items():
        if normalized in set(sites):
            return region
    return "UNRESOLVED"


def main() -> None:
    metadata = build_region_metadata()
    print(json.dumps({
        "revision": metadata["revision"],
        "region_site_count": metadata["region_site_count"],
        "stage_cone_site_count": metadata["stage_cone_site_count"],
        "predecessor_edges": metadata["predecessor_edges"],
        "connectivity_pass": metadata["connectivity_pass"],
    }, indent=2))


if __name__ == "__main__":
    main()
