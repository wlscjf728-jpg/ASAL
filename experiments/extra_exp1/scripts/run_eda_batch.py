#!/usr/bin/env python3
"""
Run DC synthesis and DFT scan insertion across all 8 topology cases in extra_exp1.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = Path(__file__).resolve().parents[1]
CASES_DIR = BASE_DIR / "cases"

def run_case_eda(cdir):
    case_name = cdir.name
    print(f"[{case_name}] Starting DC Pre-DFT Synthesis...")
    t0 = time.time()
    
    # 1. Run DC Pre-DFT Synthesis
    dc_cmd = f"dc_shell -f {cdir}/dft/run_dc.tcl"
    dc_log = cdir / "logs" / "run_dc.log"
    with open(dc_log, "w") as f:
        res = subprocess.run(dc_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        print(f"[{case_name}] ERROR in DC Pre-DFT synthesis! See {dc_log}")
        return False, case_name, "DC_FAILED"
    
    # 2. Run DFT Scan Insertion
    print(f"[{case_name}] Starting DFT Scan Insertion...")
    dft_cmd = f"dc_shell -f {cdir}/dft/run_dft.tcl"
    dft_log = cdir / "logs" / "run_dft.log"
    with open(dft_log, "w") as f:
        res = subprocess.run(dft_cmd, shell=True, cwd=cdir, stdout=f, stderr=subprocess.STDOUT)
    if res.returncode != 0:
        print(f"[{case_name}] ERROR in DFT scan insertion! See {dft_log}")
        return False, case_name, "DFT_FAILED"
        
    t1 = time.time()
    print(f"[{case_name}] SUCCESS in {t1 - t0:.1f}s!")
    return True, case_name, "SUCCESS"

def main():
    cases = sorted([d for d in CASES_DIR.glob("case_*") if d.is_dir()])
    print(f"Starting EDA batch for {len(cases)} cases...")
    
    # Run in parallel with max 4 workers to balance CPU and memory
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_case_eda, cases))
        
    all_success = True
    for success, name, status in results:
        print(f"Case {name}: {status}")
        if not success:
            all_success = False
            
    if all_success:
        print("All 8 cases successfully synthesized with DFT!")
        sys.exit(0)
    else:
        print("Some cases failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
