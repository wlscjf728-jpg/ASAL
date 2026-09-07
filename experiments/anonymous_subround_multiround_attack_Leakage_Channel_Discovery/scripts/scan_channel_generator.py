"""Public generator API with anonymous schema and held-out slot preservation."""
from __future__ import annotations

import random

import scan_channel_generator_legacy as _legacy

MC_COLUMNS = _legacy.MC_COLUMNS
SCHEDULES = _legacy.SCHEDULES
coarse_plaintexts = _legacy.coarse_plaintexts
key_for_trial = _legacy.key_for_trial


def build_trial(seed: int, config: dict) -> tuple[dict, dict]:
    anonymous, ground_truth = _legacy.build_trial(seed, config)
    anonymous["scan_slots"] = list(range(int(anonymous["scan_slot_count"])))
    return anonymous, ground_truth


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
    anonymous, _ = _legacy._render(seed, config, bytes.fromhex(ground_truth["key_hex"]), sources, list(range(len(sources))), points, f"holdout-{seed}")
    anonymous["scan_slots"] = list(range(int(anonymous["scan_slot_count"])))
    return anonymous


def write_trial(directory, anonymous: dict, ground_truth: dict) -> None:
    return _legacy.write_trial(directory, anonymous, ground_truth)
