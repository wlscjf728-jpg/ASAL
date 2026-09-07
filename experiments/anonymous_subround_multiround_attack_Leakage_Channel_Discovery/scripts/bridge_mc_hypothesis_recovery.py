"""Bridge anonymous MC-channel discovery to hypothesis-aware key recovery.

The analyzer path receives only the selected anonymous slot, its MC column
hypothesis, and the selected slot's observed one-bit temporal transcript. The
oracle-side renderer uses ground truth only to generate that transcript. The
reported evaluation fields are kept separate from attacker-path decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import count
from pathlib import Path

import z3

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = ROOT / "anonymous_subround_multiround_attack_Leakage_Channel_Discovery"
ATTACK8_SCRIPTS = ROOT / "anonymous_subround_multiround_attack_8_oracle" / "scripts"
sys.path.insert(0, str(ATTACK8_SCRIPTS))
sys.path.insert(1, str(DISCOVERY_ROOT / "scripts"))

from oracle import generate_observation  # noqa: E402
from scan_channel_generator_legacy import MC_COLUMNS, coarse_plaintexts  # noqa: E402
from z3_aes import AESGraphBuilder, select_bit  # noqa: E402


SOLVER_NAMES = count()
BRANCH_WORKERS = 16
DEPTH = 2
MODE = "differential"
SBOX_ENCODING = "uf_axiom"


def status_name(result: z3.CheckSatResult) -> str:
    return str(result).lower()


def trial_key_and_true_bit(ground_truth: dict) -> tuple[bytes, int]:
    targets = [source for source in ground_truth["scan_sources"] if source["kind"] == "mc"]
    if len(targets) != 1:
        raise ValueError("bridge expects exactly one hidden MC target")
    return bytes.fromhex(ground_truth["key_hex"]), int(targets[0]["bit_index"])


def make_hypotheses(column: int) -> list[dict[str, object]]:
    if not 0 <= column < len(MC_COLUMNS):
        raise ValueError(f"invalid MC column: {column}")
    hypotheses = []
    for row in range(4):
        byte_index = 4 * column + row
        for bit in range(8):
            bit_index = 8 * byte_index + bit
            hypotheses.append({
                "hypothesis_id": f"MC_C{column}_BYTE{byte_index}_BIT{bit}",
                "stage": "MC",
                "column": column,
                "byte_index": byte_index,
                "bit_in_byte": bit,
                "bit_index": bit_index,
            })
    return hypotheses


def render_temporal_transcript(key: bytes, true_bit: int, plaintexts: list[bytes]) -> tuple[dict, list[tuple[int, int]]]:
    tap = {"tap_id": "s_star", "stage": "MC", "bit_index": true_bit}
    document = generate_observation(key, [tap], plaintexts, DEPTH, MODE)
    leakage = []
    for observation in document["observations"]:
        leakage.append(tuple(
            int(observation["rounds"][str(round_index)]["s_star"]["differential"])
            for round_index in range(1, DEPTH + 1)
        ))
    return document, leakage


def make_graph(plaintexts: list[bytes], key: list[z3.BitVecRef], prefix: str):
    builder = AESGraphBuilder(DEPTH, key, SBOX_ENCODING)
    for query_id, plaintext in enumerate(plaintexts):
        builder.build_for_plaintext(plaintext, f"{prefix}_q{query_id}")
    return builder


def hypothesis_constraints(builder, plaintexts: list[bytes], leakage: list[tuple[int, int]], hypothesis: dict[str, object], prefix: str):
    bit_index = int(hypothesis["bit_index"])
    constraints = []
    base_id = f"{prefix}_q0"
    for query_id in range(len(plaintexts)):
        query_id_name = f"{prefix}_q{query_id}"
        for round_index in range(1, DEPTH + 1):
            query_bit = select_bit(builder.graphs[query_id_name][round_index]["MC"], bit_index)
            base_bit = select_bit(builder.graphs[base_id][round_index]["MC"], bit_index)
            constraints.append(
                (query_bit ^ base_bit) == z3.BitVecVal(leakage[query_id][round_index - 1], 1)
            )
    return constraints


def solve_single_hypothesis(payload: tuple[list[bytes], list[tuple[int, int]], dict[str, object], str | None]) -> dict[str, object]:
    """Solve one h branch; the disjunction over h is the caller's union."""
    plaintexts, leakage, hypothesis, blocked_hex = payload
    prefix = f"branch_{os.getpid()}_{next(SOLVER_NAMES)}"
    key = [z3.BitVec(f"{prefix}_k{i}", 8) for i in range(16)]
    builder = make_graph(plaintexts, key, prefix)
    constraints = hypothesis_constraints(builder, plaintexts, leakage, hypothesis, prefix)
    solver = z3.Solver()
    solver.add(*builder.sbox_constraints, *constraints)
    if blocked_hex is not None:
        blocked_key = bytes.fromhex(blocked_hex)
        solver.add(z3.Or(*[
            key[index] != z3.BitVecVal(value, 8)
            for index, value in enumerate(blocked_key)
        ]))

    started = time.perf_counter()
    result = solver.check()
    elapsed = time.perf_counter() - started
    row: dict[str, object] = {
        "status": status_name(result),
        "elapsed_seconds": elapsed,
        "hypothesis_count": 1,
        "hypothesis_id": str(hypothesis["hypothesis_id"]),
    }
    if result != z3.sat:
        row["reason_unknown"] = solver.reason_unknown() if result == z3.unknown else ""
        return row
    model = solver.model()
    candidate = bytes(model.eval(value, model_completion=True).as_long() for value in key)
    row.update({
        "candidate_key_sha256": hashlib.sha256(candidate).hexdigest(),
        "candidate_key": candidate,
        "matching_hypotheses": [str(hypothesis["hypothesis_id"])],
    })
    return row


