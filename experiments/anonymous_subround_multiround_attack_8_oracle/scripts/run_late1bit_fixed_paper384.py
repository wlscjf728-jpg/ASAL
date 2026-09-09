"""Classify fixed q128 one-bit late leakage before adaptive recovery."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import yaml

from adaptive_query_attack import solver_result
from experiment_common import ROOT, append_jsonl, key_for_seed, load_candidate_map, nested_plaintexts, read_csv, taps_for_case
from oracle import generate_observation
from run_phase8_campaign import write_atomic


RESULT_SCHEMA = "late-1bit-fixed-q128-result-v1"
RUN_TAG = "late1bit_fixed_q128_paper384"
MAX_WORKERS = 64


@dataclass(frozen=True)
class RunTask:
    run_id: str
    case: dict[str, str]
    seed: int
    taps: tuple[dict[str, object], ...]
    query_count: int
    config: dict
    result_path: Path


def run_id(case: dict[str, str], seed: int) -> str:
    return f"{case['case_id']}__seed{seed}__{RUN_TAG}"


def _rooted(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _validate_config(config: dict) -> None:
    if config["campaign"]["seeds"] != [0, 1, 2]:
        raise ValueError("late one-bit fixed baseline requires seeds [0, 1, 2]")
    if int(config["campaign"]["workers"]) > MAX_WORKERS:
        raise ValueError("late one-bit fixed baseline workers must not exceed 32")
    attack = config["attack"]
    if (int(attack["depth"]), attack["mode"], int(attack["query_count"])) != (2, "differential", 128):
        raise ValueError("late one-bit fixed baseline requires depth=2, differential, q128")
    for name in ("first_timeout_ms", "second_timeout_ms"):
        if int(config["solver"][name]) != 0:
            raise ValueError(f"{name} must be 0 (unlimited)")


def _is_terminal(path: Path, expected_run_id: str) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    return payload.get("schema") == RESULT_SCHEMA and payload.get("run_id") == expected_run_id and payload.get("state") == "terminal"


def load_tasks(config: dict, result_dir: Path | None = None) -> list[RunTask]:
    _validate_config(config)
    result_dir = result_dir or _rooted(config["paths"]["result_dir"])
    candidate_map = load_candidate_map()
    cases = read_csv(_rooted(config["paths"]["manifest"]))
    if len(cases) != 128 or len({case["case_id"] for case in cases}) != 128:
        raise ValueError("paper384 manifest must contain 128 unique cases")

    tasks = []
    for case in cases:
        candidate = candidate_map[case["candidate_id"]]
        if candidate["stage"] != case["stage"] or int(candidate["bit_index"]) != int(case["bit_index"]):
            raise ValueError(f"manifest/candidate mismatch: {case['case_id']}")
        taps = tuple(taps_for_case({"cand_a": case["candidate_id"]}, candidate_map))
        if len(taps) != 1:
            raise ValueError(f"case does not define exactly one tap: {case['case_id']}")
        for seed in config["campaign"]["seeds"]:
            identifier = run_id(case, int(seed))
            result_path = result_dir / f"{identifier}.json"
            if _is_terminal(result_path, identifier):
                continue
            tasks.append(RunTask(identifier, dict(case), int(seed), taps, 128, config, result_path))
    return tasks


def run_fixed_baseline(task: RunTask) -> dict:
    attack = task.config["attack"]
    plaintexts = nested_plaintexts(task.query_count, task.seed)
    document = generate_observation(
        key_for_seed(task.seed), list(task.taps), plaintexts, int(attack["depth"]), attack["mode"]
    )
    result = solver_result(document, task.config)
    statuses = (result.get("first_result"), result.get("second_result"))
    if statuses == ("sat", "unsat"):
        terminal = "fixed_query_unique"
        eligible = False
    elif statuses == ("sat", "sat"):
        terminal = "finite_query_ambiguity"
        eligible = True
    else:
        return {
            "schema": RESULT_SCHEMA,
            "state": "nonterminal",
            "run_id": task.run_id,
            "case_id": task.case["case_id"],
            "seed": task.seed,
            "terminal_classification": "solver_unresolved",
            "phase2_eligible": False,
            "solver": result,
        }
    return {
        "schema": RESULT_SCHEMA,
        "state": "terminal",
        "run_id": task.run_id,
        "case_id": task.case["case_id"],
        "candidate_id": task.case["candidate_id"],
        "tap": task.taps[0],
        "seed": task.seed,
        "query_count": task.query_count,
        "oracle_encryptions": task.query_count + 1,
        "terminal_classification": terminal,
        "phase2_eligible": eligible,
        "solver": result,
    }


def execute_task(task: RunTask) -> dict:
    started = time.perf_counter()
    try:
        payload = run_fixed_baseline(task)
    except BaseException as error:
        payload = {
            "schema": RESULT_SCHEMA,
            "state": "error",
            "run_id": task.run_id,
            "case_id": task.case["case_id"],
            "seed": task.seed,
            "error": repr(error),
            "traceback": traceback.format_exc(),
        }
    payload["wall_time"] = time.perf_counter() - started
    return payload


def _dry_run_line(config: dict, pending: int, requested: int | None) -> str:
    workers = min(pending, int(config["campaign"]["workers"]), requested or int(config["campaign"]["workers"]), MAX_WORKERS)
    return f"cases=128 seeds=3 runs=384 pending={pending} workers={workers} fixed=q128 depth=2 mode=differential"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/late_1bit_fixed_q128.yaml")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--result-dir")
    parser.add_argument("--summary")
    parser.add_argument("--errors")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(_rooted(args.config).read_text())
    result_dir = _rooted(args.result_dir or config["paths"]["result_dir"])
    summary_path = _rooted(args.summary or config["paths"]["summary"])
    errors = _rooted(args.errors or config["paths"]["errors"])
    tasks = load_tasks(config, result_dir)
    print(_dry_run_line(config, len(tasks), args.workers), flush=True)
    if args.dry_run or not tasks:
        return

    result_dir.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    workers = min(len(tasks), int(config["campaign"]["workers"]), args.workers or int(config["campaign"]["workers"]), MAX_WORKERS)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(execute_task, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            payload = future.result()
            if payload["state"] == "terminal":
                write_atomic(task.result_path, payload)
                terminal_rows = [path.read_text() for path in sorted(result_dir.glob("*.json"))]
                write_atomic(summary_path, {"rows": terminal_rows})
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(errors, payload)
                outcome = payload["terminal_classification"] if payload["state"] == "nonterminal" else "error"
            print(f"[{index}/{len(tasks)}] {task.run_id} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
