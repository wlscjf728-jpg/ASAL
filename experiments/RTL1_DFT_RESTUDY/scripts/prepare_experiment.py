#!/usr/bin/env python3
"""Prepare common fault exclusions, structural cones, and D5 ranking inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
CHECKPOINT = ROOT / "results/checkpoint/mor1kx_aes_soc_pre_dft.v"
RAW_FAULTS = CONFIG / "canonical_faults_all.list"
STAGES = ("IARK", "SB", "SR", "MC")


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_fault_sites() -> set[str]:
    sites = set()
    for line in read_lines(RAW_FAULTS):
        fields = line.split()
        if len(fields) >= 3 and fields[0] in {"sa0", "sa1"}:
            sites.add(fields[2])
    return sites


def parse_instances(text: str) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, set[str]]]:
    instances: dict[str, dict[str, str]] = {}
    driver: dict[str, str] = {}
    consumers: dict[str, set[str]] = defaultdict(set)
    header = re.compile(r"^[ \t]+(\S+)[ \t]+(.+?)[ \t]+\(", re.MULTILINE)
    for match in header.finditer(text):
        cell_type, raw_name = match.groups()
        if cell_type.startswith(("FD", "TLAT", "LAT")) or cell_type[0].isalpha():
            start = match.start()
            end = text.find(");", start)
            if end < 0:
                continue
            block = text[start:end]
            pins = {
                pin: net.strip()
                for pin, net in re.findall(r"\.([A-Za-z0-9_]+)\s*\(\s*([^()]+?)\s*\)", block)
            }
            name = raw_name.strip()
            if name.startswith("\\"):
                name = name[1:]
            instances[name] = pins
            outputs = {"Z", "ZN", "Y", "Q", "QN", "CO", "O", "SO"}
            for pin, net in pins.items():
                if pin in outputs and net:
                    driver[net] = name
                elif net:
                    consumers[net].add(name)
    return instances, driver, consumers


def cell_q_sites(instances: dict[str, dict[str, str]], cells: set[str], raw_sites: set[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for cell in sorted(cells):
        pins = instances.get(cell)
        if pins is None or not any(pin in pins for pin in ("Q", "QN")):
            raise SystemExit(f"missing Q/QN pin for {cell}")
        candidates = []
        for pin in ("Q", "QN"):
            if pin not in pins:
                continue
            pin_site = "\\" + cell + "/" + pin
            if pin_site in raw_sites:
                candidates.append(pin_site)
            qnet = pins[pin]
            if qnet in raw_sites:
                candidates.append(qnet)
        kept = sorted(set(candidates))
        if not kept:
            raise SystemExit(f"no raw fault site for Q/QN of {cell}")
        result[cell] = kept
    return result


def backward_cone(instances: dict[str, dict[str, str]], driver: dict[str, str], targets: set[str]) -> set[str]:
    seen_nets: set[str] = set()
    seen_cells: set[str] = set()
    queue = deque(targets)
    output_pins = {"Z", "ZN", "Y", "Q", "QN", "CO", "O", "SO"}
    while queue:
        net = queue.popleft()
        if not net or net in seen_nets:
            continue
        seen_nets.add(net)
        cell = driver.get(net)
        if cell is None or cell in seen_cells:
            continue
        seen_cells.add(cell)
        pins = instances[cell]
        if cell.startswith(("FD", "TLAT", "LAT")):
            continue
        for pin, source in pins.items():
            if pin not in output_pins and source:
                queue.append(source)
    sites = set(seen_nets)
    for cell in seen_cells:
        for pin in instances[cell]:
            sites.add("\\" + cell + "/" + pin)
    return sites


def forward_cone(instances: dict[str, dict[str, str]], consumers: dict[str, set[str]], start: str) -> tuple[int, int, int, int]:
    seen_nets: set[str] = set()
    seen_cells: set[str] = set()
    queue = deque([start])
    endpoints = 0
    aes_endpoints = 0
    while queue:
        net = queue.popleft()
        if not net or net in seen_nets:
            continue
        seen_nets.add(net)
        plain = net.lstrip("\\")
        if plain.startswith(("aes_result_o", "aes_done_o")):
            endpoints += 1
            aes_endpoints += 1
        elif plain.startswith(("iwb_", "dwb_")):
            endpoints += 1
        for cell in consumers.get(net, set()):
            if cell in seen_cells:
                continue
            seen_cells.add(cell)
            if cell.startswith(("FD", "TLAT", "LAT")):
                continue
            for pin, outnet in instances[cell].items():
                if pin in {"Z", "ZN", "Y", "CO", "O", "SO"} and outnet:
                    queue.append(outnet)
    return len(seen_cells), len(seen_nets), endpoints, aes_endpoints


def main() -> None:
    raw_sites = parse_fault_sites()
    text = CHECKPOINT.read_text()
    instances, driver, consumers = parse_instances(text)
    manifests = {stage: set(read_lines(CONFIG / f"{stage.lower()}_scan.list")) for stage in STAGES}
    random_sets = [set(read_lines(CONFIG / f"random_scan_seed{i:02d}.list")) for i in range(1, 11)]
    random_pool = set().union(*random_sets)
    candidate_cells = set().union(*manifests.values(), random_pool)
    q_sites = cell_q_sites(instances, candidate_cells, raw_sites)

    direct_sites = set().union(*(set(sites) for sites in q_sites.values()))
    direct_sa = [f"sa{pol} NC {site}" for site in sorted(direct_sites) for pol in (0, 1)]
    CONFIG.joinpath("direct_variable_faults.list").write_text("\n".join(direct_sa) + "\n")
    transition_lines = [f"st{kind} NC {site}" for site in sorted(direct_sites) for kind in ("r", "f")]
    CONFIG.joinpath("direct_variable_transition_faults.list").write_text("\n".join(transition_lines) + "\n")

    q_rows = []
    for stage, cells in manifests.items():
        for cell in sorted(cells):
            q_rows.append({"cell": cell, "placement": stage, "q_sites": ";".join(q_sites[cell]), "q_net": instances[cell].get("Q", instances[cell].get("QN", ""))})
    for cell in sorted(random_pool):
        q_rows.append({"cell": cell, "placement": "RANDOM_POOL", "q_sites": ";".join(q_sites[cell]), "q_net": instances[cell].get("Q", instances[cell].get("QN", ""))})
    with CONFIG.joinpath("q_site_manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["cell", "placement", "q_sites", "q_net"])
        writer.writeheader()
        writer.writerows(q_rows)

    mc_d = {instances[cell].get("D") for cell in manifests["MC"] if instances[cell].get("D")}
    mc_cone = backward_cone(instances, driver, mc_d)
    aes_sites = {site for site in raw_sites if site.lstrip("\\").startswith("u_aes_peripheral/") or site.startswith(("aes_result_o", "aes_done_o"))}
    host_sites = {site for site in raw_sites if site.lstrip("\\").startswith("u_mor1kx/") or site.startswith(("iwb_", "dwb_"))}
    metadata = {
        "direct_sites": sorted(direct_sites),
        "mc_cone_sites": sorted(mc_cone),
        "aes_sites": sorted(aes_sites),
        "host_sites": sorted(host_sites),
        "raw_fault_sites": len(raw_sites),
        "candidate_count": len(candidate_cells),
        "random_pool_count": len(random_pool),
    }
    CONFIG.joinpath("region_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    ranking = []
    for stage in (*STAGES, "RANDOM_POOL"):
        cells = set().union(*(manifests.values())) if stage == "RANDOM_POOL" else manifests[stage]
        if stage == "RANDOM_POOL":
            cells = random_pool
        for cell in sorted(cells):
            qnet = instances[cell].get("Q", instances[cell].get("QN", ""))
            nodes, nets, endpoints, aes_endpoints = forward_cone(instances, consumers, qnet)
            fanin_depth = 0
            dnet = instances[cell].get("D", "")
            seen = set()
            while dnet and dnet not in seen and dnet in driver:
                seen.add(dnet)
                dcell = driver[dnet]
                fanin_depth += 1
                if dcell.startswith(("FD", "TLAT", "LAT")):
                    break
                next_inputs = [net for pin, net in instances[dcell].items() if pin not in {"Z", "ZN", "Y", "Q", "QN", "CO", "O", "SO"}]
                dnet = next_inputs[0] if next_inputs else ""
            score = 2 * nodes + nets + 20 * aes_endpoints + 5 * endpoints - fanin_depth
            ranking.append({"cell": cell, "placement": stage, "q_net": qnet, "fanout_nodes": nodes, "fanout_nets": nets, "output_endpoints": endpoints, "aes_endpoints": aes_endpoints, "fanin_depth_proxy": fanin_depth, "topology_score": score})
    ranking.sort(key=lambda row: (-row["topology_score"], row["cell"]))
    with ROOT.joinpath("results/analysis/topology_ranking.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ranking[0].keys())
        writer.writeheader()
        writer.writerows(ranking)
    auto = [row["cell"] for row in ranking[:128]]
    CONFIG.joinpath("auto_topology_scan.list").write_text("\n".join(auto) + "\n")

    manifest = {
        "checkpoint_ddc_sha256": sha256(ROOT / "results/checkpoint/mor1kx_aes_soc_pre_dft.ddc"),
        "checkpoint_verilog_sha256": sha256(CHECKPOINT),
        "raw_fault_file_sha256": sha256(RAW_FAULTS),
        "raw_fault_line_count": sum(1 for _ in RAW_FAULTS.open()),
        "raw_fault_site_count": len(raw_sites),
        "stage_counts": {stage: len(manifests[stage]) for stage in STAGES},
        "random_pool_count": len(random_pool),
        "candidate_count": len(candidate_cells),
        "direct_site_count": len(direct_sites),
        "direct_stuck_fault_count": len(direct_sa),
        "direct_transition_fault_count": len(transition_lines),
        "common_scan_count": len(read_lines(CONFIG / "stage_common_scan.list")),
        "variable_budget": 128,
        "total_scan_count": 1024,
        "chain_count": 1,
        "ranking": "pre-ATPG structural fanout/SCOAP proxy; no fault status or hidden key input",
    }
    CONFIG.joinpath("experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
