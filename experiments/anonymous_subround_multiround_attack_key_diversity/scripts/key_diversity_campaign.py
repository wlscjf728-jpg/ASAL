"""Run the isolated AES-128 master-key diversity campaign."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from adaptive_query_attack import (  # noqa: E402
    synthesize_distinguishing_query,
    synthesize_for_candidate_pair,
)
from late1bit_scoring import rank_plaintexts  # noqa: E402
from oracle import generate_observation  # noqa: E402
from solve_attacker import solve_document_without_truth  # noqa: E402
from key_diversity_common import (  # noqa: E402
    ROOT,
    append_jsonl,
    classify_pair,
    is_sat_sat,
    is_sat_unsat,
    load_keys,
    load_taps,
    nested_plaintexts,
    query_schedule_sha256,
    read_yaml,
    sanitize_for_solver,
    write_atomic,
)


RESULT_SCHEMA = "asal-key-diversity-result-v1"
CHECKPOINT_SCHEMA = "asal-key-diversity-checkpoint-v1"
ERROR_SCHEMA = "asal-key-diversity-error-v1"
DEFAULT_CONFIG = ROOT / "configs/key_diversity.yaml"


def rooted(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def load_campaign_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = read_yaml(rooted(path))
    if config["campaign"]["workers"] > 32:
        raise ValueError("workers must be <= 32")
    if config["campaign"]["key_count"] != 20:
        raise ValueError("this validation requires exactly twenty new keys")
    if config["campaign"]["tap_count"] != 4:
        raise ValueError("this validation requires exactly four taps")
    if config["attack"]["depth"] != 2 or config["attack"]["mode"] != "differential":
        raise ValueError("key diversity requires depth=2 differential leakage")
    for name in ("first_timeout_ms", "second_timeout_ms", "separability_timeout_ms"):
        if int(config["solver"][name]) != 0:
            raise ValueError(f"{name} must be unlimited (0 ms)")
    ladder = [int(value) for value in config["attack"]["fixed_query_ladder"]]
    if ladder != sorted(set(ladder)) or ladder[0] <= 0:
        raise ValueError("fixed query ladder must be strictly increasing")
    return config


def tap_from_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "tap_id": row["tap_id"],
        "candidate_id": row["candidate_id"],
        "stage": row["stage"],
        "bit_index": int(row["bit_index"]),
        "byte_index": int(row["byte_index"]),
        "row": int(row["row"]),
        "column": int(row["column"]),
        "bit_in_byte": int(row["bit_in_byte"]),
    }


def build_tasks(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    config = load_campaign_config(config_path)
    taps = [tap_from_row(row) for row in load_taps(rooted(config["paths"]["tap_manifest"]))]
    keys = load_keys(rooted(config["paths"]["evaluator_keys"]))
    tasks = []
    for key in keys:
        for tap in taps:
            tasks.append({
                "run_id": f"{key['key_id']}__{tap['tap_id']}__key_diversity",
                "key_id": key["key_id"],
                "key_hex": key["key_hex"],
                "key_sha256": key["key_sha256"],
                "tap": tap,
                "config": config,
            })
    if len(tasks) != 80:
        raise AssertionError(f"expected 80 tasks, got {len(tasks)}")
    return tasks


def terminal_classification(
    first_result: str,
    second_result: str,
    adaptive: bool,
) -> str:
    pair = classify_pair(first_result, second_result)
    if pair == "unique":
        return "ADAPTIVE_UNIQUE" if adaptive else "FIXED_UNIQUE"
    if pair == "ambiguity":
        return "FIXED_AMBIGUOUS" if not adaptive else "ADAPTIVE_AMBIGUOUS"
    if first_result.lower() == "unsat":
        return "MODEL_INCONSISTENT"
    return "UNKNOWN"


def solver_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_timeout_ms": int(config["solver"]["first_timeout_ms"]),
        "second_timeout_ms": int(config["solver"]["second_timeout_ms"]),
        "diagnostic_timeout_ms": int(config["solver"]["diagnostic_timeout_ms"]),
        "sbox_encoding": config["solver"]["sbox_encoding"],
    }


def solve_observation(
    key: bytes,
    tap: dict[str, Any],
    plaintexts: list[bytes],
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = generate_observation(
        key,
        [tap],
        plaintexts,
        int(config["attack"]["depth"]),
        config["attack"]["mode"],
    )
    solver_document = sanitize_for_solver(document)
    result = solve_document_without_truth(solver_document, **solver_config(config))
    return document, result


def checkpoint_row(
    task: dict[str, Any],
    phase: str,
    query_count: int,
    result: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    row = {
        "schema": CHECKPOINT_SCHEMA,
        "run_id": task["run_id"],
        "key_id": task["key_id"],
        "tap_id": task["tap"]["tap_id"],
        "phase": phase,
        "query_count": query_count,
        "first_result": result.get("first_result", ""),
        "second_result": result.get("second_result", ""),
        "classification": classify_pair(
            result.get("first_result", ""), result.get("second_result", "")
        ),
        "first_time": result.get("first_time", 0.0),
        "second_time": result.get("second_time", 0.0),
        "first_model_hex": result.get("first_model_hex", ""),
        "alternative_model": result.get("alternative_model", ""),
        "query_schedule_sha256": query_schedule_sha256(
            int(task["config"]["campaign"]["query_seed"]), query_count
        ),
    }
    row.update(extra)
    return row


def fixed_checkpoints(
    task: dict[str, Any],
    key: bytes,
    checkpoint_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    config = task["config"]
    tap = task["tap"]
    query_seed = int(config["campaign"]["query_seed"])
    attempts = []
    last_document = None
    last_result = None
    for count in [int(value) for value in config["attack"]["fixed_query_ladder"]]:
        plaintexts = nested_plaintexts(count, query_seed)
        document, result = solve_observation(key, tap, plaintexts, config)
        classification = classify_pair(result["first_result"], result["second_result"])
        attempt = {
            "phase": "fixed",
            "query_count": count,
            "classification": classification,
            "first_result": result["first_result"],
            "second_result": result["second_result"],
            "first_time": result["first_time"],
            "second_time": result["second_time"],
            "first_model_hex": result.get("first_model_hex", ""),
            "alternative_model": result.get("alternative_model", ""),
        }
        attempts.append(attempt)
        if checkpoint_callback:
            checkpoint_callback(checkpoint_row(task, "fixed", count, result))
        last_document, last_result = document, result
        if classification != "ambiguity":
            return {
                "attempts": attempts,
                "last_plaintexts": plaintexts,
                "last_document": document,
                "last_result": result,
                "fixed_terminal": terminal_classification(
                    result["first_result"], result["second_result"], adaptive=False
                ),
                "fixed_unique_query_count": count if classification == "unique" else None,
            }
    assert last_document is not None and last_result is not None
    return {
        "attempts": attempts,
        "last_plaintexts": nested_plaintexts(
            int(config["attack"]["fixed_query_ladder"][-1]), query_seed
        ),
        "last_document": last_document,
        "last_result": last_result,
        "fixed_terminal": "FIXED_AMBIGUOUS",
        "fixed_unique_query_count": None,
    }


def run_adaptive(
    key: bytes,
    tap: dict[str, Any],
    plaintexts: list[bytes],
    config: dict[str, Any],
    checkpoint_callback: Callable[[dict[str, Any]], None] | None = None,
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reuse the existing pair-first/global-fallback separator loop."""
    adaptive_points: list[bytes] = []
    steps = []
    prior_active_bits: set[int] = set()
    solver_options = config["solver"]
    generation = config["query_generation"]
    current_document = None
    current_result = None

    while True:
        current_plaintexts = plaintexts + adaptive_points
        current_document, current_result = solve_observation(
            key, tap, current_plaintexts, config
        )
        query_count = len(current_plaintexts) - 1
        current_class = classify_pair(
            current_result["first_result"], current_result["second_result"]
        )
        if checkpoint_callback and task:
            checkpoint_callback(
                checkpoint_row(task, "adaptive", query_count, current_result)
            )
        if current_class == "unique":
            return {
                "final_classification": "ADAPTIVE_UNIQUE",
                "adaptive_points": adaptive_points,
                "steps": steps,
                "final_document": current_document,
                "final_result": current_result,
            }
        if current_class != "ambiguity":
            return {
                "final_classification": terminal_classification(
                    current_result["first_result"], current_result["second_result"], True
                ),
                "adaptive_points": adaptive_points,
                "steps": steps,
                "final_document": current_document,
                "final_result": current_result,
            }

        step: dict[str, Any] = {
            "adaptive_query_index": len(adaptive_points) + 1,
            "query_count": query_count,
            "first_result": current_result["first_result"],
            "second_result": current_result["second_result"],
        }
        pair = synthesize_for_candidate_pair(
            current_document,
            current_result["first_model_hex"],
            current_result["alternative_model"],
            solver_options["sbox_encoding"],
            int(solver_options["separability_timeout_ms"]),
            generation["query_domain"],
            int(generation["max_active_bytes"]),
        )
        step["fixed_pair_separability"] = pair
        pair_status = pair.get("status")
        if pair_status == "sat":
            global_candidate = synthesize_distinguishing_query(
                current_document,
                solver_options["sbox_encoding"],
                int(solver_options["separability_timeout_ms"]),
                generation["query_domain"],
                int(generation["max_active_bytes"]),
            )
            step["global_candidate"] = global_candidate
            if global_candidate.get("status") != "sat":
                if global_candidate.get("status") == "unsat":
                    steps.append(step)
                    return {
                        "final_classification": "PROVEN_NON_RECOVERY",
                        "adaptive_points": adaptive_points,
                        "steps": steps,
                        "final_document": current_document,
                        "final_result": current_result,
                    }
                return {
                    "final_classification": "UNKNOWN",
                    "adaptive_points": adaptive_points,
                    "steps": steps,
                    "final_document": current_document,
                    "final_result": current_result,
                }
            candidates = [
                bytes.fromhex(pair["plaintext_hex"]),
                bytes.fromhex(global_candidate["plaintext_hex"]),
            ]
            candidates = list(dict.fromkeys(candidates))
            pair_keys = [
                bytes.fromhex(current_result["first_model_hex"]),
                bytes.fromhex(current_result["alternative_model"]),
            ]
            scores = rank_plaintexts(
                candidates,
                pair_keys,
                tap,
                plaintexts[0],
                int(config["attack"]["depth"]),
                prior_active_bits,
            )
            selected = scores[0]
            selected_point = bytes.fromhex(selected["plaintext_hex"])
            step["dependency_scores"] = scores
            step["separator_source"] = "dependency_guided_pair_global_portfolio"
            prior_active_bits.update(selected["active_bits"])
        elif pair_status == "unsat":
            global_candidate = synthesize_distinguishing_query(
                current_document,
                solver_options["sbox_encoding"],
                int(solver_options["separability_timeout_ms"]),
                generation["query_domain"],
                int(generation["max_active_bytes"]),
            )
            step["global_separability"] = global_candidate
            step["separator_source"] = "global"
            if global_candidate.get("status") == "unsat":
                steps.append(step)
                return {
                    "final_classification": "PROVEN_NON_RECOVERY",
                    "adaptive_points": adaptive_points,
                    "steps": steps,
                    "final_document": current_document,
                    "final_result": current_result,
                }
            if global_candidate.get("status") != "sat":
                return {
                    "final_classification": "UNKNOWN",
                    "adaptive_points": adaptive_points,
                    "steps": steps,
                    "final_document": current_document,
                    "final_result": current_result,
                }
            selected_point = bytes.fromhex(global_candidate["plaintext_hex"])
        else:
            steps.append(step)
            return {
                "final_classification": "UNKNOWN",
                "adaptive_points": adaptive_points,
                "steps": steps,
                "final_document": current_document,
                "final_result": current_result,
            }

        if selected_point in current_plaintexts:
            steps.append(step)
            return {
                "final_classification": "UNKNOWN",
                "adaptive_points": adaptive_points,
                "steps": steps,
                "final_document": current_document,
                "final_result": current_result,
                "detail": "separator duplicated an existing plaintext",
            }
        adaptive_points.append(selected_point)
        step["accepted_plaintext_hex"] = selected_point.hex()
        steps.append(step)
        if checkpoint_callback and task:
            checkpoint_callback(
                checkpoint_row(
                    task,
                    "adaptive_separator",
                    query_count,
                    current_result,
                    accepted_plaintext_hex=selected_point.hex(),
                    separator_source=step.get("separator_source", ""),
                )
            )


