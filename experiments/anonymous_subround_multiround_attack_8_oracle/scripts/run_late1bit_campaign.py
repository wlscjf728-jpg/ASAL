"""Run the minimal resumable late one-bit adaptive campaign."""
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

from adaptive_query_attack import (
    solver_result,
    synthesize_distinguishing_query,
    synthesize_for_candidate_pair,
)
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
from run_phase8_campaign import write_atomic
from late1bit_scoring import rank_plaintexts


CHECKPOINT_SCHEMA = "late-1bit-checkpoint-v1"
RESULT_SCHEMA = "late-1bit-result-v1"
RUN_TAG = "late1bit_adaptive"
MAX_WORKERS = 32


class NonTerminalState(RuntimeError):
    """The solver did not establish a scientific verdict."""


@dataclass(frozen=True)
class Tap:
    tap_id: str
    candidate_id: str
    stage: str
    bit_index: int

    def as_dict(self) -> dict[str, object]:
        return {
            "tap_id": self.tap_id,
            "candidate_id": self.candidate_id,
            "stage": self.stage,
            "bit_index": self.bit_index,
        }


@dataclass(frozen=True)
class RunTask:
    run_id: str
    case: dict[str, str]
    seed: int
    taps: tuple[Tap, ...]
    config: dict
    checkpoint_path: Path
    result_path: Path


def run_id(case: dict[str, str], seed: int) -> str:
    return f"{case['case_id']}__seed{seed}__{RUN_TAG}"


