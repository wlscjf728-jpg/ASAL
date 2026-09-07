"""Concrete leakage and dependency scoring for late one-bit AES taps."""

from collections import Counter
from math import log2

from aes_ref import encrypt_with_trace


def _absolute_bit(key, tap, plaintext, round_index):
    trace = encrypt_with_trace(plaintext, key)["rounds"]
    value = trace[round_index][str(tap["stage"])][int(tap["bit_index"]) // 8]
    return (value >> (int(tap["bit_index"]) % 8)) & 1


def leakage_signature(key, tap, plaintext, reference, depth):
    return tuple(
        _absolute_bit(key, tap, plaintext, round_index)
        ^ _absolute_bit(key, tap, reference, round_index)
        for round_index in range(1, depth + 1)
    )


def unresolved_key_bits(keys):
    return {
        bit
        for bit in range(128)
        if len({(key[bit // 8] >> (bit % 8)) & 1 for key in keys}) > 1
    }


def influence_profile(plaintext, keys, tap, reference, depth, unresolved_bits):
    profile = {}
    for bit in sorted(unresolved_bits):
        count = 0
        for key in keys:
            mutated = bytearray(key)
            mutated[bit // 8] ^= 1 << (bit % 8)
            count += leakage_signature(
                key, tap, plaintext, reference, depth
            ) != leakage_signature(bytes(mutated), tap, plaintext, reference, depth)
        profile[bit] = count
    return profile


def score_plaintext(plaintext, keys, tap, reference, depth, prior_active_bits):
    signatures = [leakage_signature(key, tap, plaintext, reference, depth) for key in keys]
    buckets = Counter(signatures)
    entropy = -sum(
        (count / len(keys)) * log2(count / len(keys)) for count in buckets.values()
    )
    influence = influence_profile(
        plaintext, keys, tap, reference, depth, unresolved_key_bits(keys)
    )
    active_bits = {bit for bit, count in influence.items() if count}
    values = list(influence.values())
    rank_key = (
        len(keys) - max(buckets.values()),
        entropy,
        len(active_bits - prior_active_bits),
        len(active_bits),
        -(max(values, default=0) - min(values, default=0)),
        -int.from_bytes(plaintext, "big"),
    )
    return {
        "plaintext_hex": plaintext.hex(),
        "partition_gain": rank_key[0],
        "entropy": entropy,
        "active_bits": sorted(active_bits),
        "novel_bits": sorted(active_bits - prior_active_bits),
        "influence_counts": {str(bit): count for bit, count in influence.items()},
        "rank_key": rank_key,
    }


def rank_plaintexts(points, keys, tap, reference, depth, prior_active_bits):
    return sorted(
        [
            score_plaintext(point, keys, tap, reference, depth, prior_active_bits)
            for point in points
        ],
        key=lambda item: item["rank_key"],
        reverse=True,
    )
