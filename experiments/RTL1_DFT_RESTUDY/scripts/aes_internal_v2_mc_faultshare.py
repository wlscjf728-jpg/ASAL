#!/usr/bin/env python3
"""Create fixed-size fault populations that exchange SB faults for MC faults.

The DFT/scan configuration is intentionally outside this script.  Every output
level has the same number of source entries and the same non-SB/non-MC strata;
only the SB-versus-MC allocation changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
REGION_ORDER = ("IARK_CONE", "SB_CONE", "SR_CONE", "MC_CONE", "AES_CONTROL", "AES_OTHER")
EXCHANGEABLE = ("SB_CONE", "MC_CONE")
TOTAL_ENTRIES = 4000
FIXED_COUNTS = {"IARK_CONE": 107, "SR_CONE": 59, "AES_CONTROL": 0, "AES_OTHER": 312}
# 314/4000 is the natural MC share rounded from the valid-source distribution.
MC_COUNTS = (314, 800, 1600, 2400, 3200)
SEED = 20260903
FAULT_RE = re.compile(r"^\s*(sa[01]|str|stf)\s+(\S+)\s+(\S+)")


def normalize(site: str) -> str:
    return site.lstrip("\\")


def ranked(lines: list[str], region: str) -> list[str]:
    return sorted(
        lines,
        key=lambda line: hashlib.sha256(f"{SEED}:faultshare:{region}:{line}".encode()).hexdigest(),
    )


def main() -> None:
    metadata = json.loads((CONFIG / "aes_internal_v2_region_metadata.json").read_text())
    region_sites = {
        name: {normalize(site) for site in metadata["regions"].get(name, [])}
        for name in REGION_ORDER
    }
    manifest: dict[str, object] = {
        "revision": 1,
        "design": "AES-internal fixed-size SB-to-MC fault-share sweep",
        "scan_manifests_unchanged": True,
        "source_entries_per_level": TOTAL_ENTRIES,
        "direct_ff_excluded_by_source": True,
        "selection": "deterministic SHA256 ranking within each structural region",
        "seed": SEED,
        "fixed_regions": FIXED_COUNTS,
        "exchange": "SB_CONE entries are removed as MC_CONE entries are added",
        "levels": {},
    }

    for mode in ("stuck", "transition"):
        source = CONFIG / f"aes_internal_v2_raw_{mode}.list"
        candidates = {name: [] for name in REGION_ORDER}
        for line in source.read_text().splitlines():
            match = FAULT_RE.match(line)
            if not match:
                continue
            site = normalize(match.group(3))
            region = next((name for name in REGION_ORDER if site in region_sites[name]), None)
            if region is not None:
                candidates[region].append(line)
        ordered = {name: ranked(candidates[name], name) for name in REGION_ORDER}

        source_manifest: dict[str, object] = {}
        for mc_count in MC_COUNTS:
            sb_count = TOTAL_ENTRIES - sum(FIXED_COUNTS.values()) - mc_count
            if sb_count < 0:
                raise ValueError(f"negative SB count for MC={mc_count}")
            counts = dict(FIXED_COUNTS)
            counts.update({"SB_CONE": sb_count, "MC_CONE": mc_count})
            if sum(counts.values()) != TOTAL_ENTRIES:
                raise AssertionError(counts)

            selected: list[str] = []
            for region in REGION_ORDER:
                count = counts[region]
                if count > len(ordered[region]):
                    raise ValueError(f"{mode} {region}: need {count}, have {len(ordered[region])}")
                selected.extend(ordered[region][:count])

            label = f"mc{mc_count:04d}"
            output = CONFIG / f"aes_internal_v2_faultshare_{label}_{mode}.list"
            output.write_text("\n".join(selected) + "\n")
            source_manifest[label] = {
                "counts": counts,
                "source_entries": len(selected),
                "mc_fraction_pct": round(100.0 * mc_count / TOTAL_ENTRIES, 3),
                "sb_fraction_pct": round(100.0 * sb_count / TOTAL_ENTRIES, 3),
                "output": str(output),
                "candidate_entries": {name: len(ordered[name]) for name in REGION_ORDER},
            }
        manifest["levels"][mode] = source_manifest

    (CONFIG / "aes_internal_v2_mc_faultshare_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
