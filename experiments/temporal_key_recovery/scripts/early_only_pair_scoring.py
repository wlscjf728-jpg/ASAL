"""Dynamic dependency-influence ranking for multi-tap pair separators."""
from __future__ import annotations

from aes_ref import encrypt_with_trace


def leakage_signature(key: bytes, taps: tuple[dict[str, object], ...], plaintext: bytes, reference: bytes, depth: int) -> tuple[int, ...]:
    query_trace = encrypt_with_trace(plaintext, key)["rounds"]
    base_trace = encrypt_with_trace(reference, key)["rounds"]
    values = []
    for round_index in range(1, depth + 1):
        for tap in taps:
            byte_index, bit_index = divmod(int(tap["bit_index"]), 8)
            query_value = query_trace[round_index][str(tap["stage"])][byte_index]
            base_value = base_trace[round_index][str(tap["stage"])][byte_index]
            values.append(((query_value ^ base_value) >> bit_index) & 1)
    return tuple(values)


def differing_key_bits(key_a: bytes, key_b: bytes) -> set[int]:
    return {
        bit for bit in range(128)
        if ((key_a[bit // 8] >> (bit % 8)) & 1) != ((key_b[bit // 8] >> (bit % 8)) & 1)
    }


def rank_pair_plaintexts(points: list[bytes], key_a: bytes, key_b: bytes, taps: tuple[dict[str, object], ...], reference: bytes, depth: int, prior_active_bits: set[int]) -> list[dict[str, object]]:
    differing = differing_key_bits(key_a, key_b)
    scored = []
    for plaintext in points:
        active = {}
        for bit in sorted(differing):
            count = 0
            for key in (key_a, key_b):
                mutated = bytearray(key)
                mutated[bit // 8] ^= 1 << (bit % 8)
                if leakage_signature(key, taps, plaintext, reference, depth) != leakage_signature(bytes(mutated), taps, plaintext, reference, depth):
                    count += 1
            active[bit] = count
        active_bits = {bit for bit, count in active.items() if count}
        counts = list(active.values())
        rank_key = (
            len(active_bits - prior_active_bits),
            len(active_bits),
            -(max(counts, default=0) - min(counts, default=0)),
            -int.from_bytes(plaintext, "big"),
        )
        scored.append({
            "plaintext_hex": plaintext.hex(),
            "differing_key_bits": sorted(differing),
            "active_bits": sorted(active_bits),
            "novel_bits": sorted(active_bits - prior_active_bits),
            "influence_counts": {str(bit): count for bit, count in active.items()},
            "rank_key": rank_key,
        })
    return sorted(scored, key=lambda item: item["rank_key"], reverse=True)
