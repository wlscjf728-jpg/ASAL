"""Pair-separator adaptive recovery for q128 one-bit ambiguity runs."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import yaml

from adaptive_query_attack import solver_result, synthesize_distinguishing_query, synthesize_for_candidate_pair
from experiment_common import ROOT, append_jsonl, key_for_seed, nested_plaintexts
from oracle import generate_observation
from run_phase8_campaign import write_atomic


BASELINE_SCHEMA = "late-1bit-fixed-q128-result-v1"
CHECKPOINT_SCHEMA = "late-1bit-pair-rescue-checkpoint-v1"
RESULT_SCHEMA = "late-1bit-pair-rescue-result-v1"
RUN_TAG = "late1bit_pair_rescue_paper384"
MAX_WORKERS = 64


@dataclass(frozen=True)
class RunTask:
    run_id: str
    case: dict[str, str]
    seed: int
    taps: tuple[dict[str, object], ...]
    query_count: int
    config: dict
    checkpoint_path: Path
    result_path: Path


def run_id(case: dict[str, str], seed: int) -> str:
    return f"{case['case_id']}__seed{seed}__{RUN_TAG}"


def _rooted(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _validate_config(config: dict) -> None:
    attack = config["attack"]
    if not 1 <= int(config["campaign"]["workers"]) <= MAX_WORKERS:
        raise ValueError(f"pair rescue workers must be between 1 and {MAX_WORKERS}")
    if (int(attack["depth"]), attack["mode"], int(attack["initial_query_count"])) != (2, "differential", 128):
        raise ValueError("pair rescue requires depth=2, differential, q128")
    for name in ("first_timeout_ms", "second_timeout_ms", "separability_timeout_ms"):
        if int(config["solver"][name]) != 0:
            raise ValueError(f"{name} must be 0 (unlimited)")


def _valid_terminal(path: Path, expected_run_id: str) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    return payload.get("schema") == RESULT_SCHEMA and payload.get("run_id") == expected_run_id and payload.get("state") == "terminal"


def _selected_baseline_runs(path: Path) -> list[dict]:
    selected = []
    for file_path in sorted(path.glob("*.json")):
        payload = json.loads(file_path.read_text())
        if payload.get("schema") != BASELINE_SCHEMA or payload.get("state") != "terminal":
            continue
        if payload.get("terminal_classification") != "finite_query_ambiguity":
            continue
        if int(payload.get("query_count", 0)) != 128:
            raise ValueError(f"baseline ambiguity was not q128: {file_path}")
        selected.append(payload)
    return selected


def load_tasks(config: dict, baseline_dir: Path | None = None, result_dir: Path | None = None, checkpoint_dir: Path | None = None) -> list[RunTask]:
    _validate_config(config)
    baseline_dir = baseline_dir or _rooted(config["paths"]["baseline_result_dir"])
    result_dir = result_dir or _rooted(config["paths"]["result_dir"])
    checkpoint_dir = checkpoint_dir or _rooted(config["paths"]["checkpoint_dir"])
    selected = _selected_baseline_runs(baseline_dir)
    if not selected:
        raise ValueError("paper384 baseline produced no q128 ambiguity rows")

    tasks = []
    for baseline in selected:
        tap = dict(baseline["tap"])
        if not {"tap_id", "candidate_id", "stage", "bit_index"} <= tap.keys():
            raise ValueError(f"baseline tap is incomplete: {baseline['run_id']}")
        case = {
            "case_id": baseline["case_id"],
            "candidate_id": baseline["candidate_id"],
            "stage": str(tap["stage"]),
            "bit_index": str(tap["bit_index"]),
        }
        identifier = run_id(case, int(baseline["seed"]))
        result_path = result_dir / f"{identifier}.json"
        if _valid_terminal(result_path, identifier):
            continue
        tasks.append(RunTask(
            identifier, case, int(baseline["seed"]), (tap,), 128, config,
            checkpoint_dir / f"{identifier}.json", result_path,
        ))
    return tasks


def _new_checkpoint(task: RunTask) -> dict:
    return {
        "schema": CHECKPOINT_SCHEMA,
        "run_id": task.run_id,
        "case_id": task.case["case_id"],
        "candidate_id": task.case["candidate_id"],
        "seed": task.seed,
        "tap": task.taps[0],
        "bootstrap_query_count": 128,
        "adaptive_plaintexts_hex": [],
        "steps": [],
        "state": "running",
    }


def _load_checkpoint(task: RunTask) -> dict:
    if not task.checkpoint_path.exists():
        return _new_checkpoint(task)
    checkpoint = json.loads(task.checkpoint_path.read_text())
    expected = (CHECKPOINT_SCHEMA, task.run_id, task.case["case_id"], task.case["candidate_id"], task.seed, task.taps[0], 128)
    actual = (checkpoint.get("schema"), checkpoint.get("run_id"), checkpoint.get("case_id"), checkpoint.get("candidate_id"), checkpoint.get("seed"), checkpoint.get("tap"), checkpoint.get("bootstrap_query_count"))
    if actual != expected:
        raise ValueError("checkpoint identity mismatch")
    return checkpoint


def _terminal_payload(task: RunTask, checkpoint: dict, terminal: str, solver: dict) -> dict:
    adaptive_count = len(checkpoint["adaptive_plaintexts_hex"])
    return {
        "schema": RESULT_SCHEMA,
        "state": "terminal",
        "run_id": task.run_id,
        "case_id": task.case["case_id"],
        "candidate_id": task.case["candidate_id"],
        "seed": task.seed,
        "tap": task.taps[0],
        "bootstrap_query_count": 128,
        "adaptive_query_count": adaptive_count,
        "total_query_count": 128 + adaptive_count,
        "terminal_classification": terminal,
        "attack_success": terminal == "adaptive_key_recovered",
        "solver": solver,
        "steps": checkpoint["steps"],
    }


def _nonterminal(task: RunTask, checkpoint: dict, state: str, detail: dict) -> dict:
    checkpoint["state"] = state
    checkpoint["nonterminal_detail"] = detail
    write_atomic(task.checkpoint_path, checkpoint)
    return {
        "schema": RESULT_SCHEMA,
        "state": "nonterminal",
        "run_id": task.run_id,
        "case_id": task.case["case_id"],
        "seed": task.seed,
        "terminal_classification": "solver_unresolved",
        "detail": detail,
    }


def run_pair_rescue(task: RunTask) -> dict:
    checkpoint = _load_checkpoint(task)
    bootstrap = nested_plaintexts(task.query_count, task.seed)
    adaptive = [bytes.fromhex(value) for value in checkpoint["adaptive_plaintexts_hex"]]
    if any(point in bootstrap for point in adaptive) or len(set(adaptive)) != len(adaptive):
        raise ValueError("checkpoint repeats a query plaintext")
    attack = task.config["attack"]
    solver_config = task.config["solver"]
    generation = task.config["query_generation"]

    while True:
        plaintexts = bootstrap + adaptive
        document = generate_observation(key_for_seed(task.seed), list(task.taps), plaintexts, int(attack["depth"]), attack["mode"])
        solved = solver_result(document, task.config)
        statuses = (solved.get("first_result"), solved.get("second_result"))
        if statuses == ("sat", "unsat"):
            terminal = "adaptive_key_recovered" if adaptive else "bootstrap_recovered"
            return _terminal_payload(task, checkpoint, terminal, solved)
        if statuses != ("sat", "sat"):
            return _nonterminal(task, checkpoint, "solver_unresolved", solved)

        record = {
            "adaptive_query_index": len(adaptive) + 1,
            "query_count": 128 + len(adaptive),
            "first_result": "sat",
            "second_result": "sat",
        }
        pair = synthesize_for_candidate_pair(
            document, solved["first_model_hex"], solved["alternative_model"], solver_config["sbox_encoding"],
            solver_config["separability_timeout_ms"], generation["query_domain"], int(generation["max_active_bytes"]),
        )
        record["fixed_pair_separability"] = pair
        if pair.get("status") == "sat":
            separator = pair
            record["separator_source"] = "pair"
        elif pair.get("status") == "unsat":
            global_separator = synthesize_distinguishing_query(
                document, solver_config["sbox_encoding"], solver_config["separability_timeout_ms"],
                generation["query_domain"], int(generation["max_active_bytes"]),
            )
            record["global_separability"] = global_separator
            if global_separator.get("status") == "unsat":
                checkpoint["steps"].append(record)
                return _terminal_payload(task, checkpoint, "proven_observational_non_recovery", solved)
            if global_separator.get("status") != "sat":
                return _nonterminal(task, checkpoint, "global_separator_unresolved", global_separator)
            separator = global_separator
            record["separator_source"] = "global_fallback_after_pair_unsat"
        else:
            return _nonterminal(task, checkpoint, "pair_separator_unresolved", pair)

        point = bytes.fromhex(str(separator["plaintext_hex"]))
        if point in plaintexts:
            return _nonterminal(task, checkpoint, "duplicate_separator", separator)
        adaptive.append(point)
        checkpoint["adaptive_plaintexts_hex"].append(point.hex())
        record["accepted_plaintext_hex"] = point.hex()
        checkpoint["steps"].append(record)
        checkpoint["state"] = "running"
        checkpoint.pop("nonterminal_detail", None)
        write_atomic(task.checkpoint_path, checkpoint)


def execute_task(task: RunTask) -> dict:
    started = time.perf_counter()
    try:
        payload = run_pair_rescue(task)
    except BaseException as error:
        payload = {
            "schema": RESULT_SCHEMA, "state": "error", "run_id": task.run_id,
            "case_id": task.case["case_id"], "seed": task.seed,
            "error": repr(error), "traceback": traceback.format_exc(),
        }
    payload["wall_time"] = time.perf_counter() - started
    return payload


def rebuild_summary(result_dir: Path, summary_path: Path) -> None:
    rows = [path.read_text().strip() for path in sorted(result_dir.glob("*.json"))]
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = summary_path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text("\n".join(rows) + ("\n" if rows else ""))
    temporary.replace(summary_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/late_1bit_pair_rescue_paper384.yaml")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers is not None and not 1 <= args.workers <= MAX_WORKERS:
        parser.error(f"workers must be between 1 and {MAX_WORKERS}")
    config = yaml.safe_load(_rooted(args.config).read_text())
    tasks = load_tasks(config)
    workers = min(len(tasks), int(config["campaign"]["workers"]), args.workers or int(config["campaign"]["workers"]), MAX_WORKERS)
    print(f"selected={len(tasks)} workers={workers} bootstrap=q128 pair_separator=only global_fallback=pair_unsat", flush=True)
    if args.dry_run or not tasks:
        return

    result_dir = _rooted(config["paths"]["result_dir"])
    summary_path = _rooted(config["paths"]["summary"])
    errors = _rooted(config["paths"]["errors"])
    result_dir.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(execute_task, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            payload = future.result()
            if payload["state"] == "terminal":
                write_atomic(task.result_path, payload)
                rebuild_summary(result_dir, summary_path)
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(errors, payload)
                outcome = payload["terminal_classification"] if payload["state"] == "nonterminal" else "error"
            print(f"[{index}/{len(tasks)}] {task.run_id} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