def terminal_payload(
    task: dict[str, Any],
    fixed: dict[str, Any],
    adaptive: dict[str, Any] | None,
    started: float,
) -> dict[str, Any]:
    final = adaptive["final_result"] if adaptive else fixed["last_result"]
    final_classification = adaptive["final_classification"] if adaptive else fixed["fixed_terminal"]
    recovered = final.get("first_model_hex", "")
    key_hex = task["key_hex"]
    return {
        "schema": RESULT_SCHEMA,
        "state": "terminal",
        "run_id": task["run_id"],
        "key_id": task["key_id"],
        "tap": task["tap"],
        "fixed_terminal_classification": fixed["fixed_terminal"],
        "terminal_classification": final_classification,
        "attack_success": final_classification in {"FIXED_UNIQUE", "ADAPTIVE_UNIQUE"},
        "fixed_unique_query_count": fixed["fixed_unique_query_count"],
        "fixed_attempts": fixed["attempts"],
        "adaptive_used": adaptive is not None,
        "adaptive_query_count": len(adaptive["adaptive_points"]) if adaptive else 0,
        "adaptive_steps": adaptive["steps"] if adaptive else [],
        "total_query_count": (
            fixed["attempts"][-1]["query_count"]
            + (len(adaptive["adaptive_points"]) if adaptive else 0)
        ),
        "recovered_key_hex": recovered,
        "correct_key_match": recovered.lower() == key_hex.lower(),
        "evaluator_only": {
            "master_key_hex": key_hex,
            "key_sha256": task["key_sha256"],
            "note": "retained for external correctness checking; absent from solver document",
        },
        "final_solver": final,
        "wall_time": time.perf_counter() - started,
    }


