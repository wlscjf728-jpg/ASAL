"""Shared Attack 8 case, tap, plaintext, and result helpers."""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_ROOT = ROOT.parent
PHASE7 = EXPERIMENTS_ROOT / "multibit_baselines"
PHASE7_1 = EXPERIMENTS_ROOT / "multibit_hard_cases"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def load_candidate_map(path: Path | None = None) -> dict[str, dict[str, str]]:
    source = path or ROOT / "reference" / "candidate_map_extended512.csv"
    return {row["candidate_id"]: row for row in read_csv(source)}


def case_candidates(row: dict[str, str]) -> list[str]:
    return [row[name] for name in ("cand_a", "cand_b", "cand_c", "cand_d") if row.get(name)]


def taps_for_case(row: dict[str, str], candidate_map: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    taps = []
    for index, candidate_id in enumerate(case_candidates(row)):
        candidate = candidate_map[candidate_id]
        taps.append({
            "tap_id": f"t{index}",
            "candidate_id": candidate_id,
            "stage": candidate["stage"],
            "bit_index": int(candidate["bit_index"]),
        })
    return taps


def key_for_seed(seed: int) -> bytes:
    return hashlib.sha256(f"oracle-key-{seed}".encode()).digest()[:16]


def nested_plaintexts(query_count: int, seed: int) -> list[bytes]:
    """Reproduce Phase 7 nested one-byte differentials, including the zero base."""
    rng = random.Random(seed * 65537 + 17)
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


def proof_class(row: dict[str, str]) -> str:
    first = row.get("first_result", "").lower()
    second = row.get("second_result", "").lower()
    if first == "sat" and second == "unsat":
        return "unique"
    if first == "sat" and second == "sat":
        return "ambiguity"
    return "unresolved"


def canonical_case_id(row: dict[str, str]) -> str:
    return row.get("pair_id") or row["case_id"]
