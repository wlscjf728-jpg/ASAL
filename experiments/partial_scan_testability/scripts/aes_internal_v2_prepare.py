#!/usr/bin/env python3
"""Build the revision-2 AES-internal scan manifests and invariants."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import deque
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from aes_internal_prepare import (  # noqa: E402
    cell_q_sites,
    parse_netlist_instances,
    read_lines,
)

ROOT = SCRIPT_DIR.parent
CONFIG = ROOT / "config"
CHECKPOINT = ROOT / "results/checkpoint/mor1kx_aes_soc_pre_dft.v"
INVENTORY = ROOT / "results/checkpoint/register_inventory.rpt"
STAGES = ("IARK", "SB", "SR", "MC")
SEEDS = tuple(range(1, 11))
COMMON_COUNT = 896
VARIABLE_COUNT = 128


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_list(path: Path, values: list[str]) -> None:
    path.write_text("\n".join(values) + ("\n" if values else ""))


def is_aes_cell(cell: str) -> bool:
    return cell.lstrip("\\").startswith("u_aes_peripheral/")


def is_stage_cell(cell: str, stage: str) -> bool:
    return f"u_aes_peripheral/u_aes_round1/{stage}_REG_reg[" in cell


def all_stage_sets() -> dict[str, set[str]]:
    return {
        stage: set(read_lines(CONFIG / f"{stage.lower()}_scan.list"))
        for stage in STAGES
    }


def parse_fault_sites(path: Path) -> set[str]:
    result: set[str] = set()
    for line in read_lines(path):
        fields = line.split()
        if len(fields) >= 3 and fields[0] in {"sa0", "sa1"}:
            result.add(fields[2])
    return result


def forward_metrics(
    consumers: dict[str, set[str]],
    instances: dict[str, dict[str, str]],
    start: str,
) -> tuple[int, int, int]:
    seen_nets: set[str] = set()
    seen_cells: set[str] = set()
    queue = deque([start])
    endpoints = 0
    while queue:
        net = queue.popleft()
        if not net or net in seen_nets:
            continue
        seen_nets.add(net)
        for cell in consumers.get(net, set()):
            if cell in seen_cells:
                continue
            seen_cells.add(cell)
            if cell.startswith(("FD", "TLAT", "LAT")):
                continue
            for pin, output_net in instances.get(cell, {}).items():
                if pin in {"Z", "ZN", "Y", "CO", "O", "SO"} and output_net:
                    plain = output_net.lstrip("\\")
                    if plain.startswith(("aes_result_o", "aes_done_o")):
                        endpoints += 1
                    queue.append(output_net)
    return len(seen_cells), len(seen_nets), endpoints


def build_manifests(root: Path = ROOT) -> dict[str, object]:
    config = root / "config"
    checkpoint_dir = root / "results/checkpoint"
    inventory = set(read_lines(checkpoint_dir / "register_inventory.rpt"))
    common = set(read_lines(config / "stage_common_scan.list"))
    stages = all_stage_sets()
    stage_union = set().union(*stages.values())
    aes = {cell for cell in inventory if is_aes_cell(cell)}
    aes_non_stage = aes - stage_union
    if len(inventory) != 4157 or len(aes) != 772:
        raise ValueError(f"unexpected inventory counts: total={len(inventory)} aes={len(aes)}")
    if len(common) != COMMON_COUNT or not common.issubset(inventory):
        raise ValueError("common scan set is not the expected 896-cell checkpoint set")
    if not all(len(stages[stage]) == VARIABLE_COUNT for stage in STAGES):
        raise ValueError("one or more stage lists is not 128 cells")
    for index, left in enumerate(STAGES):
        for right in STAGES[index + 1:]:
            if stages[left] & stages[right]:
                raise ValueError(f"stage lists overlap: {left}/{right}")
    if not stage_union.issubset(aes) or len(aes_non_stage) != 260:
        raise ValueError("AES stage partition is inconsistent")

    required_common_prefixes = (
        "u_aes_peripheral/key_reg_reg[",
        "u_aes_peripheral/plaintext_reg_reg[",
    )
    for prefix in required_common_prefixes:
        required = {cell for cell in inventory if cell.startswith(prefix)}
        if len(required) != 128 or not required.issubset(common):
            raise ValueError(f"input register is not fully common: {prefix}")

    for name, values in {
        "common_scan_v2.list": sorted(common),
        "iark_scan_v2.list": sorted(stages["IARK"]),
        "sb_scan_v2.list": sorted(stages["SB"]),
        "sr_scan_v2.list": sorted(stages["SR"]),
        "mc_scan_v2.list": sorted(stages["MC"]),
        "aes_stage_pool_v2.list": sorted(stage_union),
    }.items():
        write_list(config / name, values)

    cases: dict[str, list[str]] = {}
    rows: list[dict[str, object]] = []
    for stage in STAGES:
        case = f"CASE_{stage}"
        cells = sorted(stages[stage])
        cases[case] = cells
        for rank, cell in enumerate(cells, 1):
            rows.append({"case": case, "seed": "", "mc_count": "", "pool": "AES_STAGE", "rank": rank, "cell": cell})

    stage_pool = sorted(stage_union)
    for seed in SEEDS:
        cells = sorted(random.Random(seed).sample(stage_pool, VARIABLE_COUNT))
        case = f"CASE_RANDOM_STAGE_seed{seed:02d}"
        cases[case] = cells
        write_list(config / f"random_stage_seed{seed:02d}.list", cells)
        counts = {stage: sum(is_stage_cell(cell, stage) for cell in cells) for stage in STAGES}
        for rank, cell in enumerate(cells, 1):
            rows.append({"case": case, "seed": seed, "mc_count": counts["MC"], "pool": "AES_STAGE_RANDOM", "rank": rank, "cell": cell})

    non_mc = sorted(stage_union - stages["MC"])
    mc_perm = sorted(stages["MC"])
    non_mc_perm = sorted(non_mc)
    for mc_count in (0, 32, 64, 96, 128):
        cells = sorted(mc_perm[:mc_count] + non_mc_perm[: VARIABLE_COUNT - mc_count])
        case = f"CASE_MIX_MC_{mc_count:03d}"
        cases[case] = cells
        write_list(config / f"mix_mc_{mc_count:03d}.list", cells)
        for rank, cell in enumerate(cells, 1):
            rows.append({"case": case, "seed": "", "mc_count": mc_count, "pool": "MC_MIX_NESTED", "rank": rank, "cell": cell})

    instances, _, consumers = parse_netlist_instances(checkpoint_dir / "mor1kx_aes_soc_pre_dft.v")
    ranking: list[dict[str, object]] = []
    for cell in stage_pool:
        qnet = instances[cell].get("Q", instances[cell].get("QN", ""))
        nodes, nets, endpoints = forward_metrics(consumers, instances, qnet)
        ranking.append({"cell": cell, "fanout_nodes": nodes, "fanout_nets": nets, "aes_endpoints": endpoints, "score": 2 * nodes + nets + 20 * endpoints})
    ranking.sort(key=lambda row: (-int(row["score"]), str(row["cell"])))
    auto = [str(row["cell"]) for row in ranking[:VARIABLE_COUNT]]
    cases["CASE_AUTO_STAGE"] = auto
    write_list(config / "auto_stage_scan_v2.list", auto)
    with (root / "results/analysis/aes_internal_v2_topology_ranking.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ranking[0].keys()))
        writer.writeheader()
        writer.writerows(ranking)
    for rank, cell in enumerate(auto, 1):
        rows.append({"case": "CASE_AUTO_STAGE", "seed": "", "mc_count": sum(is_stage_cell(cell, "MC") for cell in auto), "pool": "AES_STAGE_TOPOLOGY", "rank": rank, "cell": cell})

    with (config / "aes_internal_v2_candidate_manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case", "seed", "mc_count", "pool", "rank", "cell"])
        writer.writeheader()
        writer.writerows(rows)

    raw_sites = parse_fault_sites(config / "canonical_faults_all.list")
    aes_q = cell_q_sites(instances, aes, raw_sites)
    direct_sites = sorted({site for sites in aes_q.values() for site in sites})
    write_list(config / "aes_internal_v2_direct_sites.list", direct_sites)
    write_list(config / "aes_internal_v2_direct_exclusion_stuck.list", [f"sa{pol} NC {site}" for site in direct_sites for pol in (0, 1)])
    write_list(config / "aes_internal_v2_direct_exclusion_transition.list", [f"st{pol} NC {site}" for site in direct_sites for pol in ("r", "f")])
    with (config / "aes_internal_v2_q_site_manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["cell", "q_sites", "q_net"])
        writer.writeheader()
        for cell in sorted(aes):
            writer.writerow({"cell": cell, "q_sites": ";".join(aes_q[cell]), "q_net": instances[cell].get("Q", instances[cell].get("QN", ""))})

    manifest = {
        "revision": 2,
        "checkpoint_ddc_sha256": digest(checkpoint_dir / "mor1kx_aes_soc_pre_dft.ddc"),
        "checkpoint_verilog_sha256": digest(CHECKPOINT),
        "inventory_sha256": digest(INVENTORY),
        "inventory_count": len(inventory),
        "aes_count": len(aes),
        "stage_counts": {stage: len(stages[stage]) for stage in STAGES},
        "aes_non_stage_count": len(aes_non_stage),
        "common_count": len(common),
        "common_aes_count": len(common & aes),
        "common_host_count": len(common - aes),
        "variable_count": VARIABLE_COUNT,
        "total_scan_count": COMMON_COUNT + VARIABLE_COUNT,
        "chain_count": 1,
        "random_stage_seed_count": len(SEEDS),
        "random_stage_pool_count": len(stage_pool),
        "mix_mc_counts": [0, 32, 64, 96, 128],
        "direct_exclusion_scope": "Q/QN sites of all AES 772 FFs, common to every case",
        "direct_site_count": len(direct_sites),
        "case_count": len(cases),
        "case_names": sorted(cases),
        "ranking": "deterministic structural forward fanout proxy over all 512 AES stage FFs; no ATPG/leakage/key input",
    }
    (config / "aes_internal_v2_experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for case, cells in cases.items():
        if case == "CASE_AUTO_STAGE":
            expected = VARIABLE_COUNT
        else:
            expected = VARIABLE_COUNT
        if len(cells) != expected or common & set(cells):
            raise AssertionError(f"invalid case {case}: count={len(cells)} common_overlap={len(common & set(cells))}")
    return manifest


def main() -> None:
    print(json.dumps(build_manifests(), indent=2))


if __name__ == "__main__":
    main()
