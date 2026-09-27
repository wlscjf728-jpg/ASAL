"""Attack 8 Parallel Runner using spawn context for Z3 safety."""
from __future__ import annotations

import argparse
import json
import time
import sys
import multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import yaml

# Add scripts directory to path to import local modules
sys.path.append(str(Path(__file__).parent))

from experiment_common import ROOT, load_candidate_map, read_csv, taps_for_case, append_jsonl

# Delay imports of Z3-dependent modules to workers
def run_task(case, seed, strategy, config, taps):
    try:
        started = time.perf_counter()
        # Import inside worker to ensure clean Z3 initialization
        from adaptive_query_attack import fixed_nested_run, adaptive_run
        
        if strategy == "fixed_nested":
            payload = fixed_nested_run(case, seed, config, taps)
        else:
            payload = adaptive_run(case, seed, config, taps)
        payload["wall_time"] = time.perf_counter() - started
        return {"status": "ok", "payload": payload}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="configs/selected_2bit_proven_ambiguous.csv")
    parser.add_argument("--strategy", choices=("fixed_nested", "adaptive_pairwise"), required=True)
    parser.add_argument("--config", default="configs/run_config.yaml")
    parser.add_argument("--output", default="results/attack_runs.jsonl")
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--workers", type=int, default=96)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    cases = read_csv(ROOT / args.cases)
    if args.case_limit is not None:
        cases = cases[: args.case_limit]
    seed_count = args.seeds if args.seeds is not None else int(config["campaign"]["seeds"])
    candidate_map = load_candidate_map()
    output = ROOT / args.output
    
    # Import Z3-dependent module only in parent for checklist, but we use spawn context for workers
    from adaptive_query_attack import existing_run_ids
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

    print(f"strategy={args.strategy} cases={len(cases)} seeds={seed_count} pending_runs={len(planned)} using {args.workers} workers (spawn context)")
    if args.dry_run:
        for case, seed, taps in planned[:10]:
            print(case["attack8_case_id"], seed, [(tap["stage"], tap["bit_index"]) for tap in taps])
        return

    if len(planned) == 0:
        print("No runs to execute. All planned runs are already completed.")
        return

    start_time = time.perf_counter()
    completed_count = 0
    unique_count = 0
    ambiguity_count = 0
    support_limited_count = 0
    budget_exhausted_count = 0
    other_count = 0

    # Use explicit spawn context for Z3 safety
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(mp_context=ctx, max_workers=args.workers) as executor:
        futures = {}
        for case, seed, taps in planned:
            future = executor.submit(run_task, case, seed, args.strategy, config, taps)
            futures[future] = (case["attack8_case_id"], seed)

        for future in as_completed(futures):
            case_id, seed = futures[future]
            try:
                result = future.result()
                if result["status"] == "error":
                    print(f"Worker task error for {case_id} seed {seed}:\n{result['traceback']}", flush=True)
                    continue

                payload = result["payload"]
                completed_count += 1
                append_jsonl(output, payload)

                tc = payload["terminal_classification"]
                if tc == "full_key_unique":
                    unique_count += 1
                elif tc in ("finite_budget_ambiguity", "ambiguity", "finite_transcript_ambiguity"):
                    ambiguity_count += 1
                elif tc == "support_limited_ambiguity":
                    support_limited_count += 1
                elif tc == "query_budget_exhausted":
                    budget_exhausted_count += 1
                else:
                    other_count += 1

                elapsed = time.perf_counter() - start_time
                avg_time = elapsed / completed_count
                est_rem = avg_time * (len(planned) - completed_count)

                print(
                    f"[{completed_count}/{len(planned)}] {payload['run_id']} -> {tc} "
                    f"q={payload['query_count']} | Unique: {unique_count}, Amb: {ambiguity_count}, "
                    f"Support-Lim: {support_limited_count}, Budget-Exhausted: {budget_exhausted_count}, Other: {other_count} | "
                    f"Avg: {avg_time:.1f}s, Est Rem: {est_rem/60.0:.1f}m",
                    flush=True,
                )
            except Exception as e:
                print(f"Job crashed: {case_id} seed {seed} -> Error: {e}", flush=True)

    print(f"Parallel runner campaign completed. Total runs: {completed_count} in {time.perf_counter() - start_time:.1f}s")

if __name__ == "__main__":
    main()
