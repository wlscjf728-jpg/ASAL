from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import late1bit_scoring
from aes_ref import encrypt_with_trace
from late1bit_scoring import (
    leakage_signature,
    rank_plaintexts,
    unresolved_key_bits,
)

TAP = {"tap_id": "t0", "stage": "MC", "bit_index": 0}


def test_signature_has_one_bit_per_round_and_zero_at_reference():
    key = bytes(range(16))
    reference = bytes(16)
    assert leakage_signature(key, TAP, reference, reference, 2) == (0, 0)
    assert len(
        leakage_signature(key, TAP, bytes.fromhex("01" + "00" * 15), reference, 2)
    ) == 2


def test_unresolved_bits_follow_little_endian_bit_indexing():
    keys = [bytes(16), bytes([1]) + bytes(15), bytes([0, 128]) + bytes(14)]
    assert unresolved_key_bits(keys) == {0, 15}


def test_signature_matches_independent_nonzero_round_one_and_two_differentials():
    key = bytes(range(16))
    plaintext = bytes.fromhex("04" + "00" * 15)
    reference = bytes(16)
    byte_index = TAP["bit_index"] // 8
    bit_offset = TAP["bit_index"] % 8
    plaintext_trace = encrypt_with_trace(plaintext, key)["rounds"]
    reference_trace = encrypt_with_trace(reference, key)["rounds"]
    expected = tuple(
        ((plaintext_trace[round_index][TAP["stage"]][byte_index] >> bit_offset) & 1)
        ^ ((reference_trace[round_index][TAP["stage"]][byte_index] >> bit_offset) & 1)
        for round_index in (1, 2)
    )

    assert expected == (1, 1)
    assert leakage_signature(key, TAP, plaintext, reference, 2) == expected


def test_rank_prefers_higher_partition_gain_over_much_higher_influence(monkeypatch):
    high_influence = bytes.fromhex("01" + "00" * 15)
    high_partition_gain = bytes.fromhex("02" + "00" * 15)
    scores = {
        high_influence: {
            "plaintext_hex": high_influence.hex(),
            "partition_gain": 1,
            "influence_counts": {"0": 10_000},
            "rank_key": (1, 99.0, 999, 999, -999, -1),
        },
        high_partition_gain: {
            "plaintext_hex": high_partition_gain.hex(),
            "partition_gain": 2,
            "influence_counts": {"0": 0},
            "rank_key": (2, 0.0, 0, 0, 0, -2),
        },
    }
    monkeypatch.setattr(late1bit_scoring, "score_plaintext", lambda point, *_: scores[point])

    ranked = rank_plaintexts(
        [high_influence, high_partition_gain], [], TAP, bytes(16), 2, set()
    )

    assert [item["plaintext_hex"] for item in ranked] == [
        high_partition_gain.hex(),
        high_influence.hex(),
    ]


def test_rank_uses_lower_plaintext_integer_after_equal_preceding_components(monkeypatch):
    higher_plaintext = bytes(15) + b"\x02"
    lower_plaintext = bytes(15) + b"\x01"
    scores = {
        higher_plaintext: {
            "plaintext_hex": higher_plaintext.hex(),
            "rank_key": (4, 1.5, 3, 7, -2, -2),
        },
        lower_plaintext: {
            "plaintext_hex": lower_plaintext.hex(),
            "rank_key": (4, 1.5, 3, 7, -2, -1),
        },
    }
    monkeypatch.setattr(late1bit_scoring, "score_plaintext", lambda point, *_: scores[point])

    ranked = rank_plaintexts(
        [higher_plaintext, lower_plaintext], [], TAP, bytes(16), 2, set()
    )

    assert [item["plaintext_hex"] for item in ranked] == [
        lower_plaintext.hex(),
        higher_plaintext.hex(),
    ]
