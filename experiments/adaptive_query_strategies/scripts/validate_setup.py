"""Static validation for the Attack 8 experiment setup."""
from __future__ import annotations

import csv
from pathlib import Path

import z3

from dependency_support import build_support_trace, differential_equivalence_id
from experiment_common import ROOT, case_candidates, load_candidate_map, nested_plaintexts, read_csv
from z3_aes import AESGraphBuilder


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_cases() -> None:
    candidate_map = load_candidate_map()
    expected_minimum = {2: 1, 3: 1, 4: 1}
    for bits, minimum in expected_minimum.items():
        path = ROOT / "configs" / f"selected_{bits}bit_proven_ambiguous.csv"
        rows = read_csv(path)
        require(len(rows) >= minimum, f"no selected {bits}-bit cases")
        seen = set()
        for row in rows:
            candidates = case_candidates(row)
            require(len(candidates) == bits, f"tap-count mismatch: {row['attack8_case_id']}")
            require(int(row["proof_ambiguity_runs"]) > 0, "selected case lacks direct ambiguity proof")
            require(int(row["proof_unique_runs"]) == 0, "selected case contains a direct unique proof")
            require(all(candidate in candidate_map for candidate in candidates), "unknown candidate")
            key = tuple(sorted(candidates))
            require(key not in seen, f"duplicate tap set in {path}")
            seen.add(key)
        print(f"validated {len(rows)} selected {bits}-bit cases")


def validate_nested_queries() -> None:
    q32 = nested_plaintexts(32, 0)
    q64 = nested_plaintexts(64, 0)
    require(q32 == q64[: len(q32)], "plaintext ladders are not nested")
    require(len(q32) == 33 and len(q64) == 65, "reference/query accounting changed")
    print("validated nested query generation and reference accounting")


def validate_symbolic_plaintext() -> None:
    symbolic = [z3.BitVec(f"setup_p_{index}", 8) for index in range(16)]
    builder = AESGraphBuilder(2, sbox_encoding="uf_axiom")
    graph = builder.build_for_plaintext(symbolic, "symbolic_setup")
    require(set(graph[1]) == {"SB", "SR", "MC", "ARK"}, "symbolic graph missing stages")
    print("validated symbolic plaintext AES graph construction")


def validate_support() -> None:
    trace = build_support_trace(2)
    round1_sb0 = trace[1]["SB"][0][0]
    round1_mc0 = trace[1]["MC"][0][0]
    require(round1_sb0.k.bit_count() == 8, "round-1 SB support should be byte-local")
    require(round1_mc0.k.bit_count() == 32, "round-1 MC support should cover four source bytes")
    require(
        differential_equivalence_id("MC", 9) == differential_equivalence_id("ARK", 9),
        "MC/ARK differential equivalence class mismatch",
    )
    print("validated structural AES support and differential equivalence labels")


def main() -> None:
    validate_cases()
    validate_nested_queries()
    validate_symbolic_plaintext()
    validate_support()
    print("Attack 8 setup validation passed; no solver campaign was executed")


if __name__ == "__main__":
    main()
