"""Support-guided pair-only adaptive rescue for early-only Phase 7/7_1 runs."""
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
import z3

from adaptive_query_attack import leakage_vector, plaintext_domain_constraints, solver_result, synthesize_distinguishing_query, timed_check
from early_only_pair_scoring import rank_pair_plaintexts
from experiment_common import ROOT, append_jsonl, key_for_seed, load_candidate_map, nested_plaintexts, read_csv, taps_for_case
from oracle import generate_observation
from run_phase8_campaign import write_atomic
from z3_aes import AESGraphBuilder


CHECKPOINT_SCHEMA = "early-only-pair-rescue-checkpoint-v1"
RESULT_SCHEMA = "early-only-pair-rescue-result-v1"
RUN_TAG = "early_only_pair_rescue"
MAX_WORKERS = 32


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


def task_id(row: dict[str, str]) -> str:
    return f"p{row['source_phase']}_{row['tap_count']}b__{row['source_case_id']}__seed{row['seed']}__q{row['query_count']}__{RUN_TAG}"


def validate_config(config: dict) -> None:
    if int(config["campaign"]["workers"]) > MAX_WORKERS:
        raise ValueError("workers must not exceed 32")
    for name in ("first_timeout_ms", "second_timeout_ms", "separability_timeout_ms"):
        if int(config["solver"][name]) != 0:
            raise ValueError(f"{name} must be unlimited")


def terminal(path: Path, identifier: str) -> bool:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    return data.get("schema") == RESULT_SCHEMA and data.get("state") == "terminal" and data.get("run_id") == identifier


def load_tasks(config: dict, manifest_path: Path | None = None, result_dir: Path | None = None, checkpoint_dir: Path | None = None) -> list[RunTask]:
    validate_config(config)
    manifest_path = manifest_path or rooted(config["paths"]["manifest"])
    result_dir = result_dir or rooted(config["paths"]["result_dir"])
    checkpoint_dir = checkpoint_dir or rooted(config["paths"]["checkpoint_dir"])
    rows = read_csv(manifest_path)
    if len(rows) != int(config["campaign"]["expected_tasks"]):
        raise ValueError(f"expected {config['campaign']['expected_tasks']} tasks, found {len(rows)}")
    candidates = load_candidate_map()
    tasks = []
    for row in rows:
        if (int(row["depth"]), row["mode"], int(row["tap_count"])) not in ((2, "differential", 2), (2, "differential", 3)):
            raise ValueError(f"invalid source model: {row}")
        taps = tuple(taps_for_case(row, candidates))
        if len(taps) != int(row["tap_count"]) or any(tap["stage"] not in {"SB", "SR"} for tap in taps):
            raise ValueError(f"source is not early-only: {row}")
        identifier = task_id(row)
        path = result_dir / f"{identifier}.json"
        if not terminal(path, identifier):
            tasks.append(RunTask(identifier, dict(row), taps, config, checkpoint_dir / f"{identifier}.json", path))
    return tasks


def new_checkpoint(task: RunTask) -> dict:
    return {"schema": CHECKPOINT_SCHEMA, "run_id": task.run_id, "source": task.source, "taps": task.taps, "adaptive_plaintexts_hex": [], "prior_active_bits": [], "steps": [], "state": "running"}


def load_checkpoint(task: RunTask) -> dict:
    if not task.checkpoint_path.exists():
        return new_checkpoint(task)
    data = json.loads(task.checkpoint_path.read_text())
    if (data.get("schema"), data.get("run_id"), data.get("source"), tuple(data.get("taps", []))) != (CHECKPOINT_SCHEMA, task.run_id, task.source, task.taps):
        raise ValueError("checkpoint identity mismatch")
    return data


def synthesize_pair_candidate(document: dict, key_a_hex: str, key_b_hex: str, config: dict, exclusions: list[bytes]) -> dict:
    experiment = document["experiment"]
    key_a = [z3.BitVecVal(value, 8) for value in bytes.fromhex(key_a_hex)]
    key_b = [z3.BitVecVal(value, 8) for value in bytes.fromhex(key_b_hex)]
    builder_a = AESGraphBuilder(int(experiment["depth"]), key_a, config["solver"]["sbox_encoding"])
    builder_b = AESGraphBuilder(int(experiment["depth"]), key_b, config["solver"]["sbox_encoding"])
    reference = bytes.fromhex(document["observations"][int(experiment.get("base_query_id", 0))]["plaintext_hex"])
    plaintext = [z3.BitVec(f"early_pair_p_{index}", 8) for index in range(16)]
    for builder, base, query in ((builder_a, "a_base", "a_query"), (builder_b, "b_base", "b_query")):
        builder.build_for_plaintext(reference, base)
        builder.build_for_plaintext(plaintext, query)
    leak_a = leakage_vector(builder_a, "a_query", "a_base", experiment)
    leak_b = leakage_vector(builder_b, "b_query", "b_base", experiment)
    solver = z3.Solver()
    solver.add(*builder_a.sbox_constraints, *builder_b.sbox_constraints)
    solver.add(z3.Or(*[left != right for left, right in zip(leak_a, leak_b)]))
    generation = config["query_generation"]
    solver.add(*plaintext_domain_constraints(plaintext, reference, generation["query_domain"], int(generation["max_active_bytes"])))
    for observation in document["observations"]:
        exclusions.append(bytes.fromhex(observation["plaintext_hex"]))
    for previous in exclusions:
        solver.add(z3.Or(*[plaintext[index] != z3.BitVecVal(previous[index], 8) for index in range(16)]))
    status, elapsed, reason = timed_check(solver, config["solver"]["separability_timeout_ms"])
    result = {"status": str(status).lower(), "elapsed": elapsed, "reason_unknown": reason, "synthesis_mode": "fixed_candidate_pair"}
    if status == z3.sat:
        result["plaintext_hex"] = bytes(solver.model().eval(value, model_completion=True).as_long() for value in plaintext).hex()
    return result


