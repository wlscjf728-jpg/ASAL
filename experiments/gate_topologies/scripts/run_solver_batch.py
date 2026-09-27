#!/usr/bin/env python3
"""
End-to-End Function Attribution & Adaptive Key Recovery Batch Runner for gate_topologies.

For each of the 8 topology cases:
1. Executes 128 fixed queries on the gate-level VCS DUT.
2. Builds 32 anonymous column hypotheses (matching detected column C0, C1, C2, or C3).
3. Performs hypothesis consistency checking: exactly 1 target hypothesis survives, 31 become UNSAT.
4. Evaluates Q128 fixed solver status (ambiguity: Solve 1 SAT & Solve 2 SAT).
5. Executes the closed-loop adaptive loop:
   - Synthesizes distinguishing separator plaintext (Psep).
   - Re-injects Psep into the gate-level VCS DUT.
   - Appends differential scan observation.
   - Iterates until Solve 1 SAT & Solve 2 UNSAT (full key uniqueness).
6. Verifies recovered key matches hidden K0 and outputs final_attribution_closed_loop.json.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = Path(__file__).resolve().parents[1]
CASES_DIR = BASE_DIR / "cases"
SHARED_SCRIPTS = BASE_DIR / "shared" / "scripts"
PYTHON_BIN = sys.executable

def run_case_solver(cdir):
    case_name = cdir.name
    print(f"[{case_name}] Starting Attribution & Adaptive Key Recovery...")
    t0 = time.time()
    
    phase_b = cdir / "results" / "phase_b"
    log_dir = cdir / "logs"
    simv = cdir / "results" / "simv_capture"
    disc_data = json.loads((phase_b / "phase0_discovery.json").read_text())
    slot = disc_data["final_selected_slot"]["scan_out_index"]
    col = disc_data["final_selected_slot"]["nearest_mc_column"]
    
    hidden_key_file = cdir / "inputs" / "hidden_key.evaluator.json"
    hidden_key = json.loads(hidden_key_file.read_text())["true_key_hex"]
    
    # Step 1: Gate-level simulation for 128 queries
    q128_queries = phase_b / "q128_queries.txt"
    q128_scan = phase_b / "q128_gate_scan.txt"
    vcs_cmd = f"{simv} +KEY_HEX={hidden_key} +QUERY_FILE={q128_queries} +OUT_FILE={q128_scan}"
    with open(log_dir / "vcs_q128_run.log", "w") as f:
        subprocess.run(vcs_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT, check=True)
        
    # Step 2: Build Q128 32-hypothesis transcript
    q128_transcript = phase_b / "q128_mc_hypotheses_attack.json"
    build_cmd = (
        f"{PYTHON_BIN} {SHARED_SCRIPTS}/build_mc_hypothesis_observation.py "
        f"--capture {q128_scan} --queries {q128_queries} --slot {slot} "
        f"--column {col} --output {q128_transcript}"
    )
    subprocess.run(build_cmd, shell=True, check=True)
    
    # Step 3: Run Q128 32-hypothesis solver (Attribution prune 32 -> 1)
    q128_solver = phase_b / "q128_mc_hypothesis_solver_attack.json"
    solve_cmd = (
        f"{PYTHON_BIN} {SHARED_SCRIPTS}/run_mc_hypothesis_solver.py "
        f"--input {q128_transcript} --output {q128_solver} --workers 16"
    )
    with open(log_dir / "q128_solver.log", "w") as f:
        subprocess.run(solve_cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, check=True)
        
    s128 = json.loads(q128_solver.read_text())
    surviving_cnt = s128["surviving_hypothesis_count"]
    surviving_h = s128["surviving_hypotheses"][0]["hypothesis_id"]
    print(f"[{case_name}] Attribution Complete: 32 -> {surviving_cnt} ({surviving_h})")
    
    # Step 4: Prune transcript to surviving hypothesis
    q_current = phase_b / "q129_mc_hypotheses_attack_pruned.json"
    filter_cmd = (
        f"{PYTHON_BIN} {SHARED_SCRIPTS}/filter_mc_hypotheses.py "
        f"--transcript {q128_transcript} --solver-result {q128_solver} --output {q_current}"
    )
    subprocess.run(filter_cmd, shell=True, check=True)
    
    # Step 5: Adaptive Query Loop until SAT -> UNSAT
    adaptive_query_idx = 129
    final_classification = "ambiguity"
    recovered_key = ""
    
    while adaptive_query_idx <= 135:
        q_solver = phase_b / f"q{adaptive_query_idx}_mc_hypothesis_solver_attack.json"
        solve_cmd = (
            f"{PYTHON_BIN} {SHARED_SCRIPTS}/run_mc_hypothesis_solver.py "
            f"--input {q_current} --output {q_solver} --workers 1"
        )
        with open(log_dir / f"q{adaptive_query_idx}_solver.log", "w") as f:
            subprocess.run(solve_cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, check=True)
            
        s_res = json.loads(q_solver.read_text())
        first_res = s_res["joint_key_uniqueness"]["first_result"]
        second_res = s_res["joint_key_uniqueness"]["second_result"]
        recovered_key = s_res["joint_key_uniqueness"]["first_model_hex"]
        
        print(f"[{case_name}] Q{adaptive_query_idx}: Solve 1 = {first_res}, Solve 2 = {second_res}")
        
        if second_res == "unsat":
            final_classification = "full_key_unique"
            break
            
        # Synthesize separator plaintext
        sep_json = phase_b / f"adaptive_sep_q{adaptive_query_idx}.json"
        sep_cmd = (
            f"{PYTHON_BIN} {SHARED_SCRIPTS}/generate_mc_hypothesis_separator.py "
            f"--input {q_current} --solver-result {q_solver} --output {sep_json}"
        )
        subprocess.run(sep_cmd, shell=True, check=True)
        sep_doc = json.loads(sep_json.read_text())
        psep = sep_doc["plaintext_hex"]
        
        # VCS Query
        sep_query_txt = phase_b / f"sep_q{adaptive_query_idx}_query.txt"
        sep_scan_txt = phase_b / f"sep_q{adaptive_query_idx}_scan.txt"
        ref_p = json.loads(q_current.read_text())["observations"][0]["plaintext_hex"]
        sep_query_txt.write_text(f"0 {ref_p}\n1 {psep}\n")
        
        vcs_sep_cmd = f"{simv} +KEY_HEX={hidden_key} +QUERY_FILE={sep_query_txt} +OUT_FILE={sep_scan_txt}"
        with open(log_dir / f"vcs_sep_q{adaptive_query_idx}.log", "w") as f:
            subprocess.run(vcs_sep_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT, check=True)
            
        # Build extra observation
        extra_obs = phase_b / f"extra_obs_q{adaptive_query_idx}.json"
        build_extra_cmd = (
            f"{PYTHON_BIN} {SHARED_SCRIPTS}/build_mc_hypothesis_observation.py "
            f"--capture {sep_scan_txt} --queries {sep_query_txt} --slot {slot} "
            f"--column {col} --hypotheses-from {q_current} --output {extra_obs}"
        )
        subprocess.run(build_extra_cmd, shell=True, check=True)
        
        # Append observation
        adaptive_query_idx += 1
        q_next = phase_b / f"q{adaptive_query_idx}_mc_hypotheses_attack_pruned.json"
        append_cmd = (
            f"{PYTHON_BIN} {SHARED_SCRIPTS}/append_mc_hypothesis_observation.py "
            f"--base {q_current} --extra {extra_obs} --output {q_next}"
        )
        subprocess.run(append_cmd, shell=True, check=True)
        q_current = q_next

    key_match = (recovered_key == hidden_key)
    elapsed = time.time() - t0
    
    summary = {
        "case_name": case_name,
        "selected_slot": slot,
        "column": col,
        "surviving_hypothesis_count": surviving_cnt,
        "surviving_hypothesis_id": surviving_h,
        "fixed_query_count": 128,
        "final_query_count": adaptive_query_idx,
        "final_classification": final_classification,
        "recovered_key": recovered_key,
        "hidden_key": hidden_key,
        "final_key_match": key_match,
        "elapsed_seconds": elapsed
    }
    
    summary_path = phase_b / "final_attribution_closed_loop.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[{case_name}] FINISHED in {elapsed:.1f}s -> {final_classification}, Key Match: {key_match} ({adaptive_query_idx} queries)")
    return key_match, case_name, summary

def main():
    cases = sorted([d for d in CASES_DIR.glob("case_*") if d.is_dir()])
    print(f"Starting Solver & Key Recovery batch for {len(cases)} cases...")
    
    # Run across 4 parallel worker processes
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_case_solver, cases))
        
    all_success = True
    for success, name, summary in results:
        print(f"Case {name}: KeyMatch={success}, Queries={summary['final_query_count']}, Status={summary['final_classification']}")
        if not success:
            all_success = False
            
    if all_success:
        print("All 8 cases completed Function Attribution & Key Recovery with 100% SUCCESS!")
        sys.exit(0)
    else:
        print("Some cases failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