def solve_union(
    plaintexts: list[bytes],
    leakage: list[tuple[int, int]],
    hypotheses: list[dict[str, object]],
    blocked_key: bytes | None = None,
) -> dict[str, object]:
    """Evaluate OR_h C_Q(K,h) as independent, parallel SAT branches."""
    blocked_hex = blocked_key.hex() if blocked_key is not None else None
    payloads = [(plaintexts, leakage, hypothesis, blocked_hex) for hypothesis in hypotheses]
    if len(payloads) == 1:
        branch_results = [solve_single_hypothesis(payloads[0])]
    else:
        workers = min(BRANCH_WORKERS, len(payloads))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            branch_results = list(pool.map(solve_single_hypothesis, payloads))

    sat_branches = [row for row in branch_results if row["status"] == "sat"]
    unknown_branches = [row for row in branch_results if row["status"] == "unknown"]
    if sat_branches:
        chosen = sat_branches[0]
        return {
            **chosen,
            "union_status": "sat",
            "hypothesis_count": len(hypotheses),
            "sat_branch_count": len(sat_branches),
        }
    if unknown_branches:
        return {
            "status": "unknown",
            "union_status": "unknown",
            "hypothesis_count": len(hypotheses),
            "sat_branch_count": 0,
            "unknown_branch_count": len(unknown_branches),
            "reason_unknown": "; ".join(str(row.get("reason_unknown", "")) for row in unknown_branches),
        }
    return {
        "status": "unsat",
        "union_status": "unsat",
        "hypothesis_count": len(hypotheses),
        "sat_branch_count": 0,
        "unknown_branch_count": 0,
    }

def solve_path(
    plaintexts: list[bytes],
    leakage: list[tuple[int, int]],
    hypotheses: list[dict[str, object]],
) -> dict[str, object]:
    first = solve_union(plaintexts, leakage, hypotheses)
    if first["status"] != "sat":
        return {"first": first, "second": {"status": "not_run"}, "classification": "unresolved"}
    candidate = first["candidate_key"]
    second = solve_union(plaintexts, leakage, hypotheses, blocked_key=candidate)
    classification = {
        "unsat": "full_key_unique",
        "sat": "ambiguity",
        "unknown": "unresolved",
    }.get(str(second["status"]), "unresolved")
    return {
        "first": first,
        "second": second,
        "classification": classification,
    }


def solve_known_path(
    plaintexts: list[bytes],
    leakage: list[tuple[int, int]],
    true_hypothesis: dict[str, object],
) -> dict[str, object]:
    return solve_path(plaintexts, leakage, [true_hypothesis])


def one_byte_constraints(plaintext: list[z3.BitVecRef], reference: bytes):
    changed = [plaintext[index] != z3.BitVecVal(reference[index], 8) for index in range(16)]
    return [z3.Sum([z3.If(item, 1, 0) for item in changed]) == 1]


