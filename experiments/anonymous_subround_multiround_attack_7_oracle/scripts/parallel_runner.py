import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
import yaml
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Ensure scripts directory is in path to import locally copied modules
sys.path.append(str(Path(__file__).parent))

from oracle import generate_observation
from solve_known_mapping import solve_document

def key_for_seed(seed):
    return hashlib.sha256(f"oracle-key-{seed}".encode()).digest()[:16]

def make_plaintexts(query_count, seed):
    rng = random.Random(seed * 65537 + 17)
    base = bytes(16)
    points = [base]
    seen = {base}
    while len(points) <= query_count:
        p = bytearray(16)
        p[rng.randrange(16)] = rng.randrange(1, 256)
        p = bytes(p)
        if p not in seen:
            points.append(p)
            seen.add(p)
    return points

def parse_taps_from_case(case, cand_map):
    # Parse cand_a and cand_b from the case
    cands = [case["cand_a"], case["cand_b"]]
    if "cand_c" in case and case["cand_c"]:
        cands.append(case["cand_c"])
    if "cand_d" in case and case["cand_d"]:
        cands.append(case["cand_d"])
        
    taps = []
    for i, c_id in enumerate(cands):
        c_info = cand_map[c_id]
        taps.append({
            "tap_id": f"t{i}",
            "stage": c_info["stage"],
            "bit_index": int(c_info["bit_index"])
        })
    return taps

def run_single_seed(case_id, taps, seed, depth, mode, config_solver, log_dir):
    first_timeout = config_solver["first_timeout_ms"]
    second_timeout = config_solver["second_timeout_ms"]
    diagnostic_timeout = config_solver["diagnostic_timeout_ms"]
    sbox_encoding = config_solver["sbox_encoding"]
    
    ladder = [32, 64, 96, 128]
    final_res = None
    
    for q in ladder:
        # Create log path
        log_file = log_dir / f"seed_{seed}" / f"q{q}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        pts = make_plaintexts(q, seed)
        doc = generate_observation(key_for_seed(seed), taps, pts, depth, mode)
        
        # Save output redirect to log file
        # Solve
        res = solve_document(
            doc,
            first_timeout_ms=first_timeout,
            second_timeout_ms=second_timeout,
            diagnostic_timeout_ms=diagnostic_timeout,
            sbox_encoding=sbox_encoding
        )
        
        final_res = {
            "case_id": case_id,
            "seed": seed,
            "query_count": q,
            "depth": depth,
            "mode": mode,
            **res
        }
        
        # Log resolution status
        with open(log_file, "w") as lf:
            lf.write(f"Query {q} result: {res['classification']}\n")
            lf.write(json.dumps(res, indent=2) + "\n")
            
        # Early stop if unique
        if res["classification"] == "full_key_unique":
            break
            
    # Escalation for UNKNOWN
    if final_res["classification"] == "undecided":
        for escalated_q in [192, 255]:
            log_file = log_dir / f"seed_{seed}" / f"q{escalated_q}_escalated.log"
            pts = make_plaintexts(escalated_q, seed)
            doc = generate_observation(key_for_seed(seed), taps, pts, depth, mode)
            
            # Run with double alternative key timeout
            res = solve_document(
                doc,
                first_timeout_ms=first_timeout,
                second_timeout_ms=second_timeout * 2,
                diagnostic_timeout_ms=diagnostic_timeout,
                sbox_encoding=sbox_encoding
            )
            
            final_res = {
                "case_id": case_id,
                "seed": seed,
                "query_count": escalated_q,
                "depth": depth,
                "mode": mode,
                **res
            }
            
            with open(log_file, "w") as lf:
                lf.write(f"Escalated Query {escalated_q} result: {res['classification']}\n")
                lf.write(json.dumps(res, indent=2) + "\n")
                
            if res["classification"] != "undecided":
                break
                
    return final_res

