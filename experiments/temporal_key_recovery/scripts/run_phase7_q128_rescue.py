"""Resolve the six direct Phase 7 q128 early+late ambiguity runs."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import time
import traceback
from pathlib import Path

import yaml

from adaptive_query_attack import solver_result
from experiment_common import (
    ROOT,
    key_for_seed,
    load_candidate_map,
    nested_plaintexts,
    read_csv,
    taps_for_case,
)
from oracle import generate_observation
from run_phase8_campaign import result_path, sound_adaptive_run, write_atomic

MANIFEST = "configs/phase7_q128_rescue_cases.csv"
RUN_TAG = "phase7_q128_rescue"


def load_tasks(
    config: dict,
    result_dir: Path,
    *,
    include_completed: bool = False,
) -> list[tuple[dict, int, list[dict], dict]]:
    candidate_map = load_candidate_map()
    tasks = []
    for case in read_csv(ROOT / MANIFEST):
        seed = int(case["seed"])
        run_id = f"{case['attack8_case_id']}__seed{seed}__{RUN_TAG}"
        if include_completed or not result_path(result_dir, run_id).exists():
            tasks.append((case, seed, taps_for_case(case, candidate_map), config))
    return tasks


def validate_baseline_task(task: tuple[dict, int, list[dict], dict]) -> dict:
    case, seed, taps, config = task
    doc = generate_observation(
        key_for_seed(seed),
        taps,
        nested_plaintexts(128, seed),
        2,
        "differential",
    )
    result = solver_result(doc, config)
    if result["first_result"] != "sat" or result["second_result"] != "sat":
        raise RuntimeError(
            f"baseline mismatch for {case['source_case_id']} seed {seed}: "
            f"{result['first_result']}->{result['second_result']}"
        )
    return {
        "source_case_id": case["source_case_id"],
        "seed": seed,
        "first_result": result["first_result"],
        "second_result": result["second_result"],
    }


def execute_rescue_task(task: tuple[dict, int, list[dict], dict]) -> dict:
    case, seed, taps, config = task
    run_id = f"{case['attack8_case_id']}__seed{seed}__{RUN_TAG}"
    started = time.perf_counter()
    try:
        payload = sound_adaptive_run(
            case,
            seed,
            config,
            taps,
            run_tag=RUN_TAG,
            require_initial_ambiguity=True,
        )
        payload["source_query_count"] = int(case["source_query_count"])
        payload["baseline_verified"] = True
        payload["wall_time"] = time.perf_counter() - started
        return payload
    except BaseException as error:
        return {
            "run_id": run_id,
            "attack8_case_id": case["attack8_case_id"],
            "source_case_id": case["source_case_id"],
            "seed": seed,
            "terminal_classification": "worker_error",
            "error": repr(error),
            "traceback": traceback.format_exc(),
            "wall_time": time.perf_counter() - started,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase7_q128_rescue.yaml")
    parser.add_argument("--result-dir", default="results/phase7_q128_rescue_runs")
    parser.add_argument("--summary", default="results/phase7_q128_rescue_summary.jsonl")
    parser.add_argument("--errors", default="logs/phase7_q128_rescue_errors.jsonl")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate-baseline", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    workers = min(args.workers, int(config["campaign"]["workers"]))
    result_dir = ROOT / args.result_dir
    summary = ROOT / args.summary
    errors = ROOT / args.errors
    tasks = load_tasks(config, result_dir)
    print(
        f"targets=6 workers={workers} pending={len(tasks)} initial_q=128 final_q=255",
        flush=True,
    )
    if args.dry_run:
        for case, seed, taps, _ in tasks:
            print(
                case["source_case_id"],
                seed,
                [(tap["stage"], tap["bit_index"]) for tap in taps],
            )
        return

    if args.validate_baseline:
        baseline_tasks = load_tasks(config, result_dir, include_completed=True)
        context = multiprocessing.get_context("spawn")
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
        ) as pool:
            for result in pool.map(validate_baseline_task, baseline_tasks):
                print(
                    f"baseline {result['source_case_id']} seed={result['seed']} -> "
                    f"{result['first_result']}->{result['second_result']}",
                    flush=True,
                )
        return

    result_dir.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
    ) as pool:
        futures = [pool.submit(execute_rescue_task, task) for task in tasks]
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
