from __future__ import annotations

import hashlib
import random
from typing import Any

from .model import DefenseCondition


SCAN_CELLS = 256
TARGET_SLOT = 255
STATE_DECOY_SLOT = 240
ROUND_DECOY_SLOT = 1
FULL_MASK = (1 << SCAN_CELLS) - 1


def _mask_bit(condition_id: str, query_id: int, schedule: int) -> int:
    payload = f"{condition_id}:{query_id}:{schedule}".encode()
    return hashlib.sha256(payload).digest()[0] & 1


def _permutation(condition_id: str, query_id: int = 0) -> list[int]:
    seed_bytes = hashlib.sha256(f"python-defense:{condition_id}:{query_id}".encode()).digest()
    seed = int.from_bytes(seed_bytes[:8], "big")
    result = list(range(SCAN_CELLS))
    random.Random(seed).shuffle(result)
    return result


def _permute(vector: int, condition_id: str, query_id: int) -> int:
    permutation = _permutation(condition_id, query_id)
    output = 0
    for output_slot, input_slot in enumerate(permutation):
        output |= ((vector >> input_slot) & 1) << output_slot
    return output


def _hide(vector: int, condition_id: str, query_id: int, schedule: int) -> int:
    payload = f"{condition_id}:{query_id}:{schedule}:{vector:064x}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def apply_observation_transform(
    vector: int,
    condition: DefenseCondition,
    query_id: int,
    schedule: int,
) -> int:
    """Return the scan vector visible to the attacker for one capture."""
    vector &= FULL_MASK
    transform = condition.transform
    if transform == "identity":
        return vector
    if transform == "state_only":
        return vector & ~(1 << STATE_DECOY_SLOT)
    if transform in {"clear_post_mc", "reset_capture"}:
        return vector & ~(1 << TARGET_SLOT)
    if transform == "round_mask_only":
        if schedule == 2 and _mask_bit(condition.condition_id, query_id, schedule):
            vector ^= 1 << ROUND_DECOY_SLOT
        return vector
    if transform == "round_and_mc_mask":
        if _mask_bit(condition.condition_id, query_id, schedule):
            vector ^= 1 << (TARGET_SLOT if schedule in (1, 2) else ROUND_DECOY_SLOT)
        return vector
    if transform == "static_permutation":
        return _permute(vector, condition.condition_id, 0)
    if transform == "fixed_inversion":
        return vector ^ FULL_MASK
    if transform == "epoch_permutation":
        return _permute(vector, condition.condition_id, query_id // 8)
    if transform == "probe_permutation":
        return _permute(vector, condition.condition_id, query_id)
    if transform == "response_hide":
        return _hide(vector, condition.condition_id, query_id, schedule)
    raise ValueError(f"unsupported transform: {transform}")


def apply_differential_transform(
    bit: int,
    condition: DefenseCondition,
    query_id: int,
    schedule: int,
) -> int:
    """Apply a representative defense to an already selected bit.

    This helper is used for unit-level adapter checks. Full scan-bank runs use
    ``apply_observation_transform`` so permutations and response hiding operate
    on the complete anonymous vector.
    """
    bit = int(bit) & 1
    if condition.transform in {"clear_post_mc", "reset_capture"}:
        return 0
    if condition.transform == "round_mask_only" and schedule == 2:
        return bit ^ _mask_bit(condition.condition_id, query_id, schedule)
    if condition.transform == "round_and_mc_mask":
        return bit ^ _mask_bit(condition.condition_id, query_id, schedule)
    if condition.transform == "fixed_inversion":
        return bit ^ 1
    if condition.transform == "response_hide":
        return _hide(bit, condition.condition_id, query_id, schedule) & 1
    return bit



def transform_capture(rows: list[dict[str, Any]], condition: DefenseCondition) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Transform anonymous scan rows and return a non-sensitive audit log."""
    transformed = []
    audit = []
    for row in rows:
        query_id = int(row["query_id"])
        schedule = int(row["capture_schedule"])
        vector = int(str(row["scan_vector_hex"]), 16)
        visible = apply_observation_transform(vector, condition, query_id, schedule)
        transformed.append({
            "query_id": query_id,
            "capture_schedule": schedule,
            "scan_vector_hex": f"{visible:064x}",
        })
        audit.append({
            "query_id": query_id,
            "capture_schedule": schedule,
            "transform": condition.transform,
            "visible_width": SCAN_CELLS,
        })
    return transformed, audit