def load_completed_jobs(results_file):
    completed = {}
    if not results_file.exists():
        return completed
    try:
        with open(results_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = row["case_id"]
                seed = int(row["seed"])
                if case_id not in completed:
                    completed[case_id] = set()
                completed[case_id].add(seed)
    except Exception:
        pass
    return completed

def load_candidate_map(base_dir):
    cand_map = {}
    # Read both core384 and extended512 maps to be fully flexible
    for name in ["candidate_map_core384.csv", "candidate_map_extended512.csv"]:
        path = base_dir / "results" / name
        if path.exists():
            with open(path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cand_map[row["candidate_id"]] = row
    return cand_map

def append_to_csv(results_file, row):
    exists = results_file.exists()
    # Flatten JSON fields
    flat_row = {}
    for k, v in row.items():
        if isinstance(v, (list, dict)):
            flat_row[k] = json.dumps(v)
        else:
            flat_row[k] = v
            
    with open(results_file, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(flat_row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(flat_row)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, help="CSV path of selected cases to execute")
    ap.add_argument("--type", choices=["2bit", "3bit", "4bit"], required=True)
    ap.add_argument("--seeds", type=int, default=20, help="Number of seeds to run (1..20)")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--mode", default="differential")
    ap.add_argument("--resume", action="store_true", default=True)
    a = ap.parse_args()
    
    base_dir = Path(__file__).parent.parent
    
    # Load config
    with open(base_dir / "configs" / "run_config.yaml") as f:
        config = yaml.safe_load(f)
        
    max_workers = config["max_workers"]
    config_solver = config["solver"]
    
    # Paths
    results_file = base_dir / "results" / f"raw_solver_runs_{a.type}.csv"
    log_dir = base_dir / "logs" / a.type
    
    # Load candidates
    cand_map = load_candidate_map(base_dir)
    
    # Read cases
    cases = []
    with open(a.cases) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)
            
    completed = load_completed_jobs(results_file) if a.resume else {}
    
    # Build list of parallel tasks
    tasks = []
    for case in cases:
        case_id = case["pair_id"] if "pair_id" in case else case["case_id"]
        taps = parse_taps_from_case(case, cand_map)
        completed_seeds = completed.get(case_id, set())
        
        for seed in range(a.seeds):
            if seed in completed_seeds:
                continue
            tasks.append((case_id, taps, seed, case, a.depth, a.mode, config_solver, log_dir / case_id))
            
    print(f"Total parallel seeds to run: {len(tasks)} using {max_workers} processes")
    
    # Execute in ProcessPool
    start_time = time.perf_counter()
    completed_count = 0
    unique_count = 0
    ambiguity_count = 0
    unknown_count = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for task in tasks:
            case_id, taps, seed, case_row, depth, mode, solver_cfg, case_log_dir = task
            future = executor.submit(run_single_seed, case_id, taps, seed, depth, mode, solver_cfg, case_log_dir)
            futures[future] = (case_id, seed, case_row)
            
        for future in as_completed(futures):
            case_id, seed, case_row = futures[future]
            try:
                res = future.result()
                completed_count += 1
                
                # Combine case features with solver output
                row_out = {**case_row, **res}
                append_to_csv(results_file, row_out)
                
                cls = res["classification"]
                if cls == "full_key_unique":
                    unique_count += 1
                elif cls == "ambiguity":
                    ambiguity_count += 1
                else:
                    unknown_count += 1
                    
                elapsed = time.perf_counter() - start_time
                avg_time = elapsed / completed_count
                est_rem = avg_time * (len(tasks) - completed_count)
                
                # Concise summary line
                print(f"[{completed_count}/{len(tasks)}] {case_id} seed {seed} -> {cls} (Q{res['query_count']}) | Unique: {unique_count}, Amb: {ambiguity_count}, Unk: {unknown_count} | Avg: {avg_time:.1f}s, Est Rem: {est_rem/60.0:.1f}m", flush=True)
                
            except Exception as e:
                print(f"Job failed: {case_id} seed {seed} -> Error: {e}", flush=True)
                
    print(f"Sweep completed. Total runs: {completed_count}")

if __name__ == "__main__":
    main()