def nonterminal(task: RunTask, checkpoint: dict, state: str, detail: dict) -> dict:
    checkpoint["state"] = state
    checkpoint["nonterminal_detail"] = detail
    write_atomic(task.checkpoint_path, checkpoint)
    return {"schema": RESULT_SCHEMA, "state": "nonterminal", "run_id": task.run_id, "source": task.source, "terminal_classification": "solver_unresolved", "detail": detail}


def terminal_payload(task: RunTask, checkpoint: dict, classification: str, solver: dict) -> dict:
    adaptive_count = len(checkpoint["adaptive_plaintexts_hex"])
    return {"schema": RESULT_SCHEMA, "state": "terminal", "run_id": task.run_id, "source": task.source, "taps": task.taps, "adaptive_query_count": adaptive_count, "total_query_count": int(task.source["query_count"]) + adaptive_count, "terminal_classification": classification, "attack_success": classification == "adaptive_key_recovered", "solver": solver, "steps": checkpoint["steps"]}


def run_task(task: RunTask) -> dict:
    checkpoint = load_checkpoint(task)
    bootstrap = nested_plaintexts(int(task.source["query_count"]), int(task.source["seed"]))
    adaptive = [bytes.fromhex(value) for value in checkpoint["adaptive_plaintexts_hex"]]
    if any(point in bootstrap for point in adaptive) or len(set(adaptive)) != len(adaptive):
        raise ValueError("duplicate adaptive plaintext")
    while True:
        document = generate_observation(key_for_seed(int(task.source["seed"])), list(task.taps), bootstrap + adaptive, int(task.source["depth"]), task.source["mode"])
        solved = solver_result(document, task.config)
        statuses = (solved.get("first_result"), solved.get("second_result"))
        if statuses == ("sat", "unsat"):
            label = "adaptive_key_recovered" if adaptive else "baseline_reproduction_unique"
            return terminal_payload(task, checkpoint, label, solved)
        if statuses != ("sat", "sat"):
            return nonterminal(task, checkpoint, "baseline_reproduction_unresolved" if not adaptive else "solver_unresolved", solved)
        record = {"adaptive_query_index": len(adaptive) + 1, "query_count": int(task.source["query_count"]) + len(adaptive), "first_result": "sat", "second_result": "sat"}
        candidates, synthesis = [], []
        exclusions = []
        for _ in range(int(task.config["query_generation"]["pair_candidates"])):
            item = synthesize_pair_candidate(document, solved["first_model_hex"], solved["alternative_model"], task.config, exclusions)
            synthesis.append(item)
            if item.get("status") != "sat":
                break
            point = bytes.fromhex(item["plaintext_hex"])
            candidates.append(point)
            exclusions.append(point)
        record["pair_candidate_synthesis"] = synthesis
        if candidates:
            scores = rank_pair_plaintexts(candidates, bytes.fromhex(solved["first_model_hex"]), bytes.fromhex(solved["alternative_model"]), task.taps, bootstrap[0], int(task.source["depth"]), set(checkpoint["prior_active_bits"]))
            selected = scores[0]
            point = bytes.fromhex(selected["plaintext_hex"])
            record["dependency_scores"] = [{**score, "rank_key": list(score["rank_key"])} for score in scores]
            record["separator_source"] = "support_guided_pair"
            checkpoint["prior_active_bits"] = sorted(set(checkpoint["prior_active_bits"]) | set(selected["active_bits"]))
        elif synthesis[0].get("status") == "unsat":
            generation = task.config["query_generation"]
            global_separator = synthesize_distinguishing_query(document, task.config["solver"]["sbox_encoding"], task.config["solver"]["separability_timeout_ms"], generation["query_domain"], int(generation["max_active_bytes"]))
            record["global_separability"] = global_separator
            if global_separator.get("status") == "unsat":
                checkpoint["steps"].append(record)
                return terminal_payload(task, checkpoint, "proven_observational_non_recovery", solved)
            if global_separator.get("status") != "sat":
                return nonterminal(task, checkpoint, "global_separator_unresolved", global_separator)
            point = bytes.fromhex(global_separator["plaintext_hex"])
            record["separator_source"] = "global_fallback_after_pair_unsat"
        else:
            return nonterminal(task, checkpoint, "pair_separator_unresolved", synthesis[0])
        if point in bootstrap or point in adaptive:
            return nonterminal(task, checkpoint, "duplicate_separator", {"plaintext_hex": point.hex()})
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
    parser.add_argument("--config", default="configs/early_only_pair_rescue.yaml")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(rooted(args.config).read_text())
    tasks = load_tasks(config)
    workers = min(len(tasks), int(config["campaign"]["workers"]), args.workers or int(config["campaign"]["workers"]), MAX_WORKERS)
    print(f"selected={len(tasks)} workers={workers} support_guided_pair_candidates={config['query_generation']['pair_candidates']} global_fallback=pair_unsat", flush=True)
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
