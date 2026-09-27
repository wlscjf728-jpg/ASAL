from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


EXTRA_EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTRA_EXP / "scripts"))
import semantic_reference as sr  # noqa: E402


TARGET_SLOT = 255
TARGET_BIT = 9
STATE_DECOY_SLOT = 240
SCHEDULES = (1, 2, 3)


def _plaintexts(rows: list[dict[str, Any]]) -> list[bytes]:
    result = []
    for row in rows:
        value = bytes.fromhex(str(row["plaintext_hex"]))
        if len(value) != 16:
            raise ValueError("Phase 0 plaintext must be 16 bytes")
        result.append(value)
    return result


def _target_value(plaintext: bytes, key: bytes, schedule: int) -> int:
    if schedule == 1:
        return sr.mc_bit(plaintext, key, 1, TARGET_BIT)
    if schedule == 2:
        return 0
    if schedule == 3:
        return sr.mc_bit(plaintext, key, 2, TARGET_BIT)
    raise ValueError(f"unsupported capture schedule: {schedule}")


def _state_register_value(plaintext: bytes, key: bytes) -> int:
    mc = sr.mc_state_at_round(plaintext, key, 1)
    round_key = sr.expand_key(key)[1]
    state = bytes(left ^ right for left, right in zip(mc, round_key))
    return (state[TARGET_BIT // 8] >> (TARGET_BIT % 8)) & 1


def _capture(queries: list[dict[str, Any]], key: bytes, started: bool) -> list[dict[str, Any]]:
    points = _plaintexts(queries)
    rows: list[dict[str, Any]] = []
    for query_id, plaintext in enumerate(points):
        for schedule in SCHEDULES:
            vector = 1  # Stable non-AES decoy cell; it vanishes in differential views.
            if started:
                vector |= _target_value(plaintext, key, schedule) << TARGET_SLOT
                if schedule in (2, 3):
                    vector |= _state_register_value(plaintext, key) << STATE_DECOY_SLOT
            rows.append({
                "query_id": query_id,
                "capture_schedule": schedule,
                "scan_vector_hex": f"{vector:064x}",
            })
    return rows


def build_scan_bank(queries: list[dict[str, Any]], key: bytes, target_bit: int = TARGET_BIT, scan_cells: int = 256) -> dict[str, Any]:
    if len(key) != 16:
        raise ValueError("AES-128 key must be 16 bytes")
    if target_bit != TARGET_BIT or scan_cells != 256:
        raise ValueError("the frozen Python fixture uses MC bit 9 in a 256-cell bank")
    if not queries:
        raise ValueError("scan bank requires at least one query")
    attack = _capture(queries, key, started=True)
    repeat = _capture(queries[:1], key, started=True) + _capture(queries[:1], key, started=True)
    no_start = _capture(queries[:1], key, started=False)
    return {
        "attack": attack,
        "repeat": repeat,
        "no_start": no_start,
        "evaluator": {
            "target_slot": TARGET_SLOT,
            "target_bit": TARGET_BIT,
            "target_stage": "MC",
            "scan_cells": scan_cells,
            "mapping": {str(TARGET_SLOT): "evaluator-only-target"},
        },
    }


def write_attack_capture(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{int(row['query_id'])} {int(row['capture_schedule'])} {row['scan_vector_hex']}"
        for row in rows
    ]
    path.write_text("\n".join(lines) + "\n")

