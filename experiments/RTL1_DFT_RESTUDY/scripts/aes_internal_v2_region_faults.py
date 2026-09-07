#!/usr/bin/env python3
"""Partition the revision-2 AES-internal source by structural cone region."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
REGIONS = ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "AES_CONTROL", "AES_OTHER")
FAULT_RE = re.compile(r"^\s*(sa[01]|str|stf)\s+(\S+)\s+(\S+)")


def normalize(site: str) -> str:
    return site.lstrip("\\")


def main() -> None:
    metadata = json.loads((CONFIG / "aes_internal_v2_region_metadata.json").read_text())
    region_sites = {name: {normalize(site) for site in metadata["regions"].get(name, [])} for name in REGIONS}
    direct = {normalize(line.split()[-1]) for line in (CONFIG / "aes_internal_v2_direct_sites.list").read_text().splitlines() if line.strip()}
    output = {"revision": 2, "direct_exclusion_used": True, "regions": {}}
    for mode in ("stuck", "transition"):
        source = CONFIG / f"aes_internal_v2_raw_{mode}.list"
        lines = {name: [] for name in REGIONS}
        for line in source.read_text().splitlines():
            match = FAULT_RE.match(line)
            if not match:
                continue
            site = normalize(match.group(3))
            if site in direct:
                continue
            region = next((name for name in REGIONS if site in region_sites[name]), None)
            if region is not None:
                lines[region].append(line)
        output["regions"][mode] = {}
        for region, region_lines in lines.items():
            path = CONFIG / "aes_internal_v2_region_faults" / mode / f"{region}.list"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(region_lines) + ("\n" if region_lines else ""))
            output["regions"][mode][region] = {"line_count": len(region_lines), "path": str(path)}
    (CONFIG / "aes_internal_v2_region_fault_manifest.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