def _rooted(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _valid_terminal_result(path: Path, expected_run_id: str) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        return False
    return (
        payload.get("schema") == RESULT_SCHEMA
        and payload.get("run_id") == expected_run_id
        and payload.get("state") == "terminal"
    )


def _validate_config(config: dict) -> None:
    attack = config["attack"]
    solver = config["solver"]
    if config["campaign"]["seeds"] != [0, 1, 2]:
        raise ValueError("late one-bit seeds must be exactly [0, 1, 2]")
    if int(config["campaign"]["workers"]) > MAX_WORKERS:
        raise ValueError("late one-bit workers must not exceed 32")
    if (int(attack["depth"]), attack["mode"], int(attack["initial_query_count"])) != (
        2,
        "differential",
        64,
    ):
        raise ValueError("late one-bit campaign requires depth=2, differential, q64")
    if attack["max_adaptive_queries"] is not None:
        raise ValueError("late one-bit adaptive loop must be unlimited")
    for name in ("first_timeout_ms", "second_timeout_ms", "separability_timeout_ms"):
        if int(solver[name]) != 0:
            raise ValueError(f"{name} must be 0 (unlimited)")


def load_tasks(
    config: dict,
    result_dir: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> list[RunTask]:
    _validate_config(config)
    paths = config["paths"]
    result_dir = result_dir or _rooted(paths["result_dir"])
    checkpoint_dir = checkpoint_dir or _rooted(paths["checkpoint_dir"])
    rows = read_csv(_rooted(paths["manifest"]))
    if len(rows) != 32 or len({row["case_id"] for row in rows}) != 32:
        raise ValueError("late one-bit manifest must contain 32 unique cases")

    candidate_map = load_candidate_map()
    tasks = []
    for case in rows:
        candidate = candidate_map[case["candidate_id"]]
        if (
            case["stage"] != candidate["stage"]
            or int(case["bit_index"]) != int(candidate["bit_index"])
        ):
            raise ValueError(f"manifest/candidate mismatch: {case['case_id']}")
        tap_dicts = taps_for_case({"cand_a": case["candidate_id"]}, candidate_map)
        if len(tap_dicts) != 1:
            raise ValueError(f"case does not define exactly one tap: {case['case_id']}")
        tap = Tap(**tap_dicts[0])
        for seed in config["campaign"]["seeds"]:
            identifier = run_id(case, int(seed))
            result_path = result_dir / f"{identifier}.json"
            if _valid_terminal_result(result_path, identifier):
                continue
            tasks.append(
                RunTask(
                    run_id=identifier,
                    case=dict(case),
                    seed=int(seed),
                    taps=(tap,),
                    config=config,
                    checkpoint_path=checkpoint_dir / f"{identifier}.json",
                    result_path=result_path,
                )
            )
    return tasks


def effective_workers(task_count: int, configured: int, requested: int | None) -> int:
    if task_count <= 0:
        return 0
    return min(task_count, configured, requested or configured, MAX_WORKERS)


def dry_run_line(config: dict, pending: int, requested_workers: int | None) -> str:
    seeds = config["campaign"]["seeds"]
    workers = effective_workers(32 * len(seeds), int(config["campaign"]["workers"]), requested_workers)
    attack = config["attack"]
    return (
        f"cases=32 seeds={len(seeds)} runs={32 * len(seeds)} pending={pending} "
        f"workers={workers} bootstrap=q{attack['initial_query_count']} "
        f"max_adaptive_queries=unlimited depth={attack['depth']} mode={attack['mode']}"
    )


def _new_checkpoint(case: dict[str, str], seed: int, tap: dict[str, object]) -> dict:
    return {
        "schema": CHECKPOINT_SCHEMA,
        "run_id": run_id(case, seed),
        "case_id": case["case_id"],
        "candidate_id": case["candidate_id"],
        "seed": seed,
        "tap": tap,
        "bootstrap_query_count": 64,
        "adaptive_plaintexts_hex": [],
        "prior_active_bits": [],
        "steps": [],
        "state": "running",
    }


def _load_checkpoint(
    path: Path,
    case: dict[str, str],
    seed: int,
    tap: dict[str, object],
) -> dict:
    if not path.exists():
        return _new_checkpoint(case, seed, tap)
    payload = json.loads(path.read_text())
    expected = (
        CHECKPOINT_SCHEMA,
        run_id(case, seed),
        case["case_id"],
        case["candidate_id"],
        seed,
        tap,
        64,
    )
    actual = (
        payload.get("schema"),
        payload.get("run_id"),
        payload.get("case_id"),
        payload.get("candidate_id"),
        payload.get("seed"),
        payload.get("tap"),
        payload.get("bootstrap_query_count"),
    )
    if actual != expected:
        raise ValueError("checkpoint identity mismatch")
    adaptive = payload.get("adaptive_plaintexts_hex")
    if not isinstance(adaptive, list) or len(adaptive) != len(set(adaptive)):
        raise ValueError("checkpoint adaptive plaintexts are invalid or duplicated")
    payload.setdefault("steps", [])
    payload.setdefault("prior_active_bits", [])
    payload["state"] = "running"
    return payload


def _nonterminal(checkpoint_path: Path, checkpoint: dict, state: str, detail: object) -> None:
    checkpoint["state"] = state
    checkpoint["nonterminal_detail"] = detail
    write_atomic(checkpoint_path, checkpoint)
    raise NonTerminalState(f"{state}: {detail}")


def _terminal_payload(
    case: dict[str, str],
    seed: int,
    tap: dict[str, object],
    checkpoint: dict,
    terminal: str,
    result: dict,
) -> dict:
    adaptive_count = len(checkpoint["adaptive_plaintexts_hex"])
    return {
        "schema": RESULT_SCHEMA,
        "state": "terminal",
        "run_id": run_id(case, seed),
        "case_id": case["case_id"],
        "candidate_id": case["candidate_id"],
        "seed": seed,
        "tap": tap,
        "tap_count": 1,
        "terminal_classification": terminal,
        "attack_success": terminal in {"fixed_q64_recovered", "adaptive_key_recovered"},
        "bootstrap_query_count": 64,
        "adaptive_query_count": adaptive_count,
        "total_query_count": 64 + adaptive_count,
        "oracle_encryptions": 65 + adaptive_count,
        "steps": checkpoint["steps"],
        "final_solver": result,
    }


def run_late1bit(
    case: dict[str, str],
    seed: int,
    config: dict,
    taps: tuple[Tap | dict[str, object], ...],
    checkpoint_path: Path,
) -> dict:
    _validate_config(config)
    if len(taps) != 1:
        raise ValueError("late one-bit run requires exactly one immutable tap")
    tap = taps[0].as_dict() if isinstance(taps[0], Tap) else dict(taps[0])
    checkpoint = _load_checkpoint(checkpoint_path, case, seed, tap)
    bootstrap = nested_plaintexts(64, seed)
    adaptive = [bytes.fromhex(value) for value in checkpoint["adaptive_plaintexts_hex"]]
    if any(point in bootstrap for point in adaptive):
        raise ValueError("checkpoint repeats a bootstrap plaintext")
    attack = config["attack"]
    solver = config["solver"]
    generation = config["query_generation"]

    while True:
        plaintexts = bootstrap + adaptive
        doc = generate_observation(
            key_for_seed(seed),
            [tap],
            plaintexts,
            int(attack["depth"]),
            attack["mode"],
        )
        result = solver_result(doc, config)
        statuses = (result.get("first_result"), result.get("second_result"))
        if statuses == ("sat", "unsat"):
            terminal = "fixed_q64_recovered" if not adaptive else "adaptive_key_recovered"
            return _terminal_payload(case, seed, tap, checkpoint, terminal, result)
        if statuses != ("sat", "sat"):
            _nonterminal(checkpoint_path, checkpoint, "solver_unresolved", result)

        record = {
            "adaptive_query_index": len(adaptive) + 1,
            "query_count": 64 + len(adaptive),
            "first_result": "sat",
            "second_result": "sat",
        }
        fixed = synthesize_for_candidate_pair(
            doc,
            result["first_model_hex"],
            result["alternative_model"],
            solver["sbox_encoding"],
            solver["separability_timeout_ms"],
            generation["query_domain"],
            int(generation["max_active_bytes"]),
        )
        record["fixed_pair_separability"] = fixed
        fixed_status = fixed.get("status")
        if fixed_status == "sat":
            global_candidate = synthesize_distinguishing_query(
                doc, solver["sbox_encoding"], solver["separability_timeout_ms"],
                generation["query_domain"], int(generation["max_active_bytes"]),
            )
            record["global_candidate"] = global_candidate
            if global_candidate.get("status") != "sat":
                _nonterminal(checkpoint_path, checkpoint, "candidate_portfolio_unresolved", global_candidate)
            candidates = [bytes.fromhex(fixed["plaintext_hex"]), bytes.fromhex(global_candidate["plaintext_hex"])]
            candidates = list(dict.fromkeys(candidates))
            pair_keys = [bytes.fromhex(result["first_model_hex"]), bytes.fromhex(result["alternative_model"])]
            scores = rank_plaintexts(candidates, pair_keys, tap, bootstrap[0], int(attack["depth"]), set(checkpoint["prior_active_bits"]))
            selected = scores[0]
            separating = {"status": "sat", "plaintext_hex": selected["plaintext_hex"]}
            record["dependency_scores"] = [
                {name: (list(value) if name == "rank_key" else value) for name, value in score.items()}
                for score in scores
            ]
            record["separator_source"] = "dependency_guided_pair_global_portfolio"
            checkpoint["prior_active_bits"] = sorted(set(checkpoint["prior_active_bits"]) | set(selected["active_bits"]))
        elif fixed_status == "unsat":
            separating = synthesize_distinguishing_query(
                doc, solver["sbox_encoding"], solver["separability_timeout_ms"],
                generation["query_domain"], int(generation["max_active_bytes"]),
            )
            record["global_separability"] = separating
            record["separator_source"] = "global"
            if separating.get("status") == "unsat":
                checkpoint["steps"].append(record)
                return _terminal_payload(case, seed, tap, checkpoint, "proven_observational_non_recovery", result)
        else:
            _nonterminal(checkpoint_path, checkpoint, "fixed_pair_unresolved", fixed)

        if separating.get("status") != "sat":
            _nonterminal(checkpoint_path, checkpoint, "global_separator_unresolved", separating)
        point = bytes.fromhex(str(separating["plaintext_hex"]))
        if point in plaintexts:
            _nonterminal(
                checkpoint_path,
                checkpoint,
                "duplicate_separator",
                separating,
            )
        adaptive.append(point)
        checkpoint["adaptive_plaintexts_hex"].append(point.hex())
        record["accepted_plaintext_hex"] = point.hex()
        checkpoint["steps"].append(record)
        checkpoint["state"] = "running"
        checkpoint.pop("nonterminal_detail", None)
        write_atomic(checkpoint_path, checkpoint)


def execute_task(task: RunTask) -> dict:
    started = time.perf_counter()
    try:
        payload = run_late1bit(
            task.case,
            task.seed,
            task.config,
            task.taps,
            task.checkpoint_path,
        )
        payload["wall_time"] = time.perf_counter() - started
        return payload
    except BaseException as error:
        return {
            "schema": "late-1bit-error-v1",
            "state": "error",
            "run_id": task.run_id,
            "case_id": task.case["case_id"],
            "seed": task.seed,
            "error": repr(error),
            "traceback": traceback.format_exc(),
            "wall_time": time.perf_counter() - started,
        }


def rebuild_summary(result_dir: Path, summary_path: Path) -> None:
    rows = []
    for path in sorted(result_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError, TypeError):
            continue
        if payload.get("schema") == RESULT_SCHEMA and payload.get("state") == "terminal":
            rows.append(json.dumps(payload, sort_keys=True))
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = summary_path.with_suffix(f".tmp.{os.getpid()}")
    temporary.write_text("\n".join(rows) + ("\n" if rows else ""))
    temporary.replace(summary_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/late_1bit_adaptive.yaml")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--result-dir")
    parser.add_argument("--checkpoint-dir")
    parser.add_argument("--summary")
    parser.add_argument("--errors")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load(_rooted(args.config).read_text())
    paths = config["paths"]
    result_dir = _rooted(args.result_dir or paths["result_dir"])
    checkpoint_dir = _rooted(args.checkpoint_dir or paths["checkpoint_dir"])
    summary = _rooted(args.summary or paths["summary"])
    errors = _rooted(args.errors or paths["errors"])
    tasks = load_tasks(config, result_dir, checkpoint_dir)
    print(dry_run_line(config, len(tasks), args.workers), flush=True)
    if args.dry_run or not tasks:
        return

    result_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    workers = effective_workers(
        len(tasks), int(config["campaign"]["workers"]), args.workers
    )
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
    ) as pool:
        futures = {pool.submit(execute_task, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            payload = future.result()
            if payload["state"] == "terminal":
                write_atomic(task.result_path, payload)
                rebuild_summary(result_dir, summary)
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(errors, payload)
                outcome = "nonterminal_error"
            print(f"[{index}/{len(tasks)}] {task.run_id} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
