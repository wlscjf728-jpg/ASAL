#!/usr/bin/env python3
"""Create a deterministic, equal-weight four-stage-cone fault universe."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
REGIONS = ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE")
PER_REGION = 1000
FAULT_RE = re.compile(r"^\s*(sa[01]|str|stf)\s+(\S+)\s+(\S+)")


def normalize(site: str) -> str:
    return site.lstrip("\\")


def main() -> None:
    metadata = json.loads((CONFIG / "aes_internal_v2_region_metadata.json").read_text())
    region_sites = {name: {normalize(site) for site in metadata["regions"].get(name, [])} for name in REGIONS}
    manifest: dict[str, object] = {
        "revision": 2,
        "design": "AES-internal balanced four-stage-cone fault universe",
        "regions": list(REGIONS),
        "per_region_entries": PER_REGION,
        "selection": "sort by SHA256(seed:region:source_line) and retain first 1000",
        "seed": 20260903,
        "direct_ff_excluded_by_source": True,
        "modes": {},
    }
    for mode in ("stuck", "transition"):
        source = CONFIG / f"aes_internal_v2_raw_{mode}.list"
        candidates = {name: [] for name in REGIONS}
        for line in source.read_text().splitlines():
            match = FAULT_RE.match(line)
            if not match:
                continue
            site = normalize(match.group(3))
            region = next((name for name in REGIONS if site in region_sites[name]), None)
            if region is not None:
                candidates[region].append(line)
        selected: list[str] = []
        mode_info: dict[str, object] = {}
        for region in REGIONS:
            ranked = sorted(candidates[region], key=lambda line: hashlib.sha256(f"20260903:{region}:{line}".encode()).hexdigest())
            if len(ranked) < PER_REGION:
                raise ValueError(f"{mode} {region} has only {len(ranked)} entries")
            chosen = ranked[:PER_REGION]
            selected.extend(chosen)
            mode_info[region] = {"candidate_entries": len(ranked), "selected_entries": len(chosen), "selected_sites": len({normalize(line.split()[2]) for line in chosen})}
        out = CONFIG / f"aes_internal_v2_balanced4_{mode}.list"
        out.write_text("\n".join(selected) + "\n")
        mode_info["total_selected_entries"] = len(selected)
        mode_info["output"] = str(out)
        manifest["modes"][mode] = mode_info
    (CONFIG / "aes_internal_v2_balanced4_fault_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
