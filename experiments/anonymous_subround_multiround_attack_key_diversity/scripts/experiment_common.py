"""Compatibility surface required by the copied Attack 8 solver modules."""
from __future__ import annotations

import hashlib

from key_diversity_common import (  # noqa: F401
    ROOT,
    append_jsonl,
    nested_plaintexts,
    read_csv,
    write_csv,
)


def key_for_seed(seed: int) -> bytes:
    return hashlib.sha256(f"oracle-key-{seed}".encode()).digest()[:16]


def load_candidate_map(path=None):
    source = path or ROOT / "reference/candidate_map_extended512.csv"
    return {row["candidate_id"]: row for row in read_csv(source)}


def taps_for_case(row, candidate_map):
    taps = []
    for index, name in enumerate(("cand_a", "cand_b", "cand_c", "cand_d")):
        candidate_id = row.get(name)
        if not candidate_id:
            continue
        candidate = candidate_map[candidate_id]
        taps.append({
            "tap_id": f"t{index}",
            "candidate_id": candidate_id,
            "stage": candidate["stage"],
            "bit_index": int(candidate["bit_index"]),
        })
    return taps
