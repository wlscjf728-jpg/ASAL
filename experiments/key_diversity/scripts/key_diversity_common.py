"""Shared deterministic inputs and attack/evaluator boundary helpers."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text())


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n")
    temporary.replace(path)


def key_for_original_seed(seed: int) -> bytes:
    return hashlib.sha256(f"oracle-key-{seed}".encode()).digest()[:16]


def generate_new_key_rows(generation_seed: int, count: int) -> list[dict[str, str]]:
    """Generate reproducible keys while excluding the original seed keys."""
    original = {key_for_original_seed(seed).hex() for seed in (0, 1, 2)}
    rows: list[dict[str, str]] = []
    seen = set(original)
    index = 0
    while len(rows) < count:
        key = hashlib.sha256(
            f"asal-key-diversity-{generation_seed}-{index}".encode()
        ).digest()[:16]
        index += 1
        key_hex = key.hex()
        if key_hex in seen:
            continue
        seen.add(key_hex)
        rows.append({
            "key_id": f"K{len(rows) + 1:02d}",
            "key_hex": key_hex,
            "key_sha256": hashlib.sha256(key).hexdigest(),
            "generation_seed": str(generation_seed),
            "generation_index": str(index - 1),
            "evaluator_only": "true",
        })
    return rows


def nested_plaintexts(query_count: int, query_seed: int) -> list[bytes]:
    """Reproduce the existing nested one-byte schedule with one shared seed."""
    rng = random.Random(query_seed * 65537 + 17)
    base = bytes(16)
    points = [base]
    seen = {base}
    while len(points) <= query_count:
        point = bytearray(16)
        point[rng.randrange(16)] = rng.randrange(1, 256)
        encoded = bytes(point)
        if encoded not in seen:
            points.append(encoded)
            seen.add(encoded)
    return points


def query_schedule_sha256(query_seed: int, max_query_count: int) -> str:
    payload = b"".join(nested_plaintexts(max_query_count, query_seed))
    return hashlib.sha256(payload).hexdigest()


def load_taps(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 4 or len({row["tap_id"] for row in rows}) != 4:
        raise ValueError("representative tap manifest must contain four unique taps")
    for row in rows:
        if row["stage"] != "MC":
            raise ValueError(f"non-MC representative tap: {row}")
    return rows


def load_keys(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 20 or len({row["key_id"] for row in rows}) != 20:
        raise ValueError("evaluator key manifest must contain twenty unique keys")
    key_hexes = [row["key_hex"] for row in rows]
    if len(set(key_hexes)) != 20 or any(len(value) != 32 for value in key_hexes):
        raise ValueError("evaluator keys must be twenty unique 128-bit values")
    original = {key_for_original_seed(seed).hex() for seed in (0, 1, 2)}
    if original.intersection(key_hexes):
        raise ValueError("new evaluator keys overlap original seed keys")
    return rows


def sanitize_for_solver(document: dict[str, Any]) -> dict[str, Any]:
    """Remove evaluator-only key material before the document reaches Z3."""
    sanitized = json.loads(json.dumps(document))

    def scrub(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("true_key_hex", None)
            for child in value.values():
                scrub(child)
        elif isinstance(value, list):
            for child in value:
                scrub(child)

    scrub(sanitized)
    sanitized.setdefault("evaluator", {})["true_key_removed"] = True
    return sanitized


def classify_pair(first_result: str, second_result: str) -> str:
    first = first_result.lower()
    second = second_result.lower()
    if first == "sat" and second == "unsat":
        return "unique"
    if first == "sat" and second == "sat":
        return "ambiguity"
    return "unresolved"


def is_sat_sat(result: dict[str, Any]) -> bool:
    return result.get("first_result") == "sat" and result.get("second_result") == "sat"


def is_sat_unsat(result: dict[str, Any]) -> bool:
    return result.get("first_result") == "sat" and result.get("second_result") == "unsat"