def concrete_leakage(builder, query_id: str, base_id: str, hypothesis: dict[str, object]):
    bit_index = int(hypothesis["bit_index"])
    values = []
    for round_index in range(1, DEPTH + 1):
        query_bit = select_bit(builder.graphs[query_id][round_index]["MC"], bit_index)
        base_bit = select_bit(builder.graphs[base_id][round_index]["MC"], bit_index)
        values.append(query_bit ^ base_bit)
    return values


def separator_for_pair(
    plaintexts: list[bytes],
    key_a: bytes,
    hypothesis_a: dict[str, object],
    key_b: bytes,
    hypothesis_b: dict[str, object],
) -> dict[str, object]:
    reference = plaintexts[0]
    symbolic_plaintext = [z3.BitVec(f"separator_p{index}", 8) for index in range(16)]
    key_a_values = [z3.BitVecVal(value, 8) for value in key_a]
    key_b_values = [z3.BitVecVal(value, 8) for value in key_b]
    builder_a = AESGraphBuilder(DEPTH, key_a_values, SBOX_ENCODING)
    builder_b = AESGraphBuilder(DEPTH, key_b_values, SBOX_ENCODING)
    builder_a.build_for_plaintext(reference, "separator_a_base")
    builder_b.build_for_plaintext(reference, "separator_b_base")
    builder_a.build_for_plaintext(symbolic_plaintext, "separator_a_query")
    builder_b.build_for_plaintext(symbolic_plaintext, "separator_b_query")
    leakage_a = concrete_leakage(builder_a, "separator_a_query", "separator_a_base", hypothesis_a)
    leakage_b = concrete_leakage(builder_b, "separator_b_query", "separator_b_base", hypothesis_b)

    solver = z3.Solver()
    solver.add(*builder_a.sbox_constraints, *builder_b.sbox_constraints)
    solver.add(*one_byte_constraints(symbolic_plaintext, reference))
    solver.add(z3.Or(*[left != right for left, right in zip(leakage_a, leakage_b)]))
    for previous in plaintexts:
        solver.add(z3.Or(*[
            symbolic_plaintext[index] != z3.BitVecVal(previous[index], 8)
            for index in range(16)
        ]))
    started = time.perf_counter()
    result = solver.check()
    elapsed = time.perf_counter() - started
    row: dict[str, object] = {
        "status": status_name(result),
        "elapsed_seconds": elapsed,
        "synthesis_mode": "pair_hypothesis_one_byte",
    }
    if result == z3.sat:
        model = solver.model()
        point = bytes(model.eval(value, model_completion=True).as_long() for value in symbolic_plaintext)
        row["plaintext_hex"] = point.hex()
    elif result == z3.unknown:
        row["reason_unknown"] = solver.reason_unknown()
    return row


def load_campaign_rows() -> list[dict[str, object]]:
    path = DISCOVERY_ROOT / "results" / "discovery_trials" / "discovery_results.json"
    return json.loads(path.read_text())


def load_trial(trial_id: str) -> tuple[dict, dict, dict, dict]:
    directory = DISCOVERY_ROOT / "results" / "discovery_trials"
    anonymous = json.loads((directory / f"{trial_id}.anonymous.json").read_text())
    ground_truth = json.loads((directory / f"{trial_id}.ground_truth.json").read_text())
    discovery_result = next(row["discovery"] for row in load_campaign_rows() if row["trial_id"] == trial_id)
    observation = json.loads((directory / f"{trial_id}.observation.json").read_text())
    return anonymous, ground_truth, discovery_result, observation


