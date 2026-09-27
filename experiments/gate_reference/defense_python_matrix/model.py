from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TRANSFORMS = {
    "identity",
    "state_only",
    "clear_post_mc",
    "reset_capture",
    "round_mask_only",
    "round_and_mc_mask",
    "static_permutation",
    "fixed_inversion",
    "epoch_permutation",
    "probe_permutation",
    "response_hide",
}
AUTHORIZATIONS = {"allow", "deny_access", "restrict_adaptive"}


@dataclass(frozen=True)
class DefenseCondition:
    condition_id: str
    family: str
    description: str
    transform: str
    authorization: str
    secret_id: str | None
    adaptive_allowed: bool
    expected_boundary: str


@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    reason: str = ""
    details: dict[str, Any] | None = None


def condition_from_config(payload: dict[str, Any]) -> DefenseCondition:
    required = {
        "condition_id", "family", "description", "transform", "authorization",
        "secret_id", "adaptive_allowed", "expected_boundary",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"missing condition fields: {sorted(missing)}")
    transform = str(payload["transform"])
    if transform not in TRANSFORMS:
        raise ValueError(f"unknown transform: {transform}")
    authorization = str(payload["authorization"])
    if authorization not in AUTHORIZATIONS:
        raise ValueError(f"unknown authorization: {authorization}")
    secret = payload["secret_id"]
    if secret is not None:
        secret = str(secret)
    return DefenseCondition(
        condition_id=str(payload["condition_id"]),
        family=str(payload["family"]),
        description=str(payload["description"]),
        transform=transform,
        authorization=authorization,
        secret_id=secret,
        adaptive_allowed=bool(payload["adaptive_allowed"]),
        expected_boundary=str(payload["expected_boundary"]),
    )


def load_conditions(path: Path) -> list[DefenseCondition]:
    payload = json.loads(path.read_text())
    raw_conditions = payload.get("conditions")
    if not isinstance(raw_conditions, list):
        raise ValueError("config must contain a conditions list")
    conditions = [condition_from_config(item) for item in raw_conditions]
    ids = [item.condition_id for item in conditions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate condition_id")
    return conditions

