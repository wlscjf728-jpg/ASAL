"""Held-out validation plus diagnostic joint-byte probe."""
from __future__ import annotations

from discover_mc_channel import differential_signatures
from refine_mc_channel_legacy import evaluate_candidate as _evaluate_candidate
import scan_channel_generator_legacy as _legacy


def _joint_probe(seed: int, ground_truth: dict, slot: int) -> bool:
    sources = [{key: value for key, value in source.items() if key != "scan_slot"} for source in ground_truth["scan_sources"]]
    base = bytes(16)
    a = bytearray(base)
    b = bytearray(base)
    a[0] = 1
    b[1] = 1
    ab = bytes(x ^ y for x, y in zip(a, b))
    probe, _ = _legacy._render(seed, {"n_scan_ff": len(sources)}, bytes.fromhex(ground_truth["key_hex"]), sources, list(range(len(sources))), [base, bytes(a), bytes(b), ab], f"joint-{seed}")
    signatures = differential_signatures(probe)["mc_capture"]
    return signatures[3][slot] == (signatures[1][slot] ^ signatures[2][slot])


def evaluate_candidate(scan_slot: int, holdout: dict, ground_truth: dict) -> dict:
    result = _evaluate_candidate(scan_slot, holdout, ground_truth)
    result["joint_superposition_match"] = _joint_probe(int(ground_truth["seed"]), ground_truth, scan_slot)
    return result
