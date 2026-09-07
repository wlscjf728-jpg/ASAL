#!/usr/bin/env python3
"""
Run VCS gate-level simulation and Phase 0 discovery for all 8 topology cases in extra_exp1.
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
SHARED_DIR = BASE_DIR / "shared"
SIM_CELL = SHARED_DIR / "tb" / "class_scan_sim.v"
TB_FILE = SHARED_DIR / "tb" / "tb_gate_capture.sv"
DISCOVERY_SCRIPT = SHARED_DIR / "scripts" / "run_phase0_discovery.py"
MAKE_INPUTS = SHARED_DIR / "scripts" / "make_gate_inputs.py"

def run_case_phase0(cdir):
    case_name = cdir.name
    print(f"[{case_name}] Starting VCS Compile & Phase 0 Discovery...")
    t0 = time.time()
    
    netlist = cdir / "netlist" / "extra_exp_postscan.v"
    simv = cdir / "results" / "simv_capture"
    log_dir = cdir / "logs"
    phase_b = cdir / "results" / "phase_b"
    phase_b.mkdir(parents=True, exist_ok=True)
    
    # 1. Compile with VCS
    vcs_log = log_dir / "vcs_compile.log"
    vcs_cmd = (
        f"vcs -full64 -sverilog -O3 -timescale=1ns/1ps -o {simv} -top tb_gate_capture "
        f"{SIM_CELL} {netlist} {TB_FILE}"
    )
    with open(vcs_log, "w") as f:
        res = subprocess.run(vcs_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        print(f"[{case_name}] VCS compile failed! See {vcs_log}")
        return False, case_name, "VCS_COMPILE_FAILED"

    # 2. Prepare query files
    query_json = cdir / "inputs" / "phase0_queries.json"
    queries_txt = phase_b / "phase0_queries.txt"
    repeat_txt = phase_b / "phase0_repeat_queries.txt"
    nostart_txt = phase_b / "phase0_nostart_queries.txt"
    
    subprocess.run(f"python3 {MAKE_INPUTS} --input {query_json} --output {queries_txt}", shell=True, check=True)
    repeat_txt.write_text("0 00000000000000000000000000000000\n0 00000000000000000000000000000000\n")
    nostart_txt.write_text("0 00000000000000000000000000000000\n")

    # 3. Run VCS gate simulation
    hidden_key = "a66f651322597191ab9f8f8af4c2db61"
    scan_raw = phase_b / "phase0_gate_scan.txt"
    repeat_raw = phase_b / "phase0_repeat_gate_scan.txt"
    nostart_raw = phase_b / "phase0_nostart_gate_scan.txt"
    
    cmd_full = f"{simv} +KEY_HEX={hidden_key} +QUERY_FILE={queries_txt} +OUT_FILE={scan_raw}"
    cmd_repeat = f"{simv} +KEY_HEX={hidden_key} +QUERY_FILE={repeat_txt} +OUT_FILE={repeat_raw}"
    cmd_nostart = f"{simv} +KEY_HEX={hidden_key} +NO_START +QUERY_FILE={nostart_txt} +OUT_FILE={nostart_raw}"
    
    with open(log_dir / "vcs_run_full.log", "w") as f:
        subprocess.run(cmd_full, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT, check=True)
    with open(log_dir / "vcs_run_repeat.log", "w") as f:
        subprocess.run(cmd_repeat, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT, check=True)
    with open(log_dir / "vcs_run_nostart.log", "w") as f:
        subprocess.run(cmd_nostart, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT, check=True)

    # 4. Run Phase 0 Discovery
    disc_json = phase_b / "phase0_discovery.json"
    attack_txt = phase_b / "phase0_gate_scan_attack.txt"
    disc_cmd = (
        f"python3 {DISCOVERY_SCRIPT} --capture {scan_raw} --repeat {repeat_raw} "
        f"--no-start {nostart_raw} --out {disc_json} --attack-out {attack_txt}"
    )
    with open(log_dir / "phase0_discovery.log", "w") as f:
        res = subprocess.run(disc_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        print(f"[{case_name}] Phase 0 discovery failed! See {log_dir / 'phase0_discovery.log'}")
        return False, case_name, "DISCOVERY_FAILED"

    # Verify discovery data
    data = json.loads(disc_json.read_text())
    selected_slot = data["final_selected_slot"]["scan_out_index"]
    detected_col = data["final_selected_slot"]["nearest_mc_column"]
    score = data["final_selected_slot"]["score"]
    
    t1 = time.time()
    print(f"[{case_name}] SUCCESS in {t1 - t0:.1f}s -> Slot {selected_slot}, Col {detected_col}, Score {score}")
    return True, case_name, f"Slot {selected_slot}, {detected_col}"

def main():
    cases = sorted([d for d in CASES_DIR.glob("case_*") if d.is_dir()])
    print(f"Starting Phase 0 batch for {len(cases)} cases...")
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_case_phase0, cases))
        
    all_success = True
    for success, name, status in results:
        print(f"Case {name}: {status}")
        if not success:
            all_success = False
            
    if all_success:
        print("All 8 cases completed Phase 0 discovery successfully!")
        sys.exit(0)
    else:
        print("Some cases failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
