"""Generate AES-aware structural dependency profiles for semantic taps."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass

from aes_ref import RCON
from experiment_common import ROOT, case_candidates, load_candidate_map, read_csv


@dataclass(frozen=True)
class Provenance:
    k: int = 0
    p: int = 0

    def __or__(self, other: "Provenance") -> "Provenance":
        return Provenance(self.k | other.k, self.p | other.p)


def union(items: list[Provenance]) -> Provenance:
    value = Provenance()
    for item in items:
        value = value | item
    return value


def xor_byte(a: list[Provenance], b: list[Provenance]) -> list[Provenance]:
    return [x | y for x, y in zip(a, b)]


def xor_many(*values: list[Provenance]) -> list[Provenance]:
    result = [Provenance() for _ in range(8)]
    for value in values:
        result = xor_byte(result, value)
    return result


def sbox(value: list[Provenance]) -> list[Provenance]:
    all_inputs = union(value)
    return [all_inputs for _ in range(8)]


def xtime(value: list[Provenance]) -> list[Provenance]:
    x = value
    return [x[7], x[0] | x[7], x[1], x[2] | x[7], x[3] | x[7], x[4], x[5], x[6]]


def shift_rows(state: list[list[Provenance]]) -> list[list[Provenance]]:
    output = [None] * 16
    for row in range(4):
        for column in range(4):
            output[4 * column + row] = state[4 * ((column + row) % 4) + row]
    return output


def mix_columns(state: list[list[Provenance]]) -> list[list[Provenance]]:
    output = [None] * 16
    for column in range(4):
        offset = 4 * column
        a0, a1, a2, a3 = state[offset : offset + 4]
        m2 = [xtime(a0), xtime(a1), xtime(a2), xtime(a3)]
        m3 = [xor_byte(m2[i], value) for i, value in enumerate((a0, a1, a2, a3))]
        output[offset] = xor_many(m2[0], m3[1], a2, a3)
        output[offset + 1] = xor_many(a0, m2[1], m3[2], a3)
        output[offset + 2] = xor_many(a0, a1, m2[2], m3[3])
        output[offset + 3] = xor_many(m3[0], a1, a2, m2[3])
    return output


def expand_key(key: list[list[Provenance]], rounds: int) -> list[list[list[Provenance]]]:
    round_keys = [key]
    for round_index in range(1, rounds + 1):
        previous = round_keys[-1]
        rotated = [sbox(previous[13]), sbox(previous[14]), sbox(previous[15]), sbox(previous[12])]
        assert RCON[round_index - 1] >= 0
        current = [None] * 16
        for index in range(4):
            current[index] = xor_byte(previous[index], rotated[index])
        for index in range(4, 16):
            current[index] = xor_byte(previous[index], current[index - 4])
        round_keys.append(current)
    return round_keys


def initial_bytes(kind: str) -> list[list[Provenance]]:
    state = []
    for byte_index in range(16):
        bits = []
        for bit_index in range(8):
            global_index = 8 * byte_index + bit_index
            bits.append(Provenance(
                k=(1 << global_index) if kind == "key" else 0,
                p=(1 << global_index) if kind == "plaintext" else 0,
            ))
        state.append(bits)
    return state


def build_support_trace(depth: int) -> dict[int, dict[str, list[list[Provenance]]]]:
    plaintext = initial_bytes("plaintext")
    master_key = initial_bytes("key")
    round_keys = expand_key(master_key, depth)
    state = [xor_byte(p, k) for p, k in zip(plaintext, round_keys[0])]
    trace = {}
    for round_index in range(1, depth + 1):
        sb = [sbox(value) for value in state]
        sr = shift_rows(sb)
        mc = mix_columns(sr)
        ark = [xor_byte(value, key_value) for value, key_value in zip(mc, round_keys[round_index])]
        trace[round_index] = {"SB": sb, "SR": sr, "MC": mc, "ARK": ark}
        state = ark
    return trace


def bit_indices(mask: int) -> list[int]:
    return [index for index in range(128) if mask & (1 << index)]


def byte_indices(mask: int) -> list[int]:
    return sorted({index // 8 for index in bit_indices(mask)})


def differential_equivalence_id(stage: str, bit_index: int) -> str:
    if stage in {"MC", "ARK"}:
        return f"DIFF_MC_ARK_{bit_index}"
    if stage == "SR":
        byte_index, bit = divmod(bit_index, 8)
        column, row = divmod(byte_index, 4)
        sb_byte = 4 * ((column + row) % 4) + row
        return f"DIFF_SB_SR_{8 * sb_byte + bit}"
    if stage == "SB":
        return f"DIFF_SB_SR_{bit_index}"
    return f"DIFF_{stage}_{bit_index}"


FIELDS = [
    "candidate_id", "stage", "bit_index", "round", "observation_mode",
    "structural_k0_bit_count", "structural_k0_bits_json", "structural_k0_bytes_json",
    "structural_plaintext_bit_count", "structural_plaintext_bits_json",
    "structural_plaintext_bytes_json", "differential_equivalence_class", "support_status",
]


def profile_candidates(candidate_ids: set[str], depth: int) -> list[dict[str, object]]:
    candidates = load_candidate_map()
    trace = build_support_trace(depth)
    rows = []
    for candidate_id in sorted(candidate_ids):
        candidate = candidates[candidate_id]
        stage = candidate["stage"]
        bit_index = int(candidate["bit_index"])
        byte_index, bit_in_byte = divmod(bit_index, 8)
        for round_index in range(1, depth + 1):
            support = trace[round_index][stage][byte_index][bit_in_byte]
            if stage == "ARK":
                support = trace[round_index]["MC"][byte_index][bit_in_byte]
            k_bits = bit_indices(support.k)
            p_bits = bit_indices(support.p)
            rows.append({
                "candidate_id": candidate_id,
                "stage": stage,
                "bit_index": bit_index,
                "round": round_index,
                "observation_mode": "differential",
                "structural_k0_bit_count": len(k_bits),
                "structural_k0_bits_json": json.dumps(k_bits),
                "structural_k0_bytes_json": json.dumps(byte_indices(support.k)),
                "structural_plaintext_bit_count": len(p_bits),
                "structural_plaintext_bits_json": json.dumps(p_bits),
                "structural_plaintext_bytes_json": json.dumps(byte_indices(support.p)),
                "differential_equivalence_class": differential_equivalence_id(stage, bit_index),
                "support_status": "structural_overapprox_mode_simplified",
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--output", default="reference/dependency_support_profiles.csv")
    args = parser.parse_args()

    case_rows = read_csv(ROOT / args.cases)
    candidate_ids = {candidate for row in case_rows for candidate in case_candidates(row)}
    profiles = profile_candidates(candidate_ids, args.depth)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(profiles)
    print(f"wrote {len(profiles)} tap-round profiles for {len(candidate_ids)} candidates -> {output}")


if __name__ == "__main__":
    main()
