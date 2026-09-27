#!/usr/bin/env python3
"""Build the revision-2 AES-internal raw fault sources."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
STUCK_KINDS = {"sa0", "sa1"}
TRANSITION_KINDS = {"str", "stf"}


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_site(site: str) -> str:
    return site.lstrip("\\")


def is_interface_site(site: str) -> bool:
    plain = normalize_site(site)
    return plain.startswith(("aes_result_o", "aes_done_o")) or plain.endswith("/aes_result_o") or plain.endswith("/aes_done_o")


def is_aes_internal_site(site: str) -> bool:
    plain = normalize_site(site)
    return plain.startswith("u_aes_peripheral/") and not is_interface_site(site)


def is_direct_variable_site(site: str, direct_sites: set[str]) -> bool:
    normalized = normalize_site(site)
    return normalized in {normalize_site(candidate) for candidate in direct_sites}


def _parse_direct_sites(path: Path) -> set[str]:
    return set(read_lines(path))


def _filter_source(path: Path, allowed_kinds: set[str], direct_sites: set[str]) -> tuple[list[str], Counter[str], set[str]]:
    accepted: list[str] = []
    status_counts: Counter[str] = Counter()
    sites: set[str] = set()
    direct_normalized = {normalize_site(site) for site in direct_sites}
    for line in read_lines(path):
        fields = line.split()
        if len(fields) < 3 or fields[0] not in allowed_kinds:
            continue
        kind, status, site = fields[:3]
        if not is_aes_internal_site(site):
            continue
        if normalize_site(site) in direct_normalized:
            continue
        accepted.append(f"{kind} {status} {site}")
        status_counts[status] += 1
        sites.add(normalize_site(site))
    if len(accepted) != len(set(accepted)):
        # Repeated records are not useful as a source and can change TetraMAX's
        # loaded count in a way that is not shared across fault models.
        accepted = sorted(set(accepted))
    return accepted, status_counts, sites


def _restrict_to_sites(lines: list[str], sites: set[str]) -> tuple[list[str], Counter[str]]:
    kept: list[str] = []
    statuses: Counter[str] = Counter()
    for line in lines:
        fields = line.split()
        if len(fields) < 3 or normalize_site(fields[2]) not in sites:
            continue
        kept.append(line)
        statuses[fields[1]] += 1
    return kept, statuses


def build_direct_exclusion(direct_sites: set[str]) -> dict[str, int]:
    ordered = sorted(direct_sites, key=normalize_site)
    stuck = [f"sa{pol} NC {site}" for site in ordered for pol in (0, 1)]
    transition = [f"st{pol} NC {site}" for site in ordered for pol in ("r", "f")]
    (CONFIG / "aes_internal_v2_direct_exclusion_stuck.list").write_text("\n".join(stuck) + "\n")
    (CONFIG / "aes_internal_v2_direct_exclusion_transition.list").write_text("\n".join(transition) + "\n")
    return {"direct_site_count": len(ordered), "stuck_lines": len(stuck), "transition_lines": len(transition)}


def build_collapsed_source(reference_fault_path: Path, output_path: Path, allowed_sites: set[str]) -> int:
    """Extract fresh NC representatives from a reference source, never 422 history."""
    allowed = {normalize_site(site) for site in allowed_sites}
    records: set[str] = set()
    for line in read_lines(reference_fault_path):
        fields = line.split()
        if len(fields) < 3 or fields[0] not in STUCK_KINDS or fields[1] != "NC":
            continue
        site = fields[2]
        if normalize_site(site) in allowed and is_aes_internal_site(site):
            records.add(f"{fields[0]} NC {site}")
    output_path.write_text("\n".join(sorted(records)) + ("\n" if records else ""))
    return len(records)


def build_sources(root: Path = ROOT) -> dict[str, object]:
    config = root / "config"
    direct_sites = _parse_direct_sites(config / "aes_internal_v2_direct_sites.list")
    stuck, stuck_status, stuck_sites = _filter_source(config / "canonical_faults_all.list", STUCK_KINDS, direct_sites)
    transition, transition_status, transition_sites = _filter_source(config / "transition_faults_all.list", TRANSITION_KINDS, direct_sites)
    common_sites = stuck_sites & transition_sites
    if not common_sites:
        raise ValueError("AES-internal raw fault source is empty")
    stuck, stuck_status = _restrict_to_sites(stuck, common_sites)
    transition, transition_status = _restrict_to_sites(transition, common_sites)
    stuck_sites = set(common_sites)
    transition_sites = set(common_sites)
    (config / "aes_internal_v2_raw_stuck.list").write_text("\n".join(stuck) + "\n")
    (config / "aes_internal_v2_raw_transition.list").write_text("\n".join(transition) + "\n")
    allowed_sites = common_sites
    collapsed_count = build_collapsed_source(
        config / "canonical_faults_all.list",
        config / "aes_internal_v2_collapsed_stuck.list",
        allowed_sites,
    )
    status = "PASS" if collapsed_count else "UNRESOLVED_NO_AES_INTERNAL_NC_IN_REFERENCE"
    manifest = {
        "revision": 2,
        "scope": "AES internal sites under u_aes_peripheral, excluding output interface and all AES FF Q/QN sites",
        "historical_422_used": False,
        "direct_site_count": len(direct_sites),
        "direct_exclusion": build_direct_exclusion(direct_sites),
        "stuck_raw_line_count": len(stuck),
        "transition_raw_line_count": len(transition),
        "stuck_pre_alignment_site_count": len(stuck_sites),
        "transition_pre_alignment_site_count": len(transition_sites),
        "common_aligned_site_count": len(common_sites),
        "stuck_raw_site_count": len(stuck_sites),
        "transition_raw_site_count": len(transition_sites),
        "stuck_status_counts": dict(stuck_status),
        "transition_status_counts": dict(transition_status),
        "stuck_source_sha256": digest(config / "aes_internal_v2_raw_stuck.list"),
        "transition_source_sha256": digest(config / "aes_internal_v2_raw_transition.list"),
        "collapsed_source_count": collapsed_count,
        "collapsed_status": status,
        "reference_source": str(config / "canonical_faults_all.list"),
        "reference_source_sha256": digest(config / "canonical_faults_all.list"),
    }
    (config / "aes_internal_v2_fault_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    print(json.dumps(build_sources(), indent=2))


if __name__ == "__main__":
    main()
