"""Synthetic anonymous scan wrapper for MC leakage-channel discovery."""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from aes_ref import encrypt_with_trace


SCHEDULES = ("mc_capture", "round_register_update", "post_update")
MC_COLUMNS = (
    (0, 5, 10, 15),
    (4, 9, 14, 3),
    (8, 13, 2, 7),
    (12, 1, 6, 11),
)


def key_for_trial(seed: int) -> bytes:
    return hashlib.sha256(f"mc-discovery-key-{seed}".encode()).digest()[:16]


def coarse_plaintexts(base: bytes | None = None, deltas: tuple[int, ...] = (0x01, 0x02, 0x04, 0x08)) -> list[bytes]:
    base = bytes(16) if base is None else bytes(base)
    if len(base) != 16:
        raise ValueError("base plaintext must be 16 bytes")
    points = [base]
    for byte_index in range(16):
        for delta in deltas:
            point = bytearray(base)
            point[byte_index] ^= delta
            points.append(bytes(point))
    return points


def _bit(state: bytes, bit_index: int) -> int:
    return (state[bit_index // 8] >> (bit_index % 8)) & 1


def _source_value(trace: dict, source: dict[str, object], schedule: str) -> int:
    kind = source["kind"]
    if kind == "control":
        return 0
    if kind == "mc":
        if schedule == "mc_capture":
            stage = "MC"
        elif schedule == "round_register_update":
            stage = "ARK"
        else:
            stage = "SB"
    elif kind == "ark":
        if schedule == "mc_capture":
            return 0
        stage = "ARK" if schedule == "round_register_update" else "SB"
    elif kind == "round_register":
        if schedule == "mc_capture":
            return 0
        stage = "ARK" if schedule == "round_register_update" else "SB"
    elif kind == "sb":
        stage = "SB"
    elif kind == "sr":
        stage = "SR"
    else:
        raise ValueError(f"unknown source kind: {kind}")
    return _bit(trace["rounds"][int(source["round"])][stage], int(source["bit_index"]))


def _default_sources(config: dict, rng: random.Random) -> list[dict[str, object]]:
    n_scan_ff = int(config["n_scan_ff"])
    target_count = int(config.get("target_mc_count", 1))
    if target_count < 1:
        raise ValueError("positive trials require at least one MC target")
    mc_bits = rng.sample(range(128), target_count)
    sources: list[dict[str, object]] = []
    for index, bit_index in enumerate(mc_bits):
        sources.append({"source_id": f"mc_target_{index}", "kind": "mc", "stage": "MC", "round": 1, "bit_index": bit_index})
    for kind, count, stage in (
        ("ark", int(config.get("ark_decoys", 16)), "ARK"),
        ("round_register", int(config.get("round_register_decoys", 16)), "ARK"),
        ("sb", int(config.get("sb_decoys", 16)), "SB"),
        ("sr", int(config.get("sr_decoys", 8)), "SR"),
    ):
        for index in range(count):
            sources.append({"source_id": f"{kind}_decoy_{index}", "kind": kind, "stage": stage, "round": 1, "bit_index": rng.randrange(128)})
    remaining = n_scan_ff - len(sources)
    if remaining < 0:
        raise ValueError("decoy counts exceed n_scan_ff")
    for index in range(remaining):
        sources.append({"source_id": f"control_{index}", "kind": "control", "stage": "CONTROL", "round": 0, "bit_index": 0})
    return sources


def _render(seed: int, config: dict, key: bytes, sources: list[dict[str, object]], permutation: list[int], points: list[bytes], trial_id: str) -> tuple[dict, dict]:
    traces = [encrypt_with_trace(point, key) for point in points]
    idle_bits = [0] * len(sources)
    observations = []
    for schedule in SCHEDULES:
        observations.append({"query_id": -1, "plaintext_hex": points[0].hex(), "schedule": "idle", "capture_schedule": schedule, "aes_started": False, "scan_bits": idle_bits})
    for query_id, point in enumerate(points):
        for schedule in SCHEDULES:
            values = [_source_value(traces[query_id], sources[source_index], schedule) for source_index in permutation]
            observations.append({"query_id": query_id, "plaintext_hex": point.hex(), "schedule": schedule, "capture_schedule": schedule, "aes_started": True, "scan_bits": values})
    anonymous = {
        "schema": "anonymous-scan-trial-v1",
        "trial_id": trial_id,
        "scan_slot_count": len(sources),
        "schedule_order": list(SCHEDULES),
        "plaintexts": [{"query_id": index, "plaintext_hex": point.hex()} for index, point in enumerate(points)],
        "observations": observations,
    }
    source_by_slot = [sources[source_index] for source_index in permutation]
    ground_truth = {
        "schema": "scan-trial-ground-truth-v1",
        "trial_id": trial_id,
        "seed": seed,
        "key_hex": key.hex(),
        "scan_permutation": permutation,
        "scan_sources": [{**source, "scan_slot": slot} for slot, source in enumerate(source_by_slot)],
        "target_mc_slots": [slot for slot, source in enumerate(source_by_slot) if source["kind"] == "mc"],
        "control_slots": [slot for slot, source in enumerate(source_by_slot) if source["kind"] == "control"],
    }
    return anonymous, ground_truth


def build_trial(seed: int, config: dict) -> tuple[dict, dict]:
    rng = random.Random(seed)
    key = key_for_trial(seed)
    sources = _default_sources(config, rng)
    permutation = list(range(len(sources)))
    rng.shuffle(permutation)
    points = coarse_plaintexts()
    return _render(seed, config, key, sources, permutation, points, f"trial-{seed}")


def build_holdout(seed: int, config: dict, ground_truth: dict, count: int = 24) -> dict:
    rng = random.Random(seed * 1009 + 31)
    points = [bytes(16)]
    seen = {points[0]}
    while len(points) < count + 1:
        point = bytes(rng.randrange(256) for _ in range(16))
        if point not in seen:
            points.append(point)
            seen.add(point)
    sources = [{key: value for key, value in source.items() if key != "scan_slot"} for source in ground_truth["scan_sources"]]
    permutation = list(range(len(sources)))
    for slot, source in enumerate(ground_truth["scan_sources"]):
        permutation[slot] = int(ground_truth["scan_permutation"][slot])
    anonymous, _ = _render(seed, config, bytes.fromhex(ground_truth["key_hex"]), sources, permutation, points, f"holdout-{seed}")
    return anonymous


def write_trial(directory: str | Path, anonymous: dict, ground_truth: dict) -> None:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{anonymous['trial_id']}.anonymous.json").write_text(__import__("json").dumps(anonymous, indent=2) + "\n")
    (root / f"{anonymous['trial_id']}.ground_truth.json").write_text(__import__("json").dumps(ground_truth, indent=2) + "\n")
