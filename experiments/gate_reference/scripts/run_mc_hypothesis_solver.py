#!/usr/bin/env python3
"""Solve an anonymous C0 MC transcript over all surviving function hypotheses."""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import z3

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "temporal_key_recovery" / "scripts"))
from z3_aes import AESGraphBuilder, select_bit  # noqa: E402


def status(result: z3.CheckSatResult) -> str:
    return str(result).lower()


def model_key(model: z3.ModelRef, key: list[z3.BitVecRef]) -> str:
    return bytes(model.eval(item, model_completion=True).as_long() for item in key).hex()


def hypothesis_lookup(doc: dict[str, object]) -> list[dict[str, object]]:
    hypotheses = doc["experiment"]["hypotheses"]
    if not hypotheses:
        raise ValueError("empty hypothesis set")
    ids = [item["hypothesis_id"] for item in hypotheses]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate hypothesis id")
    if any("MC_9" in json.dumps(item) or "MC9" in json.dumps(item) for item in hypotheses):
        raise ValueError("ground-truth MC9 label is forbidden in attack input")
    return list(hypotheses)


def build_context(doc: dict[str, object], sbox_encoding: str):
    experiment = doc["experiment"]
    depth = int(experiment["depth"])
    mode = experiment["mode"]
    if mode != "differential":
        raise ValueError("this attribution solver expects differential observations")
    hypotheses = hypothesis_lookup(doc)
    key = [z3.BitVec(f"k_{index}", 8) for index in range(16)]
    builder = AESGraphBuilder(depth, key, sbox_encoding)
    for observation in doc["observations"]:
        builder.build_for_plaintext(
            bytes.fromhex(observation["plaintext_hex"]),
            str(observation["query_id"]),
        )
    base_id = str(experiment.get("base_query_id", 0))
    branch_constraints: dict[str, list[z3.BoolRef]] = {}
    for hypothesis in hypotheses:
        branch = []
        bit_index = int(hypothesis["bit_index"])
        stage = str(hypothesis["stage"])
        for observation in doc["observations"]:
            query_id = str(observation["query_id"])
            for round_index in range(1, depth + 1):
                query_bit = select_bit(
                    builder.graphs[query_id][round_index][stage], bit_index
                )
                base_bit = select_bit(
                    builder.graphs[base_id][round_index][stage], bit_index
                )
                observed = int(observation["rounds"][str(round_index)]["differential"])
                branch.append((query_bit ^ base_bit) == z3.BitVecVal(observed, 1))
        branch_constraints[str(hypothesis["hypothesis_id"])] = branch
    return key, builder, hypotheses, branch_constraints


_BRANCH_DOC: dict[str, object] | None = None
_BRANCH_ENCODING = "uf_axiom"


def _init_branch_worker(doc: dict[str, object], sbox_encoding: str) -> None:
    global _BRANCH_DOC, _BRANCH_ENCODING
    _BRANCH_DOC = doc
    _BRANCH_ENCODING = sbox_encoding


def _check_one_branch(hypothesis: dict[str, object]) -> dict[str, object]:
    if _BRANCH_DOC is None:
        raise RuntimeError("branch worker is not initialized")
    key, builder, _hypotheses, branch_constraints = build_context(_BRANCH_DOC, _BRANCH_ENCODING)
    hypothesis_id = str(hypothesis["hypothesis_id"])
    solver = z3.Solver()
    solver.add(*builder.sbox_constraints, *branch_constraints[hypothesis_id])
    started = time.perf_counter()
    result = solver.check()
    elapsed = time.perf_counter() - started
    row: dict[str, object] = {
        "hypothesis_id": hypothesis_id,
        "status": status(result),
        "elapsed_seconds": elapsed,
        "unknown_reason": solver.reason_unknown() if result == z3.unknown else "",
    }
    if result == z3.sat:
        row["model_hex"] = model_key(solver.model(), key)
    return row


def check_branch_consistency(
    doc: dict[str, object],
    hypotheses: list[dict[str, object]],
    sbox_encoding: str,
    workers: int,
) -> list[dict[str, object]]:
    workers = max(1, min(int(workers), len(hypotheses)))
    if workers == 1:
        _init_branch_worker(doc, sbox_encoding)
        results = [_check_one_branch(hypothesis) for hypothesis in hypotheses]
    else:
        context = mp.get_context("fork")
        with context.Pool(
            processes=workers,
            initializer=_init_branch_worker,
            initargs=(doc, sbox_encoding),
        ) as pool:
            results = pool.map(_check_one_branch, hypotheses)
    by_id = {str(row["hypothesis_id"]): row for row in results}
    return [by_id[str(hypothesis["hypothesis_id"])] for hypothesis in hypotheses]


_JOINT_DOC: dict[str, object] | None = None
_JOINT_ENCODING = "uf_axiom"
_JOINT_KEY_HEX = ""


def _init_joint_worker(doc: dict[str, object], sbox_encoding: str, key_hex: str) -> None:
    global _JOINT_DOC, _JOINT_ENCODING, _JOINT_KEY_HEX
    _JOINT_DOC = doc
    _JOINT_ENCODING = sbox_encoding
    _JOINT_KEY_HEX = key_hex


