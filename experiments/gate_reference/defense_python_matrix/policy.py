from __future__ import annotations

from .model import DefenseCondition


def authorize_access(condition: DefenseCondition, authorization: str) -> tuple[bool, str]:
    if condition.authorization == "deny_access" or authorization != "valid":
        return False, "access_denied"
    return True, "access_allowed"


def authorize_query(
    condition: DefenseCondition,
    query_id: int,
    phase: str,
    plaintext_hex: str,
    allowed_manifest: set[str],
) -> tuple[bool, str]:
    if condition.condition_id == "D4" and phase == "phase0" and plaintext_hex not in allowed_manifest:
        return False, "phase0_probe_denied"
    if condition.authorization == "restrict_adaptive" and phase == "adaptive":
        return False, "adaptive_query_denied"
    if phase == "fixed" and plaintext_hex not in allowed_manifest:
        return False, "fixed_query_denied"
    return True, "query_allowed"

