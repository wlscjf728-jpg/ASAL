"""Run the complete 2/3/4-tap Phase 8 campaign with resumable workers."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import os
import time
import traceback
from pathlib import Path

import yaml

from adaptive_query_attack import (
    solver_result,
    synthesize_distinguishing_query,
    synthesize_for_candidate_pair,
)
from experiment_common import (
    ROOT,
    case_candidates,
    key_for_seed,
    load_candidate_map,
    nested_plaintexts,
    read_csv,
    taps_for_case,
)
from oracle import generate_observation


CASE_FILES = (
    "configs/selected_2bit_proven_ambiguous.csv",
    "configs/selected_3bit_proven_ambiguous.csv",
    "configs/selected_4bit_proven_ambiguous.csv",
)


def load_support(case_file: str) -> dict[str, set[int]]:
    tap_count = Path(case_file).name.split("bit", 1)[0].rsplit("_", 1)[-1]
    rows = read_csv(ROOT / f"reference/dependency_support_{tap_count}bit_candidates.csv")
    support: dict[str, set[int]] = {}
    for row in rows:
        support.setdefault(row["candidate_id"], set()).update(
            json.loads(row["structural_k0_bits_json"])
        )
    return support


def result_path(result_dir: Path, run_id: str) -> Path:
    return result_dir / f"{run_id}.json"


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n")
    temporary.replace(path)


def sound_adaptive_run(
    case: dict,
    seed: int,
    config: dict,
    taps: list[dict],
    *,
    run_tag: str = "phase8_full",
    require_initial_ambiguity: bool = False,
) -> dict:
    attack = config["attack"]
    adaptive = config["adaptive_query"]
    key = key_for_seed(seed)
    plaintexts = nested_plaintexts(int(attack["initial_query_count"]), seed)
    max_queries = int(adaptive["max_adaptive_queries"])
    steps = []

    for step in range(max_queries + 1):
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

        if step == 0 and require_initial_ambiguity and result["classification"] != "ambiguity":
            raise RuntimeError(
                "initial transcript is not ambiguous: "
                f"{result['first_result']}->{result['second_result']}"
            )

        if result["classification"] == "full_key_unique":
            terminal = "key_recovered"
            record["terminal"] = terminal
            steps.append(record)
            break
        if result["classification"] != "ambiguity":
            raise RuntimeError(
                f"unlimited uniqueness solve did not resolve: "
                f"{result['first_result']}->{result['second_result']}"
            )
        if step == max_queries:
            terminal = "non_recovery_within_q255"
            record["terminal"] = terminal
            steps.append(record)
            break

        fixed_pair = synthesize_for_candidate_pair(
            doc,
            result["first_model_hex"],
            result["alternative_model"],
            config["solver"]["sbox_encoding"],
            adaptive["separability_timeout_ms"],
            adaptive["query_domain"],
            adaptive["max_active_bytes"],
        )
        record["fixed_pair_separability"] = fixed_pair

        if fixed_pair["status"] == "sat":
            separating = fixed_pair
        elif fixed_pair["status"] == "unsat":
            separating = synthesize_distinguishing_query(
                doc,
                config["solver"]["sbox_encoding"],
                adaptive["separability_timeout_ms"],
                adaptive["query_domain"],
                adaptive["max_active_bytes"],
            )
            record["global_separability"] = separating
        else:
            raise RuntimeError(
                f"unlimited fixed-pair separator unresolved: {fixed_pair}"
            )

        if separating["status"] == "unsat":
            terminal = "proven_observational_non_recovery"
            record["terminal"] = terminal
            steps.append(record)
            break
        if separating["status"] != "sat":
            raise RuntimeError(
                f"unlimited global separator unresolved: {separating}"
            )

        point = bytes.fromhex(str(separating["plaintext_hex"]))
        if point in plaintexts:
            raise AssertionError("separator returned a duplicate plaintext")
        plaintexts.append(point)
        steps.append(record)
    else:
        raise AssertionError("adaptive loop ended without a verdict")

    return {
        "run_id": f"{case['attack8_case_id']}__seed{seed}__{run_tag}",
        "attack8_case_id": case["attack8_case_id"],
        "source_phase": case["source_phase"],
        "source_case_id": case["source_case_id"],
        "tap_count": int(case["tap_count"]),
        "seed": seed,
        "strategy": "sound_hybrid_adaptive",
        "query_domain": adaptive["query_domain"],
        "terminal_classification": terminal,
        "attack_success": terminal == "key_recovered",
        "query_count": len(plaintexts) - 1,
        "oracle_encryptions": len(plaintexts),
        "steps": steps,
    }


def execute_task(task: tuple[dict, int, list[dict], dict]) -> dict:
    case, seed, taps, config = task
    run_id = f"{case['attack8_case_id']}__seed{seed}__phase8_full"
    started = time.perf_counter()
    try:
        if case["support_complete"] != "1":
            payload = {
                "run_id": run_id,
                "attack8_case_id": case["attack8_case_id"],
                "source_phase": case["source_phase"],
                "source_case_id": case["source_case_id"],
                "tap_count": int(case["tap_count"]),
                "seed": seed,
                "strategy": "structural_support_proof",
                "terminal_classification": "proven_structural_non_recovery",
                "attack_success": False,
                "support_k0_bit_count": int(case["support_k0_bit_count"]),
                "query_count": 0,
                "oracle_encryptions": 0,
            }
        else:
            payload = sound_adaptive_run(case, seed, config, taps)
            payload["support_k0_bit_count"] = 128
        payload["wall_time"] = time.perf_counter() - started
        return payload
    except BaseException as error:
        return {
            "run_id": run_id,
            "attack8_case_id": case["attack8_case_id"],
            "tap_count": int(case["tap_count"]),
            "seed": seed,
            "terminal_classification": "worker_error",
            "error": repr(error),
            "traceback": traceback.format_exc(),
            "wall_time": time.perf_counter() - started,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/full_phase8_campaign.yaml")
    parser.add_argument("--result-dir", default="results/phase8_full_runs")
    parser.add_argument("--summary", default="results/phase8_full_summary.jsonl")
    parser.add_argument("--errors", default="logs/phase8_full_errors.jsonl")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    workers = args.workers or int(config["campaign"]["workers"])
    seeds = args.seeds or int(config["campaign"]["seeds"])
    result_dir = ROOT / args.result_dir
    summary = ROOT / args.summary
    errors = ROOT / args.errors
    candidate_map = load_candidate_map()
    tasks = []
    case_count = 0
    support_complete_count = 0

    for case_file in CASE_FILES:
        support = load_support(case_file)
        for source_case in read_csv(ROOT / case_file):
            case_count += 1
            covered = set()
            for candidate_id in case_candidates(source_case):
                covered.update(support[candidate_id])
            case = dict(source_case)
            case["support_k0_bit_count"] = str(len(covered))
            case["support_complete"] = "1" if len(covered) == 128 else "0"
            support_complete_count += int(case["support_complete"])
            taps = taps_for_case(case, candidate_map)
            for seed in range(seeds):
                run_id = f"{case['attack8_case_id']}__seed{seed}__phase8_full"
                if not result_path(result_dir, run_id).exists():
                    tasks.append((case, seed, taps, config))

    print(
        f"cases={case_count} support_complete={support_complete_count} "
        f"seeds={seeds} workers={workers} pending={len(tasks)}",
        flush=True,
    )
    if args.dry_run:
        return

    result_dir.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, mp_context=context
    ) as pool:
        futures = [pool.submit(execute_task, task) for task in tasks]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            payload = future.result()
            if payload["terminal_classification"] == "worker_error":
                with errors.open("a") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
            else:
                write_atomic(result_path(result_dir, payload["run_id"]), payload)
                with summary.open("a") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
            print(
                f"[{index}/{len(tasks)}] {payload['run_id']} -> "
                f"{payload['terminal_classification']} "
                f"q={payload.get('query_count', '-')}",
                flush=True,
            )


if __name__ == "__main__":
    main()