def run_positive(trial_id: str, initial_query_count: int, max_adaptive_queries: int) -> dict[str, object]:
    _, ground_truth, discovery_result, observation = load_trial(trial_id)
    key, true_bit = trial_key_and_true_bit(ground_truth)
    selected_slot = observation["scan_slot"]
    selected_row = discovery_result["ranked_slots"][0]
    column = int(selected_row["closest_mc_column"])
    hypotheses = make_hypotheses(column)
    true_hypothesis = next((h for h in hypotheses if int(h["bit_index"]) == true_bit), None)
    plaintexts = coarse_plaintexts()[: initial_query_count + 1]
    steps = []
    terminal = "query_budget_exhausted"

    for step in range(max_adaptive_queries + 1):
        oracle_document, leakage = render_temporal_transcript(key, true_bit, plaintexts)
        known = solve_known_path(plaintexts, leakage, true_hypothesis) if true_hypothesis else {"classification": "mapping_not_in_hypotheses"}
        attacker = solve_path(plaintexts, leakage, hypotheses)
        record: dict[str, object] = {
            "step": step,
            "query_count_excluding_base": len(plaintexts) - 1,
            "known_function": {k: v for k, v in known.items() if k != "first" or True},
            "attacker_hypothesis_union": {k: v for k, v in attacker.items() if k not in {"first", "second"}},
            "attacker_first_status": attacker["first"]["status"],
            "attacker_second_status": attacker["second"]["status"],
            "attacker_first_matching_hypotheses": attacker["first"].get("matching_hypotheses", []),
            "attacker_second_matching_hypotheses": attacker["second"].get("matching_hypotheses", []),
        }
        if attacker["classification"] == "full_key_unique":
            record["terminal"] = "full_key_unique"
            terminal = "full_key_unique"
            steps.append(record)
            break
        if attacker["classification"] != "ambiguity":
            record["terminal"] = attacker["classification"]
            terminal = str(attacker["classification"])
            steps.append(record)
            break
        if step == max_adaptive_queries:
            record["terminal"] = "query_budget_exhausted"
            steps.append(record)
            break

        first_key = attacker["first"]["candidate_key"]
        second_key = attacker["second"]["candidate_key"]
        first_hypothesis_id = attacker["first"]["matching_hypotheses"][0]
        second_hypothesis_id = attacker["second"]["matching_hypotheses"][0]
        by_id = {str(h["hypothesis_id"]): h for h in hypotheses}
        separator = separator_for_pair(
            plaintexts,
            first_key,
            by_id[first_hypothesis_id],
            second_key,
            by_id[second_hypothesis_id],
        )
        record["separator"] = {k: v for k, v in separator.items() if k != "plaintext_hex"}
        if separator["status"] != "sat":
            record["terminal"] = "separator_unresolved" if separator["status"] == "unknown" else "pair_observationally_equivalent"
            terminal = str(record["terminal"])
            steps.append(record)
            break
        point = bytes.fromhex(str(separator["plaintext_hex"]))
        plaintexts.append(point)
        record["separator_plaintext_hex"] = point.hex()
        steps.append(record)

    final = steps[-1]
    attacker_unique = terminal == "full_key_unique"
    known_unique = final["known_function"].get("classification") == "full_key_unique"
    attacker_first = final.get("attacker_first_matching_hypotheses", [])
    return {
        "trial_id": trial_id,
        "cohort": "positive",
        "selected_slot": selected_slot,
        "discovered_column": column,
        "hypothesis_count": len(hypotheses),
        "true_function_retained": true_hypothesis is not None,
        "true_bit_index_evaluation_only": true_bit,
        "known_function_unique": known_unique,
        "attacker_key_unique": attacker_unique,
        "attacker_function_hypotheses_at_final_first_model": attacker_first,
        "terminal": terminal,
        "steps": steps,
    }


def run_negative(trial_id: str) -> dict[str, object]:
    row = next(item for item in load_campaign_rows() if item["trial_id"] == trial_id)
    discovery = row["discovery"]
    return {
        "trial_id": trial_id,
        "cohort": "negative",
        "selected_slot": discovery["selected_slot"],
        "support_consistent_candidate_count": discovery["support_consistent_candidate_count"],
        "false_positive": discovery["selected_slot"] is not None,
        "terminal": "no_channel_selected" if discovery["selected_slot"] is None else "unexpected_channel",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive-limit", type=int, default=2)
    parser.add_argument("--negative-limit", type=int, default=2)
    parser.add_argument("--initial-query-count", type=int, default=16)
    parser.add_argument("--max-adaptive-queries", type=int, default=4)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    global BRANCH_WORKERS
    BRANCH_WORKERS = max(1, int(args.workers))

    rows = load_campaign_rows()
    positives = [row["trial_id"] for row in rows if row["cohort"] == "positive"][: args.positive_limit]
    negatives = [row["trial_id"] for row in rows if row["cohort"] == "negative"][: args.negative_limit]
    results = {
        "schema": "mc-channel-hypothesis-bridge-v1",
        "settings": {
            "depth": DEPTH,
            "initial_query_count_excluding_base": args.initial_query_count,
            "max_adaptive_queries": args.max_adaptive_queries,
            "query_domain": "one_byte",
            "hypotheses_per_column": 32,
            "sbox_encoding": SBOX_ENCODING,
            "branch_workers": BRANCH_WORKERS,
        },
        "positive": [run_positive(trial_id, args.initial_query_count, args.max_adaptive_queries) for trial_id in positives],
        "negative": [run_negative(trial_id) for trial_id in negatives],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