def _check_blocked_branch(hypothesis: dict[str, object]) -> dict[str, object]:
    if _JOINT_DOC is None:
        raise RuntimeError("joint worker is not initialized")
    key, builder, _hypotheses, branch_constraints = build_context(_JOINT_DOC, _JOINT_ENCODING)
    solver = z3.Solver()
    solver.add(*builder.sbox_constraints, *branch_constraints[str(hypothesis["hypothesis_id"])])
    first_key = bytes.fromhex(_JOINT_KEY_HEX)
    # Block the complete first key; enumerate(first_key) yields positions, not symbolic key bytes.
    solver.add(z3.Or(*[key_item != z3.BitVecVal(value, 8) for key_item, value in zip(key, first_key)]))
    started = time.perf_counter()
    result = solver.check()
    elapsed = time.perf_counter() - started
    row: dict[str, object] = {
        "hypothesis_id": str(hypothesis["hypothesis_id"]),
        "status": status(result),
        "elapsed_seconds": elapsed,
        "unknown_reason": solver.reason_unknown() if result == z3.unknown else "",
    }
    if result == z3.sat:
        row["model_hex"] = model_key(solver.model(), key)
    return row


def joint_solver(
    doc: dict[str, object],
    hypotheses: list[dict[str, object]],
    branch_results: list[dict[str, object]],
    sbox_encoding: str,
    workers: int,
):
    sat_branches = [row for row in branch_results if row["status"] == "sat"]
    if not sat_branches:
        return {
            "first_result": "unsat",
            "second_result": "not_run",
            "first_time": 0.0,
            "second_time": 0.0,
            "first_model_hex": "",
            "first_hypothesis_id": "",
            "alternative_model": "",
            "alternative_hypothesis_id": "",
            "timeout": False,
            "unknown": False,
            "classification": "inconsistent",
            "confirmed_unique_candidate": False,
            "branch_key_exclusion": [],
        }
    first_row = sat_branches[0]
    first_key = str(first_row["model_hex"])
    first_id = str(first_row["hypothesis_id"])
    tasks = [next(h for h in hypotheses if str(h["hypothesis_id"]) == str(row["hypothesis_id"])) for row in sat_branches]
    started = time.perf_counter()
    workers = max(1, min(int(workers), len(tasks)))
    if workers == 1:
        _init_joint_worker(doc, sbox_encoding, first_key)
        blocked = [_check_blocked_branch(task) for task in tasks]
    else:
        context = mp.get_context("fork")
        with context.Pool(processes=workers, initializer=_init_joint_worker, initargs=(doc, sbox_encoding, first_key)) as pool:
            blocked = pool.map(_check_blocked_branch, tasks)
    second_time = time.perf_counter() - started
    alternative = next((row for row in blocked if row["status"] == "sat"), None)
    unknown = next((row for row in blocked if row["status"] == "unknown"), None)
    if alternative is not None:
        second_result = "sat"
        classification = "ambiguity"
        alternative_model = str(alternative["model_hex"])
        alternative_id = str(alternative["hypothesis_id"])
        reason = ""
    elif unknown is not None:
        second_result = "unknown"
        classification = "unresolved"
        alternative_model = ""
        alternative_id = ""
        reason = str(unknown.get("unknown_reason", ""))
    else:
        second_result = "unsat"
        classification = "full_key_unique"
        alternative_model = ""
        alternative_id = ""
        reason = ""
    return {
        "first_result": "sat",
        "second_result": second_result,
        "first_time": float(first_row.get("elapsed_seconds", 0.0)),
        "second_time": second_time,
        "first_model_hex": first_key,
        "first_hypothesis_id": first_id,
        "alternative_model": alternative_model,
        "alternative_hypothesis_id": alternative_id,
        "timeout": second_result == "unknown",
        "unknown": second_result == "unknown",
        "z3_reason_unknown": reason,
        "classification": classification,
        "confirmed_unique_candidate": second_result == "unsat",
        "branch_key_exclusion": blocked,
        "branch_workers": workers,
        "key_exclusion_scope": "all_surviving_hypotheses",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sbox-encoding", default="uf_axiom", choices=("uf_axiom", "array_select", "ite_bv"))
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    doc = json.loads(args.input.read_text())
    started = time.perf_counter()
    hypotheses = hypothesis_lookup(doc)
    branch_results = check_branch_consistency(doc, hypotheses, args.sbox_encoding, args.workers)
    key, builder, hypotheses, branch_constraints = build_context(doc, args.sbox_encoding)
    surviving = [
        hypothesis for hypothesis, result in zip(hypotheses, branch_results)
        if result["status"] == "sat"
    ]
    if not surviving:
        raise RuntimeError("all hypotheses are inconsistent")
    joint = joint_solver(doc, surviving, [
        row for row in branch_results if row["status"] == "sat"
    ], args.sbox_encoding, args.workers)
    result = {
        "schema": "mc9-anonymous-function-attribution-solver-v1",
        "input_transcript": str(args.input),
        "sbox_encoding": args.sbox_encoding,
        "initial_hypothesis_count": len(hypotheses),
        "branch_consistency": branch_results,
        "surviving_hypotheses": surviving,
        "surviving_hypothesis_count": len(surviving),
        "joint_key_uniqueness": joint,
        "attack_used_ground_truth_mc9": False,
        "attack_used_hidden_key": False,
        "wall_time_seconds": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "initial_hypotheses": len(hypotheses),
        "surviving_hypotheses": len(surviving),
        "first_result": joint["first_result"],
        "second_result": joint["second_result"],
        "classification": joint.get("classification"),
        "wall_time_seconds": result["wall_time_seconds"],
        "branch_workers": max(1, min(args.workers, len(hypotheses))),
    }, indent=2))


if __name__ == "__main__":
    main()
