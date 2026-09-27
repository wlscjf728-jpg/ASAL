#!/usr/bin/env python3
"""Fault-source filtering helpers for the AES-internal campaign."""

from __future__ import annotations


FAULT_KINDS = {"sa0", "sa1", "str", "stf"}


def _site_from_line(line: str) -> str | None:
    fields = line.split()
    if len(fields) < 3 or fields[0] not in FAULT_KINDS:
        return None
    return fields[2]


def filter_fault_line(
    line: str, allowed_prefixes: set[str], excluded_sites: set[str]
) -> str | None:
    site = _site_from_line(line)
    if site is None:
        return None
    normalized = site.lstrip("\\")
    prefixes = {prefix.lstrip("\\") for prefix in allowed_prefixes}
    if not any(normalized.startswith(prefix) for prefix in prefixes):
        return None
    if normalized.startswith(("aes_result_o", "aes_done_o")):
        return None
    excluded = {candidate.lstrip("\\") for candidate in excluded_sites}
    if normalized in excluded or site in excluded_sites:
        return None
    return line.strip()


def build_direct_exclusion_lines(sites: set[str], kind: str) -> list[str]:
    normalized = sorted({site.lstrip("\\") for site in sites})
    if kind == "stuck":
        prefixes = ("sa0", "sa1")
    elif kind == "transition":
        prefixes = ("str", "stf")
    else:
        raise ValueError(f"unsupported fault kind: {kind}")
    return [f"{prefix} NC {site}" for site in normalized for prefix in prefixes]
