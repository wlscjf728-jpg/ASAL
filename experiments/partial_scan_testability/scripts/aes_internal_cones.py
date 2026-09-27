#!/usr/bin/env python3
"""Sequential-boundary-aware region helpers."""

from __future__ import annotations


def classify_aes_region(site: str, metadata: dict[str, set[str]]) -> str:
    control = set().union(
        metadata.get("clock_sites", set()),
        metadata.get("reset_sites", set()),
        metadata.get("scan_enable_sites", set()),
    )
    if site in control:
        return "UNRESOLVED"
    for key, label in (
        ("iark_cone_sites", "IARK_CONE"),
        ("sb_cone_sites", "SB_CONE"),
        ("sr_cone_sites", "SR_CONE"),
        ("mc_cone_sites", "MC_CONE"),
        ("aes_control_sites", "AES_CONTROL"),
        ("aes_other_sites", "AES_OTHER"),
    ):
        if site in metadata.get(key, set()):
            return label
    return "UNRESOLVED"
