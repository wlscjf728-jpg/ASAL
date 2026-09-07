"""Attack 8 fixed-budget and solver-guided adaptive query evaluator."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml
import z3

from experiment_common import (
    ROOT,
    append_jsonl,
    key_for_seed,
    load_candidate_map,
    nested_plaintexts,
    read_csv,
    taps_for_case,
)
from oracle import generate_observation
from solve_known_mapping import solve_document
from z3_aes import AESGraphBuilder, select_bit


def timed_check(solver: z3.Solver, timeout_ms: int | None) -> tuple[z3.CheckSatResult, float, str]:
    solver.set(timeout=0 if timeout_ms is None else timeout_ms)
    started = time.perf_counter()
    result = solver.check()
    elapsed = time.perf_counter() - started
    reason = solver.reason_unknown() if result == z3.unknown else ""
    return result, elapsed, reason


def transcript_side(doc: dict, prefix: str, sbox_encoding: str):
    experiment = doc["experiment"]
    depth = int(experiment["depth"])
    key = [z3.BitVec(f"{prefix}_k_{index}", 8) for index in range(16)]
    builder = AESGraphBuilder(depth, key, sbox_encoding)
    for observation in doc["observations"]:
        builder.build_for_plaintext(
            bytes.fromhex(observation["plaintext_hex"]),
            f"{prefix}_obs_{observation['query_id']}",
        )

    tap_index = {tap["tap_id"]: tap for tap in experiment["taps"]}
    base_id = f"{prefix}_obs_{experiment.get('base_query_id', 0)}"
    constraints = list(builder.sbox_constraints)
    for observation in doc["observations"]:
        query_id = f"{prefix}_obs_{observation['query_id']}"
        for round_index in range(1, depth + 1):
            for tap_id, tap in tap_index.items():
                values = observation["rounds"][str(round_index)][tap_id]
                query_bit = select_bit(
                    builder.graphs[query_id][round_index][tap["stage"]],
                    int(tap["bit_index"]),
                )
                base_bit = select_bit(
                    builder.graphs[base_id][round_index][tap["stage"]],
                    int(tap["bit_index"]),
                )
                if experiment["mode"] in {"absolute", "combined"}:
                    constraints.append(query_bit == z3.BitVecVal(int(values["absolute"]), 1))
                if experiment["mode"] in {"differential", "combined"}:
                    constraints.append(
                        (query_bit ^ base_bit) == z3.BitVecVal(int(values["differential"]), 1)
                    )
    return key, builder, constraints, base_id


def leakage_vector(builder, query_id: str, base_id: str, experiment: dict) -> list[z3.BitVecRef]:
    vector = []
    for round_index in range(1, int(experiment["depth"]) + 1):
        for tap in experiment["taps"]:
            query_bit = select_bit(
                builder.graphs[query_id][round_index][tap["stage"]],
                int(tap["bit_index"]),
            )
            base_bit = select_bit(
                builder.graphs[base_id][round_index][tap["stage"]],
                int(tap["bit_index"]),
            )
            if experiment["mode"] in {"absolute", "combined"}:
                vector.append(query_bit)
            if experiment["mode"] in {"differential", "combined"}:
                vector.append(query_bit ^ base_bit)
    return vector


def plaintext_domain_constraints(
    symbolic_plaintext: list[z3.BitVecRef],
    reference: bytes,
    domain: str,
    max_active_bytes: int,
) -> list[z3.BoolRef]:
    changed = [symbolic_plaintext[index] != z3.BitVecVal(reference[index], 8) for index in range(16)]
    active_count = z3.Sum([z3.If(item, 1, 0) for item in changed])
    if domain == "one_byte":
        return [active_count == 1]
    if domain == "bounded":
        return [active_count >= 1, active_count <= max_active_bytes]
    if domain == "unrestricted":
        return [active_count >= 1]
    raise ValueError(f"unsupported query domain: {domain}")


def synthesize_distinguishing_query(
    doc: dict,
    sbox_encoding: str,
    timeout_ms: int | None,
    query_domain: str,
    max_active_bytes: int,
) -> dict[str, object]:
    experiment = doc["experiment"]
    key1, builder1, constraints1, base1 = transcript_side(doc, "sep1", sbox_encoding)
    key2, builder2, constraints2, base2 = transcript_side(doc, "sep2", sbox_encoding)

    plaintext = [z3.BitVec(f"adaptive_p_{index}", 8) for index in range(16)]
    query1 = "sep1_symbolic_query"
    query2 = "sep2_symbolic_query"
    builder1.build_for_plaintext(plaintext, query1)
    builder2.build_for_plaintext(plaintext, query2)

    leakage1 = leakage_vector(builder1, query1, base1, experiment)
    leakage2 = leakage_vector(builder2, query2, base2, experiment)
    if len(leakage1) != len(leakage2) or not leakage1:
        raise ValueError("empty or inconsistent leakage vectors")

    reference = bytes.fromhex(doc["observations"][int(experiment.get("base_query_id", 0))]["plaintext_hex"])
    solver = z3.Solver()
    solver.add(*constraints1, *constraints2)
    solver.add(z3.Or(*[left != right for left, right in zip(key1, key2)]))
    solver.add(z3.Or(*[left != right for left, right in zip(leakage1, leakage2)]))
    solver.add(*plaintext_domain_constraints(plaintext, reference, query_domain, max_active_bytes))

    for observation in doc["observations"]:
        previous = bytes.fromhex(observation["plaintext_hex"])
        solver.add(z3.Or(*[
            plaintext[index] != z3.BitVecVal(previous[index], 8) for index in range(16)
        ]))

    status, elapsed, reason = timed_check(solver, timeout_ms)
    result = {
        "status": str(status).lower(),
        "elapsed": elapsed,
        "reason_unknown": reason,
        "query_domain": query_domain,
    }
    if status != z3.sat:
        return result

    model = solver.model()
    point = bytes(model.eval(value, model_completion=True).as_long() for value in plaintext)
    candidate1 = bytes(model.eval(value, model_completion=True).as_long() for value in key1)
    candidate2 = bytes(model.eval(value, model_completion=True).as_long() for value in key2)
    result.update({
        "plaintext_hex": point.hex(),
        "candidate1_hex": candidate1.hex(),
        "candidate2_hex": candidate2.hex(),
        "candidate_hamming_bits": sum((a ^ b).bit_count() for a, b in zip(candidate1, candidate2)),
        "predicted_leakage_width": len(leakage1),
    })
    return result


def synthesize_for_candidate_pair(
    doc: dict,
    candidate1_hex: str,
    candidate2_hex: str,
    sbox_encoding: str,
    timeout_ms: int | None,
    query_domain: str,
    max_active_bytes: int,
) -> dict[str, object]:
    """Find a query for the concrete first/alternative models from the second solve."""
    experiment = doc["experiment"]
    depth = int(experiment["depth"])
    key1_bytes = bytes.fromhex(candidate1_hex)
    key2_bytes = bytes.fromhex(candidate2_hex)
    key1 = [z3.BitVecVal(value, 8) for value in key1_bytes]
    key2 = [z3.BitVecVal(value, 8) for value in key2_bytes]
    builder1 = AESGraphBuilder(depth, key1, sbox_encoding)
    builder2 = AESGraphBuilder(depth, key2, sbox_encoding)

    base_index = int(experiment.get("base_query_id", 0))
    reference = bytes.fromhex(doc["observations"][base_index]["plaintext_hex"])
    base1 = "pair1_base"
    base2 = "pair2_base"
    query1 = "pair1_symbolic"
    query2 = "pair2_symbolic"
    plaintext = [z3.BitVec(f"pair_p_{index}", 8) for index in range(16)]
    builder1.build_for_plaintext(reference, base1)
    builder2.build_for_plaintext(reference, base2)
    builder1.build_for_plaintext(plaintext, query1)
    builder2.build_for_plaintext(plaintext, query2)

    leakage1 = leakage_vector(builder1, query1, base1, experiment)
    leakage2 = leakage_vector(builder2, query2, base2, experiment)
    solver = z3.Solver()
    solver.add(*builder1.sbox_constraints, *builder2.sbox_constraints)
    solver.add(z3.Or(*[left != right for left, right in zip(leakage1, leakage2)]))
    solver.add(*plaintext_domain_constraints(plaintext, reference, query_domain, max_active_bytes))
    for observation in doc["observations"]:
        previous = bytes.fromhex(observation["plaintext_hex"])
        solver.add(z3.Or(*[
            plaintext[index] != z3.BitVecVal(previous[index], 8) for index in range(16)
        ]))

    status, elapsed, reason = timed_check(solver, timeout_ms)
    result = {
        "status": str(status).lower(),
        "elapsed": elapsed,
        "reason_unknown": reason,
        "query_domain": query_domain,
        "synthesis_mode": "fixed_candidate_pair",
        "candidate1_hex": candidate1_hex,
        "candidate2_hex": candidate2_hex,
        "candidate_hamming_bits": sum((a ^ b).bit_count() for a, b in zip(key1_bytes, key2_bytes)),
    }
    if status == z3.sat:
        model = solver.model()
        point = bytes(model.eval(value, model_completion=True).as_long() for value in plaintext)
        result["plaintext_hex"] = point.hex()
        result["predicted_leakage_width"] = len(leakage1)
    return result


def solver_result(doc: dict, config: dict) -> dict:
    solver = config["solver"]
    return solve_document(
        doc,
        first_timeout_ms=solver["first_timeout_ms"],
        second_timeout_ms=solver["second_timeout_ms"],
        diagnostic_timeout_ms=solver["diagnostic_timeout_ms"],
        sbox_encoding=solver["sbox_encoding"],
    )


def fixed_nested_run(case: dict[str, str], seed: int, config: dict, taps: list[dict]) -> dict:
    attack = config["attack"]
    key = key_for_seed(seed)
    attempts = []
    final = None
    for query_count in attack["fixed_query_ladder"]:
        plaintexts = nested_plaintexts(int(query_count), seed)
        doc = generate_observation(key, taps, plaintexts, attack["depth"], attack["mode"])
        result = solver_result(doc, config)
        attempts.append({
            "query_count": query_count,
            "classification": result["classification"],
            "first_result": result["first_result"],
            "second_result": result["second_result"],
            "first_time": result["first_time"],
            "second_time": result["second_time"],
            "reason_unknown": result.get("z3_reason_unknown", ""),
        })
        final = result
        if result["classification"] == "full_key_unique":
            terminal = "full_key_unique"
            break
        if result["classification"] == "undecided":
            terminal = "solver_unresolved"
            break
    else:
        terminal = "finite_budget_ambiguity" if final["classification"] == "ambiguity" else final["classification"]

    return {
        "run_id": f"{case['attack8_case_id']}__seed{seed}__fixed_nested",
        "attack8_case_id": case["attack8_case_id"],
        "source_phase": case["source_phase"],
        "source_case_id": case["source_case_id"],
        "tap_count": int(case["tap_count"]),
        "seed": seed,
        "strategy": "fixed_nested",
        "terminal_classification": terminal,
        "query_count": int(attempts[-1]["query_count"]),
        "oracle_encryptions": int(attempts[-1]["query_count"]) + 1,
        "attempts": attempts,
        "solver_result": final,
    }


def adaptive_run(case: dict[str, str], seed: int, config: dict, taps: list[dict]) -> dict:
    attack = config["attack"]
    adaptive = config["adaptive_query"]
    key = key_for_seed(seed)
    plaintexts = nested_plaintexts(int(attack["initial_query_count"]), seed)
    steps = []

    for step in range(int(adaptive["max_adaptive_queries"]) + 1):
        doc = generate_observation(key, taps, plaintexts, attack["depth"], attack["mode"])
        result = solver_result(doc, config)
        record = {
            "step": step,
            "query_count": len(plaintexts) - 1,
            "classification": result["classification"],
            "first_result": result["first_result"],
            "second_result": result["second_result"],
            "first_time": result["first_time"],
            "second_time": result["second_time"],
        }

        if result["classification"] == "full_key_unique":
            record["terminal"] = "full_key_unique"
            steps.append(record)
            terminal = "full_key_unique"
            break
        if result["classification"] != "ambiguity":
            record["terminal"] = "solver_unresolved"
            steps.append(record)
            terminal = "solver_unresolved"
            break
        if step == int(adaptive["max_adaptive_queries"]):
            record["terminal"] = "query_budget_exhausted"
            steps.append(record)
            terminal = "query_budget_exhausted"
            break

        if adaptive.get("synthesis_mode", "fixed_pair") == "joint":
            separating = synthesize_distinguishing_query(
                doc,
                config["solver"]["sbox_encoding"],
                adaptive["separability_timeout_ms"],
                adaptive["query_domain"],
                adaptive["max_active_bytes"],
            )
        else:
            separating = synthesize_for_candidate_pair(
                doc,
                result["first_model_hex"],
                result["alternative_model"],
                config["solver"]["sbox_encoding"],
                adaptive["separability_timeout_ms"],
                adaptive["query_domain"],
                adaptive["max_active_bytes"],
            )
        record["separability"] = separating
        if separating["status"] == "unsat":
            terminal = (
                "support_limited_ambiguity"
                if adaptive.get("synthesis_mode", "fixed_pair") == "joint"
                else "selected_pair_observationally_equivalent"
            )
            record["terminal"] = terminal
            steps.append(record)
            break
        if separating["status"] != "sat":
            record["terminal"] = "separability_unresolved"
            steps.append(record)
            terminal = "separability_unresolved"
            break

        point = bytes.fromhex(str(separating["plaintext_hex"]))
        if point in plaintexts:
            raise AssertionError("separability solver returned a duplicate plaintext")
        plaintexts.append(point)
        steps.append(record)
    else:
        raise AssertionError("adaptive loop terminated without a classification")

    return {
        "run_id": f"{case['attack8_case_id']}__seed{seed}__adaptive_pairwise",
        "attack8_case_id": case["attack8_case_id"],
        "source_phase": case["source_phase"],
        "source_case_id": case["source_case_id"],
        "tap_count": int(case["tap_count"]),
        "seed": seed,
        "strategy": "adaptive_pairwise",
        "query_domain": adaptive["query_domain"],
        "terminal_classification": terminal,
        "query_count": len(plaintexts) - 1,
        "oracle_encryptions": len(plaintexts),
        "steps": steps,
    }


def existing_run_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    with path.open() as handle:
        for line in handle:
            if line.strip():
                ids.add(json.loads(line)["run_id"])
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="configs/selected_2bit_proven_ambiguous.csv")
    parser.add_argument("--strategy", choices=("fixed_nested", "adaptive_pairwise"), required=True)
    parser.add_argument("--config", default="configs/run_config.yaml")
    parser.add_argument("--output", default="results/attack_runs.jsonl")
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    cases = read_csv(ROOT / args.cases)
    if args.case_limit is not None:
        cases = cases[: args.case_limit]
    seed_count = args.seeds if args.seeds is not None else int(config["campaign"]["seeds"])
    candidate_map = load_candidate_map()
    output = ROOT / args.output
    completed = existing_run_ids(output)
    planned = []

    for case in cases:
        taps = taps_for_case(case, candidate_map)
        if len(taps) != int(case["tap_count"]):
            raise ValueError(f"tap-count mismatch for {case['attack8_case_id']}")
        for seed in range(seed_count):
            run_id = f"{case['attack8_case_id']}__seed{seed}__{args.strategy}"
            if run_id not in completed:
                planned.append((case, seed, taps))

    print(f"strategy={args.strategy} cases={len(cases)} seeds={seed_count} pending_runs={len(planned)}")
    if args.dry_run:
        for case, seed, taps in planned[:10]:
            print(case["attack8_case_id"], seed, [(tap["stage"], tap["bit_index"]) for tap in taps])
        return

    for index, (case, seed, taps) in enumerate(planned, start=1):
        started = time.perf_counter()
        if args.strategy == "fixed_nested":
            payload = fixed_nested_run(case, seed, config, taps)
        else:
            payload = adaptive_run(case, seed, config, taps)
        payload["wall_time"] = time.perf_counter() - started
        append_jsonl(output, payload)
        print(
            f"[{index}/{len(planned)}] {payload['run_id']} -> "
            f"{payload['terminal_classification']} q={payload['query_count']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
