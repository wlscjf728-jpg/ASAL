#!/usr/bin/env python3
"""Prepare AES-internal-only scan candidates from the shared checkpoint."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

STAGES = ("IARK", "SB", "SR", "MC")
SEEDS = tuple(range(1, 11))
VARIABLE_BUDGET = 128
COMMON_BUDGET = 896
TOTAL_SCAN = 1024
FAULT_KINDS = {"sa0", "sa1"}

def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_register_inventory(path: Path) -> set[str]:
    return set(read_lines(path))

def _is_aes_cell(cell: str) -> bool:
    normalized = cell.lstrip("\\")
    return normalized.startswith("u_aes_peripheral/")

def partition_candidate_cells(
    inventory: set[str], common: set[str], stage_sets: dict[str, set[str]]
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {"COMMON": set(common)}
    stage_union: set[str] = set()
    for stage, cells in stage_sets.items():
        result[stage] = set(cells)
        stage_union.update(cells)
    result["AES_NON_STAGE"] = {
        cell for cell in inventory - common - stage_union if _is_aes_cell(cell)
    }
    result["HOST_NON_COMMON"] = inventory - common - stage_union - result["AES_NON_STAGE"]
    return result

def select_host_common(
    inventory: set[str], old_common: set[str], forbidden: set[str], count: int
) -> list[str]:
    """Preserve old eligible host cells, then fill lexically from host inventory."""
    old = sorted(cell for cell in old_common if cell in inventory and cell not in forbidden)
    if len(old) > count:
        raise ValueError(f"old common host set has {len(old)} cells, budget is {count}")
    fill = sorted(
        cell for cell in inventory
        if cell not in forbidden and cell not in set(old)
    )
    selected = old + fill[: count - len(old)]
    if len(selected) != count:
        raise ValueError(f"only {len(selected)} eligible host cells for common budget {count}")
    if len(set(selected)) != count:
        raise AssertionError("common selection is not unique")
    return selected

def select_seeded_pool(pool: set[str], count: int, seed: int) -> list[str]:
    if count < 0 or count > len(pool):
        raise ValueError(f"cannot select {count} cells from pool of {len(pool)}")
    rng = random.Random(seed)
    return sorted(rng.sample(sorted(pool), count))

def parse_netlist_instances(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, set[str]]]:
    text = path.read_text()
    instances: dict[str, dict[str, str]] = {}
    driver: dict[str, str] = {}
    consumers: dict[str, set[str]] = defaultdict(set)
    header = re.compile(r"^[ \t]+(\S+)[ \t]+(.+?)[ \t]+\(", re.MULTILINE)
    outputs = {"Z", "ZN", "Y", "Q", "QN", "CO", "O", "SO"}
    for match in header.finditer(text):
        cell_type, raw_name = match.groups()
        if not cell_type or not cell_type[0].isalpha():
            continue
        start = match.start()
        end = text.find(");", start)
        if end < 0:
            continue
        block = text[start:end]
        pins = {
            pin: net.strip()
            for pin, net in re.findall(
                r"\.([A-Za-z0-9_]+)\s*\(\s*([^()]+?)\s*\)", block
            )
        }
        name = raw_name.strip()
        if name.startswith("\\"):
            name = name[1:]
        instances[name] = pins
        for pin, net in pins.items():
            if not net:
                continue
            if pin in outputs:
                driver[net] = name
            else:
                consumers[net].add(name)
    return instances, driver, consumers

def cell_q_sites(
    instances: dict[str, dict[str, str]], cells: set[str], raw_sites: set[str]
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for cell in sorted(cells):
        pins = instances.get(cell)
        if pins is None or not any(pin in pins for pin in ("Q", "QN")):
            raise ValueError(f"missing Q/QN pin for {cell}")
        candidates: list[str] = []
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
            raise ValueError(f"no raw fault site for Q/QN of {cell}")
        result[cell] = kept
    return result

def _parse_stuck_sites(path: Path) -> set[str]:
    sites: set[str] = set()
    for line in read_lines(path):
        fields = line.split()
        if len(fields) >= 3 and fields[0] in FAULT_KINDS:
            sites.add(fields[2])
    return sites

def _write_list(path: Path, values: list[str] | set[str]) -> None:
    ordered = list(values) if isinstance(values, list) else sorted(values)
    path.write_text("\n".join(ordered) + ("\n" if ordered else ""))

def build_candidate_manifests(root: Path) -> dict[str, list[str]]:
    config = root / "config"
    checkpoint_dir = root / "results" / "checkpoint"
    inventory = load_register_inventory(checkpoint_dir / "register_inventory.rpt")
    old_common = set(read_lines(config / "stage_common_scan.list"))
    stage_sets = {
        stage: set(read_lines(config / f"{stage.lower()}_scan.list"))
        for stage in STAGES
    }
    stage_union = set().union(*stage_sets.values())
    for index, left in enumerate(STAGES):
        for right in STAGES[index + 1:]:
            if stage_sets[left] & stage_sets[right]:
                raise AssertionError(f"stage sets overlap: {left}/{right}")
    aes_all = {cell for cell in inventory if _is_aes_cell(cell)}
    host_all = inventory - aes_all
    if len(aes_all) != 772:
        raise ValueError(f"expected 772 AES cells, found {len(aes_all)}")
    if any(len(stage_sets[stage]) != 128 for stage in STAGES):
        raise ValueError("stage manifest does not contain exactly 128 cells")
    if not stage_union.issubset(aes_all):
        raise AssertionError("stage manifest contains non-AES cell")
    new_common = select_host_common(inventory, old_common, aes_all, COMMON_BUDGET)
    common_set = set(new_common)
    if common_set & aes_all:
        raise AssertionError("AES cell leaked into host-only common set")
    host_noncommon = host_all - common_set
    aes_nonstage = aes_all - stage_union
    if len(host_all) != 3385:
        raise ValueError(f"expected 3385 host cells, found {len(host_all)}")
    if len(aes_nonstage) != 260:
        raise ValueError(f"expected 260 AES non-stage cells, found {len(aes_nonstage)}")
    if len(host_noncommon) < VARIABLE_BUDGET:
        raise ValueError("host pool is too small for random controls")

    manifests: dict[str, list[str]] = {
        "COMMON": new_common,
        "CASE_IARK": sorted(stage_sets["IARK"]),
        "CASE_SB": sorted(stage_sets["SB"]),
        "CASE_SR": sorted(stage_sets["SR"]),
        "CASE_MC": sorted(stage_sets["MC"]),
    }
    _write_list(config / "common_scan_aes_internal.list", new_common)
    for stage in STAGES:
        _write_list(config / f"{stage.lower()}_scan_aes_internal.list", manifests[f"CASE_{stage}"])

    candidate_rows: list[dict[str, str | int]] = []
    for case in ("CASE_IARK", "CASE_SB", "CASE_SR", "CASE_MC"):
        cells = manifests[case]
        for rank, cell in enumerate(cells, start=1):
            candidate_rows.append({
                "case": case, "seed": "", "pool": "AES_STAGE",
                "rank": rank, "cell": cell,
            })

    for seed in SEEDS:
        aes_cells = select_seeded_pool(aes_nonstage, VARIABLE_BUDGET, seed)
        host_cells = select_seeded_pool(host_noncommon, VARIABLE_BUDGET, seed)
        for kind, cells in (("AES", aes_cells), ("HOST", host_cells)):
            case = f"CASE_RANDOM_{kind}_seed{seed:02d}"
            manifests[case] = cells
            _write_list(config / f"random_{kind.lower()}_seed{seed:02d}.list", cells)
            for rank, cell in enumerate(cells, start=1):
                candidate_rows.append({
                    "case": case, "seed": seed,
                    "pool": f"{kind}_RANDOM", "rank": rank, "cell": cell,
                })

    auto_candidates = sorted(aes_all)
    _write_list(config / "aes_internal_auto_candidates.list", auto_candidates)
    auto_preview = auto_candidates[:VARIABLE_BUDGET]
    manifests["CASE_AUTO_AES"] = auto_preview
    _write_list(config / "auto_aes_scan.list", auto_preview)
    for rank, cell in enumerate(auto_candidates, start=1):
        candidate_rows.append({
            "case": "CASE_AUTO_AES_CANDIDATE", "seed": "",
            "pool": "AES_ALL_RANKING_INPUT", "rank": rank, "cell": cell,
        })

    # Direct-fault candidate universe includes every cell that can be selected later.
    potential_variable = aes_all | host_noncommon
    raw_sites = _parse_stuck_sites(config / "canonical_faults_all.list")
    instances, _, _ = parse_netlist_instances(checkpoint_dir / "mor1kx_aes_soc_pre_dft.v")
    q_map = cell_q_sites(instances, potential_variable, raw_sites)
    q_rows: list[dict[str, str]] = []
    direct_sites: set[str] = set()
    for cell in sorted(potential_variable):
        sites = q_map[cell]
        direct_sites.update(sites)
        q_rows.append({
            "cell": cell,
            "pool": "AES_ALL_OR_HOST_NONCOMMON",
            "q_sites": ";".join(sites),
            "q_net": instances[cell].get("Q", instances[cell].get("QN", "")),
        })
    with (config / "aes_internal_q_site_manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["cell", "pool", "q_sites", "q_net"])
        writer.writeheader()
        writer.writerows(q_rows)

    with (config / "aes_internal_candidate_manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["case", "seed", "pool", "rank", "cell"])
        writer.writeheader()
        writer.writerows(candidate_rows)

    manifest = {
        "campaign": "aes_internal_d1_d5",
        "checkpoint_ddc_sha256": sha256(checkpoint_dir / "mor1kx_aes_soc_pre_dft.ddc"),
        "checkpoint_verilog_sha256": sha256(checkpoint_dir / "mor1kx_aes_soc_pre_dft.v"),
        "inventory_sha256": sha256(checkpoint_dir / "register_inventory.rpt"),
        "old_common_count": len(old_common),
        "old_common_aes_count": len(old_common & aes_all),
        "old_common_host_count": len(old_common & host_all),
        "aes_all_count": len(aes_all),
        "aes_stage_counts": {stage: len(stage_sets[stage]) for stage in STAGES},
        "aes_non_stage_count": len(aes_nonstage),
        "host_all_count": len(host_all),
        "common_host_count": len(new_common),
        "host_noncommon_count": len(host_noncommon),
        "variable_budget": VARIABLE_BUDGET,
        "total_scan_count": TOTAL_SCAN,
        "chain_count": 1,
        "random_seeds": list(SEEDS),
        "random_selection": "random.Random(seed).sample(sorted(pool), 128), then lexical output order",
        "direct_candidate_cell_count": len(potential_variable),
        "direct_site_count": len(direct_sites),
        "direct_candidate_scope": "AES all candidates plus host cells outside new common",
        "manifest_sha256": {
            "common": sha256(config / "common_scan_aes_internal.list"),
            "iark": sha256(config / "iark_scan_aes_internal.list"),
            "sb": sha256(config / "sb_scan_aes_internal.list"),
            "sr": sha256(config / "sr_scan_aes_internal.list"),
            "mc": sha256(config / "mc_scan_aes_internal.list"),
        },
    }
    (config / "aes_internal_experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    (config / "aes_internal_direct_candidate_sites.list").write_text(
        "\n".join(sorted(direct_sites)) + ("\n" if direct_sites else "")
    )

    # Verify every primary and random case has exactly the fixed variable budget.
    for case, cells in manifests.items():
        if case == "COMMON":
            continue
        if len(cells) != VARIABLE_BUDGET:
            raise AssertionError(f"{case} has {len(cells)} variable cells")
        if common_set & set(cells):
            raise AssertionError(f"{case} intersects the common set")
    return manifests

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = build_candidate_manifests(root)
    summary = {
        "common": len(manifest["COMMON"]),
        "stage": {stage: len(manifest[f"CASE_{stage}"]) for stage in STAGES},
        "random_aes": len([case for case in manifest if case.startswith("CASE_RANDOM_AES_")]),
        "random_host": len([case for case in manifest if case.startswith("CASE_RANDOM_HOST_")]),
        "auto_preview": len(manifest["CASE_AUTO_AES"]),
    }
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
