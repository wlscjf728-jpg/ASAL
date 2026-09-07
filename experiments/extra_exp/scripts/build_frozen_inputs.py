#!/usr/bin/env python3
"""Freeze the MC9 seed2 case without mixing evaluator truth into attacker inputs."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


EXTRA_EXP = Path(__file__).resolve().parents[1]
ROOT = EXTRA_EXP.parent
COMMON = ROOT / "anonymous_subround_multiround_attack_8_oracle" / "scripts" / "experiment_common.py"
FIXED_JSON_CANDIDATES = (
    ROOT / "exp_res" / "04_adaptive_pair_rescue_campaigns" / "results" / "late_1bit_fixed_q128_runs" / "late1_MC_9__seed2__late1bit_fixed_q128.json",
    ROOT / "anonymous_subround_multiround_attack_8_oracle" / "results" / "late_1bit_fixed_q128_runs" / "late1_MC_9__seed2__late1bit_fixed_q128.json",
)
ADAPTIVE_JSON_CANDIDATES = (
    ROOT / "exp_res" / "04_adaptive_pair_rescue_campaigns" / "results" / "late_1bit_pair_rescue_runs" / "late1_MC_9__seed2__late1bit_pair_rescue.json",
    ROOT / "anonymous_subround_multiround_attack_8_oracle" / "results" / "late_1bit_pair_rescue_runs" / "late1_MC_9__seed2__late1bit_pair_rescue.json",
)
TOOL_PATHS = {
    "vcs": Path("/srscl/tools/synopsys/VCS/vcs/R-2020.12-SP1/linux64/bin/vcs"),
    "verdi": Path("/srscl/tools/synopsys/verdi_202012/verdi/R-2020.12-SP1/bin/verdi"),
    "dc_shell": Path("/srscl/tools/synopsys/design_compiler_202106/syn/S-2021.06-SP4/bin/dc_shell"),
}


def _load_common():
    spec = importlib.util.spec_from_file_location("attack8_experiment_common", COMMON)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {COMMON}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_existing(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    joined = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"none of the authoritative files exists:\n{joined}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tool_version(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    for args in (("-ID",), ("-version",), ("-help",)):
        try:
            result = subprocess.run(
                [str(path), *args], capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"ERROR {type(exc).__name__}"
        output = (result.stdout + result.stderr).strip().splitlines()
        if output:
            return output[0][:240]
    return "NO_VERSION_OUTPUT"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build() -> None:
    common = _load_common()
    fixed_path = _first_existing(FIXED_JSON_CANDIDATES)
    adaptive_path = _first_existing(ADAPTIVE_JSON_CANDIDATES)
    fixed = json.loads(fixed_path.read_text())
    adaptive = json.loads(adaptive_path.read_text())
    if fixed.get("candidate_id") != "MC_9" or fixed.get("seed") != 2:
        raise ValueError("fixed source is not MC_9 seed2")
    if adaptive.get("candidate_id") != "MC_9" or adaptive.get("seed") != 2:
        raise ValueError("adaptive source is not MC_9 seed2")

    queries = [
        {"query_id": index, "plaintext_hex": plaintext.hex()}
        for index, plaintext in enumerate(common.nested_plaintexts(128, 2))
    ]
    key = common.key_for_seed(2)
    historical_separator = adaptive["steps"][0]["accepted_plaintext_hex"]
    output = EXTRA_EXP / "inputs"
    _write_json(output / "frozen_case.json", {
        "schema": "mc9-eda-frozen-case-v1",
        "case_id": "late1_MC_9__seed2",
        "seed": 2,
        "tap": {"stage": "MC", "bit_index": 9},
        "depth": 2,
        "mode": "differential",
        "reference_plaintext_hex": "00000000000000000000000000000000",
        "fixed_query_count": 128,
        "fixed_oracle_encryptions": 129,
        "historical_separator_hex": historical_separator,
        "historical_true_response": [0, 1],
        "historical_alternative_response": [0, 0],
        "expected_fixed_classification": "finite_query_ambiguity",
        "expected_adaptive_classification": "full_key_unique",
        "source_fixed_json": str(fixed_path.relative_to(ROOT)),
        "source_adaptive_json": str(adaptive_path.relative_to(ROOT)),
    })
    _write_json(output / "mc9_seed2_q128.json", {
        "schema": "mc9-attacker-query-manifest-v1",
        "case_id": "late1_MC_9__seed2",
        "seed": 2,
        "reference_query_id": 0,
        "queries": queries,
    })
    phase0 = [{"query_id": 0, "plaintext_hex": queries[0]["plaintext_hex"]}]
    for byte_index in range(16):
        for delta in (1, 2, 4, 8):
            value = bytearray(16)
            value[byte_index] = delta
            phase0.append({"query_id": len(phase0), "plaintext_hex": bytes(value).hex()})
    _write_json(output / "phase0_queries.json", {
        "schema": "mc9-phase0-query-manifest-v1",
        "case_id": "late1_MC_9__seed2",
        "differentials": [1, 2, 4, 8],
        "queries": phase0,
    })
    _write_json(output / "known_separator_control.json", {
        "schema": "mc9-known-separator-control-v1",
        "plaintext_hex": historical_separator,
        "expected_true_response": [0, 1],
        "expected_historical_alternative_response": [0, 0],
    })
    _write_json(output / "hidden_key.evaluator.json", {
        "schema": "evaluator-only-hidden-key-v1",
        "case_id": "late1_MC_9__seed2",
        "true_key_hex": key.hex(),
    })

    provenance = EXTRA_EXP / "provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    source_paths = [COMMON, fixed_path, adaptive_path, Path(__file__).resolve()]
    (provenance / "source_hashes.sha256").write_text(
        "\n".join(f"{_sha256(path)}  {path.relative_to(ROOT)}" for path in source_paths) + "\n"
    )
    (provenance / "tool_versions.txt").write_text(
        "\n".join(f"{name}={path}\nversion={_tool_version(path)}" for name, path in TOOL_PATHS.items()) + "\n"
    )


def verify() -> None:
    common = _load_common()
    manifest = json.loads((EXTRA_EXP / "inputs" / "mc9_seed2_q128.json").read_text())
    expected = [plaintext.hex() for plaintext in common.nested_plaintexts(128, 2)]
    actual = [row["plaintext_hex"] for row in manifest["queries"]]
    if actual != expected:
        raise AssertionError("Q128 manifest differs from nested_plaintexts(128, 2)")
    attacker_text = json.dumps(manifest)
    for forbidden in (common.key_for_seed(2).hex(), "MC_REG[9]", "scan_path"):
        if forbidden in attacker_text:
            raise AssertionError(f"attacker manifest contains forbidden field: {forbidden}")
    phase0 = json.loads((EXTRA_EXP / "inputs" / "phase0_queries.json").read_text())
    if len(phase0["queries"]) != 65:
        raise AssertionError("Phase 0 must contain exactly 65 queries")
    print("frozen inputs verified: q128=129 phase0=65")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        build()


if __name__ == "__main__":
    main()
