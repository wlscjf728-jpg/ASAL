import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).parent))

from oracle import generate_observation
from parallel_runner import (
    append_to_csv,
    key_for_seed,
    load_candidate_map,
    make_plaintexts,
    parse_taps_from_case,
)
from solve_known_mapping import solve_document


PROFILES = [
    {"query_count": 32, "first_timeout_ms": 60_000, "second_timeout_ms": 300_000},
    {"query_count": 64, "first_timeout_ms": 60_000, "second_timeout_ms": 300_000},
    {"query_count": 96, "first_timeout_ms": 60_000, "second_timeout_ms": 300_000},
    {"query_count": 128, "first_timeout_ms": 60_000, "second_timeout_ms": 300_000},
    {"query_count": 192, "first_timeout_ms": 120_000, "second_timeout_ms": 600_000},
    {"query_count": 255, "first_timeout_ms": 120_000, "second_timeout_ms": 1_800_000},
    {"query_count": 255, "first_timeout_ms": None, "second_timeout_ms": None},
]


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def completed_pairs(path):
    done = set()
    if not path.exists():
        return done
    with open(path) as f:
        for row in csv.DictReader(f):
            if row.get("classification") in {"full_key_unique", "ambiguity"}:
                done.add((row["case_id"], int(row["seed"])))
    return done


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def solve_until_confirmed(case_id, case_row, taps, seed, depth, mode, sbox_encoding, diagnostic_timeout_ms, log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    final_row = None

    for profile in PROFILES:
        q = profile["query_count"]
        pts = make_plaintexts(q, seed)
        doc = generate_observation(key_for_seed(seed), taps, pts, depth, mode)
        started = time.perf_counter()
        result = solve_document(
            doc,
            first_timeout_ms=profile["first_timeout_ms"],
            second_timeout_ms=profile["second_timeout_ms"],
            diagnostic_timeout_ms=diagnostic_timeout_ms,
            sbox_encoding=sbox_encoding,
        )
        elapsed = time.perf_counter() - started
        attempt = {
            "query_count": q,
            "first_timeout_ms": profile["first_timeout_ms"],
            "second_timeout_ms": profile["second_timeout_ms"],
            "classification": result["classification"],
            "first_result": result["first_result"],
            "second_result": result["second_result"],
            "elapsed": elapsed,
            "z3_reason_unknown": result.get("z3_reason_unknown", ""),
        }
        attempts.append(attempt)

        final_row = {
            **case_row,
            "case_id": case_id,
            "seed": seed,
            "query_count": q,
            "depth": depth,
            "mode": mode,
            "attempt_count": len(attempts),
            "attempts_json": json.dumps(attempts, sort_keys=True),
            **result,
        }
        write_json(log_dir / f"seed_{seed}_latest.json", final_row)

        if result["classification"] in {"full_key_unique", "ambiguity"}:
            return final_row

    # Reaching this means Z3 returned a non-timeout unknown even without limits.
    # Do not silently map it to a security outcome.
    final_row["monitor_status"] = "blocked_unexpected_unknown"
    return final_row


def case_id_for(row):
    return row["pair_id"] if "pair_id" in row else row["case_id"]


def run_batch(batch, args, config, cand_map, output_file, status_file):
    tasks = []
    done = completed_pairs(output_file)
    for case in batch:
        cid = case_id_for(case)
        taps = parse_taps_from_case(case, cand_map)
        for seed in range(args.seeds):
            if (cid, seed) in done:
                continue
            tasks.append((cid, case, taps, seed))

    if not tasks:
        return {"submitted": 0, "confirmed": 0, "blocked": 0}

    solver_cfg = config["solver"]
    confirmed = 0
    blocked = 0
    with ProcessPoolExecutor(max_workers=min(args.workers, len(tasks))) as pool:
        futures = {
            pool.submit(
                solve_until_confirmed,
                cid,
                case,
                taps,
                seed,
                args.depth,
                args.mode,
                solver_cfg["sbox_encoding"],
                solver_cfg["diagnostic_timeout_ms"],
                Path(args.log_dir) / cid,
            ): (cid, seed)
            for cid, case, taps, seed in tasks
        }
        for future in as_completed(futures):
            cid, seed = futures[future]
            row = future.result()
            append_to_csv(output_file, row)
            if row["classification"] in {"full_key_unique", "ambiguity"}:
                confirmed += 1
            else:
                blocked += 1
            write_json(
                status_file,
                {
                    "active_batch_size": len(batch),
                    "submitted": len(tasks),
                    "confirmed": confirmed,
                    "blocked": blocked,
                    "last_case_id": cid,
                    "last_seed": seed,
                    "last_classification": row["classification"],
                    "updated_at": time.time(),
                },
            )
    return {"submitted": len(tasks), "confirmed": confirmed, "blocked": blocked}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="configs/selected_2bit_gap_parallel.csv")
    ap.add_argument("--output", default="results/raw_solver_runs_2bit_gap_confirmed.csv")
    ap.add_argument("--status", default="results/monitored_gap_status.json")
    ap.add_argument("--log-dir", default="logs/2bit_gap_confirmed")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--batch-cases", type=int, default=10)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--mode", default="differential")
    args = ap.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    config = yaml.safe_load((base_dir / "configs" / "run_config.yaml").read_text())
    config["max_workers"] = min(config["max_workers"], args.workers)
    args.workers = config["max_workers"]

    cases_path = base_dir / args.cases
    output_file = base_dir / args.output
    status_file = base_dir / args.status
    args.log_dir = str(base_dir / args.log_dir)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cand_map = load_candidate_map(base_dir)
    cases = read_csv(cases_path)

    totals = {"submitted": 0, "confirmed": 0, "blocked": 0}
    for start in range(0, len(cases), args.batch_cases):
        batch = cases[start:start + args.batch_cases]
        write_json(
            status_file,
            {
                "phase": "starting_batch",
                "batch_start": start,
                "batch_end": start + len(batch) - 1,
                "total_cases": len(cases),
                "workers": args.workers,
                "updated_at": time.time(),
            },
        )
        result = run_batch(batch, args, config, cand_map, output_file, status_file)
        for key in totals:
            totals[key] += result[key]
        write_json(
            status_file,
            {
                "phase": "finished_batch",
                "batch_start": start,
                "batch_end": start + len(batch) - 1,
                "total_cases": len(cases),
                **totals,
                "updated_at": time.time(),
            },
        )
        if result["blocked"]:
            break

    write_json(status_file, {"phase": "complete", **totals, "updated_at": time.time()})


if __name__ == "__main__":
    main()
