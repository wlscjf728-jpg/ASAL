"""MC-1bit-equivalent pair-only adaptive rescue for all-ambiguous early 4bit sets."""
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
from experiment_common import ROOT, append_jsonl, key_for_seed, nested_plaintexts, read_csv
from oracle import generate_observation
from run_phase8_campaign import write_atomic


CHECKPOINT_SCHEMA = "early4bit-pair-rescue-checkpoint-v1"
RESULT_SCHEMA = "early4bit-pair-rescue-result-v1"
RUN_TAG = "early4bit_pair_rescue"
MAX_WORKERS = 23


@dataclass(frozen=True)
class RunTask:
    run_id: str
    source: dict[str, str]
    taps: tuple[dict[str, object], ...]
    config: dict
    checkpoint_path: Path
    result_path: Path


def rooted(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def test_config() -> dict:
    return yaml.safe_load((ROOT / "configs/early4bit_pair_rescue.yaml").read_text())


def task_id(row: dict[str, str]) -> str:
    return f"p{row['source_phase']}_4b__{row['source_case_id']}__seed{row['seed']}__q{row['query_count']}__{RUN_TAG}"


def make_taps(row: dict[str, str]) -> tuple[dict[str, object], ...]:
    taps = []
    for index, name in enumerate((row["cand_a"], row["cand_b"], row["cand_c"], row["cand_d"])):
        stage, bit = name.split("_", 1)
        taps.append({"tap_id": f"tap_{index}_{name}", "candidate_id": name, "stage": stage, "bit_index": int(bit)})
    return tuple(taps)


def validate_config(config: dict) -> None:
    if int(config["campaign"]["workers"]) > MAX_WORKERS:
        raise ValueError("workers must not exceed 23")
    for name in ("first_timeout_ms", "second_timeout_ms", "separability_timeout_ms"):
        if int(config["solver"][name]) != 0:
            raise ValueError(f"{name} must be unlimited")


def terminal(path: Path, run_id: str) -> bool:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    return data.get("schema") == RESULT_SCHEMA and data.get("state") == "terminal" and data.get("run_id") == run_id


def load_tasks(config: dict) -> list[RunTask]:
    validate_config(config)
    rows = read_csv(rooted(config["paths"]["manifest"]))
    if len(rows) != int(config["campaign"]["expected_tasks"]):
        raise ValueError(f"expected {config['campaign']['expected_tasks']} tasks, found {len(rows)}")
    result_dir, checkpoint_dir = rooted(config["paths"]["result_dir"]), rooted(config["paths"]["checkpoint_dir"])
    tasks = []
    for row in rows:
        if (int(row["tap_count"]), int(row["depth"]), row["mode"]) != (4, 2, "differential"):
            raise ValueError(f"invalid source model: {row}")
        identifier = task_id(row)
        result_path = result_dir / f"{identifier}.json"
        if not terminal(result_path, identifier):
            tasks.append(RunTask(identifier, dict(row), make_taps(row), config, checkpoint_dir / f"{identifier}.json", result_path))
    return tasks


def new_checkpoint(task: RunTask) -> dict:
    return {"schema": CHECKPOINT_SCHEMA, "run_id": task.run_id, "source": task.source, "taps": task.taps, "adaptive_plaintexts_hex": [], "steps": [], "state": "running"}


def load_checkpoint(task: RunTask) -> dict:
    if not task.checkpoint_path.exists():
        return new_checkpoint(task)
    data = json.loads(task.checkpoint_path.read_text())
    if data.get("schema") != CHECKPOINT_SCHEMA or data.get("run_id") != task.run_id:
        raise ValueError("checkpoint identity mismatch")
    return data


def terminal_payload(task: RunTask, checkpoint: dict, classification: str, solved: dict) -> dict:
    adaptive_count = len(checkpoint["adaptive_plaintexts_hex"])
    return {"schema": RESULT_SCHEMA, "state": "terminal", "run_id": task.run_id, "source": task.source, "taps": task.taps, "adaptive_query_count": adaptive_count, "total_query_count": int(task.source["query_count"]) + adaptive_count, "terminal_classification": classification, "attack_success": classification == "adaptive_key_recovered", "solver": solved, "steps": checkpoint["steps"]}


def nonterminal(task: RunTask, checkpoint: dict, state: str, detail: dict) -> dict:
    checkpoint["state"] = state
    checkpoint["nonterminal_detail"] = detail
    write_atomic(task.checkpoint_path, checkpoint)
    return {"schema": RESULT_SCHEMA, "state": "nonterminal", "run_id": task.run_id, "source": task.source, "terminal_classification": "solver_unresolved", "detail": detail}


def run_task(task: RunTask) -> dict:
    checkpoint = load_checkpoint(task)
    bootstrap = nested_plaintexts(int(task.source["query_count"]), int(task.source["seed"]))
    adaptive = [bytes.fromhex(value) for value in checkpoint["adaptive_plaintexts_hex"]]
    if any(point in bootstrap for point in adaptive) or len(adaptive) != len(set(adaptive)):
        raise ValueError("duplicate adaptive plaintext")
    while True:
        document = generate_observation(key_for_seed(int(task.source["seed"])), list(task.taps), bootstrap + adaptive, 2, "differential")
        solved = solver_result(document, task.config)
        statuses = (solved.get("first_result"), solved.get("second_result"))
        if statuses == ("sat", "unsat"):
            if not adaptive:
                return nonterminal(task, checkpoint, "baseline_reproduction_mismatch", solved)
            return terminal_payload(task, checkpoint, "adaptive_key_recovered", solved)
        if statuses != ("sat", "sat"):
            return nonterminal(task, checkpoint, "baseline_reproduction_unresolved" if not adaptive else "solver_unresolved", solved)
        generation, solver = task.config["query_generation"], task.config["solver"]
        record = {"adaptive_query_index": len(adaptive) + 1, "query_count": int(task.source["query_count"]) + len(adaptive), "first_result": "sat", "second_result": "sat"}
        pair = synthesize_for_candidate_pair(document, solved["first_model_hex"], solved["alternative_model"], solver["sbox_encoding"], solver["separability_timeout_ms"], generation["query_domain"], int(generation["max_active_bytes"]))
        record["fixed_pair_separability"] = pair
        if pair.get("status") == "sat":
            separator, record["separator_source"] = pair, "pair"
        elif pair.get("status") == "unsat":
            global_separator = synthesize_distinguishing_query(document, solver["sbox_encoding"], solver["separability_timeout_ms"], generation["query_domain"], int(generation["max_active_bytes"]))
            record["global_separability"] = global_separator
            if global_separator.get("status") == "unsat":
                checkpoint["steps"].append(record)
                return terminal_payload(task, checkpoint, "proven_observational_non_recovery", solved)
            if global_separator.get("status") != "sat":
                return nonterminal(task, checkpoint, "global_separator_unresolved", global_separator)
            separator, record["separator_source"] = global_separator, "global_fallback_after_pair_unsat"
        else:
            return nonterminal(task, checkpoint, "pair_separator_unresolved", pair)
        point = bytes.fromhex(separator["plaintext_hex"])
        if point in bootstrap or point in adaptive:
            return nonterminal(task, checkpoint, "duplicate_separator", separator)
        adaptive.append(point)
        checkpoint["adaptive_plaintexts_hex"].append(point.hex())
        record["accepted_plaintext_hex"] = point.hex()
        checkpoint["steps"].append(record)
        checkpoint["state"] = "running"
        checkpoint.pop("nonterminal_detail", None)
        write_atomic(task.checkpoint_path, checkpoint)


def execute(task: RunTask) -> dict:
    started = time.perf_counter()
    try:
        payload = run_task(task)
    except BaseException as error:
        payload = {"schema": RESULT_SCHEMA, "state": "error", "run_id": task.run_id, "source": task.source, "error": repr(error), "traceback": traceback.format_exc()}
    payload["wall_time"] = time.perf_counter() - started
    return payload


def rebuild_summary(result_dir: Path, summary: Path) -> None:
    rows = [path.read_text().strip() for path in sorted(result_dir.glob("*.json"))]
    summary.parent.mkdir(parents=True, exist_ok=True)
    temporary = summary.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text("\n".join(rows) + ("\n" if rows else ""))
    temporary.replace(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/early4bit_pair_rescue.yaml")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(rooted(args.config).read_text())
    tasks = load_tasks(config)
    workers = min(len(tasks), int(config["campaign"]["workers"]), args.workers or int(config["campaign"]["workers"]), MAX_WORKERS)
    print(f"selected={len(tasks)} workers={workers} bootstrap=preserved pair_separator=only global_fallback=pair_unsat", flush=True)
    if args.dry_run or not tasks:
        return
    result_dir, summary, errors = rooted(config["paths"]["result_dir"]), rooted(config["paths"]["summary"]), rooted(config["paths"]["errors"])
    result_dir.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(execute, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task, payload = futures[future], future.result()
            if payload["state"] == "terminal":
                write_atomic(task.result_path, payload)
                rebuild_summary(result_dir, summary)
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(errors, payload)
                outcome = payload.get("terminal_classification", "error")
            print(f"[{index}/{len(tasks)}] {task.run_id} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