def run_one_case(task: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    checkpoint_path = rooted(task["config"]["paths"]["checkpoints"])
    callback = lambda row: append_jsonl(checkpoint_path, row)
    key = bytes.fromhex(task["key_hex"])
    fixed = fixed_checkpoints(task, key, callback)
    if fixed["fixed_terminal"] == "FIXED_UNIQUE":
        return terminal_payload(task, fixed, None, started)
    if fixed["fixed_terminal"] != "FIXED_AMBIGUOUS":
        return terminal_payload(task, fixed, None, started)
    adaptive = run_adaptive(
        key,
        task["tap"],
        fixed["last_plaintexts"],
        task["config"],
        callback,
        task,
    )
    return terminal_payload(task, fixed, adaptive, started)


def execute_task(task: dict[str, Any]) -> dict[str, Any]:
    try:
        return run_one_case(task)
    except BaseException as error:  # keep the campaign resumable
        return {
            "schema": ERROR_SCHEMA,
            "state": "error",
            "run_id": task["run_id"],
            "key_id": task["key_id"],
            "tap_id": task["tap"]["tap_id"],
            "error": repr(error),
            "traceback": traceback.format_exc(),
        }


def completed_run_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed = set()
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("state") == "terminal" and row.get("schema") == RESULT_SCHEMA:
            completed.add(row.get("run_id"))
    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_campaign_config(args.config)
    all_tasks = build_tasks(args.config)
    raw_path = rooted(config["paths"]["raw_results"])
    done = completed_run_ids(raw_path)
    tasks = [task for task in all_tasks if task["run_id"] not in done]
    if args.limit is not None:
        tasks = tasks[: args.limit]
    configured = int(config["campaign"]["workers"])
    workers = min(configured, args.workers or configured, len(tasks)) if tasks else 0
    print(
        f"tasks_total={len(all_tasks)} completed={len(done)} pending={len(tasks)} workers={workers}",
        flush=True,
    )
    if args.dry_run or not tasks:
        return
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    error_path = rooted(config["paths"]["errors"])
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
    ) as pool:
        futures = {pool.submit(execute_task, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            payload = future.result()
            if payload.get("state") == "terminal":
                append_jsonl(raw_path, payload)
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(error_path, payload)
                outcome = "ERROR"
            print(f"[{index}/{len(tasks)}] {task['run_id']} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
