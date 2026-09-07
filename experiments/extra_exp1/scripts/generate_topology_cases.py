#!/usr/bin/env python3
"""
Generate 8 topology-representative case workspaces in extra_exp1/cases/
"""

import os
import shutil
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CASES_DIR = BASE_DIR / "cases"
SHARED_DIR = BASE_DIR / "shared"
EXTRA_EXP_DIR = BASE_DIR.parent / "extra_exp"

TOPOLOGY_CASES = [
    {"id": "case_01_mc009", "bit": 9,   "col": "C0", "byte": 1, "row": 1, "mult": "x3"},
    {"id": "case_02_mc018", "bit": 18,  "col": "C0", "byte": 2, "row": 2, "mult": "x1"},
    {"id": "case_03_mc036", "bit": 36,  "col": "C1", "byte": 0, "row": 0, "mult": "x2"},
    {"id": "case_04_mc054", "bit": 54,  "col": "C1", "byte": 2, "row": 2, "mult": "x1"},
    {"id": "case_05_mc064", "bit": 64,  "col": "C2", "byte": 0, "row": 0, "mult": "x2"},
    {"id": "case_06_mc082", "bit": 82,  "col": "C2", "byte": 2, "row": 2, "mult": "x1"},
    {"id": "case_07_mc100", "bit": 100, "col": "C3", "byte": 0, "row": 0, "mult": "x2"},
    {"id": "case_08_mc118", "bit": 118, "col": "C3", "byte": 2, "row": 2, "mult": "x1"},
]

def generate_case(c):
    cdir = CASES_DIR / c["id"]
    cdir.mkdir(parents=True, exist_ok=True)
    
    # Subdirectories
    (cdir / "dft").mkdir(exist_ok=True)
    (cdir / "inputs").mkdir(exist_ok=True)
    (cdir / "netlist").mkdir(exist_ok=True)
    (cdir / "results" / "evaluator").mkdir(parents=True, exist_ok=True)
    (cdir / "results" / "phase_b").mkdir(parents=True, exist_ok=True)
    (cdir / "logs").mkdir(exist_ok=True)

    # 1. Generate partial_scan_manifest.txt
    manifest_content = f"""# role|source selector used by the evaluator DFT script
target_mc{c['bit']}|aes_core/MC_REG[{c['bit']}]
# 127 state-register decoys are selected by the DFT script from STATE_REG bits.
aes_decoy|aes_core/STATE_REG[0:126]
# 120 independent data/control decoys.
data_control_decoy|decoy_bank/data_control_decoy_reg[0:119]
# 8 independent status/control decoys.
status_control_decoy|decoy_bank/status_control_decoy_reg[0:7]
"""
    (cdir / "dft" / "partial_scan_manifest.txt").write_text(manifest_content)

    # 2. Copy DFT scripts and update local paths if necessary
    shutil.copy(SHARED_DIR / "dft" / "run_dc.tcl", cdir / "dft" / "run_dc.tcl")
    shutil.copy(SHARED_DIR / "dft" / "run_dft.tcl", cdir / "dft" / "run_dft.tcl")
    shutil.copy(SHARED_DIR / "dft" / "scan_constraints.tcl", cdir / "dft" / "scan_constraints.tcl")

    # 3. Generate frozen_case.json
    frozen_case = {
        "case_id": f"topo_MC_{c['bit']}",
        "column": c["col"],
        "row": c["row"],
        "byte": c["byte"],
        "mult": c["mult"],
        "depth": 2,
        "mode": "differential",
        "fixed_query_count": 128,
        "fixed_oracle_encryptions": 129,
        "reference_plaintext_hex": "00000000000000000000000000000000",
        "schema": "topo-eda-frozen-case-v1",
        "tap": {
            "stage": "MC",
            "bit_index": c["bit"]
        }
    }
    (cdir / "inputs" / "frozen_case.json").write_text(json.dumps(frozen_case, indent=2))

    # 4. Copy hidden key and phase0 queries
    shutil.copy(EXTRA_EXP_DIR / "inputs" / "hidden_key.evaluator.json", cdir / "inputs" / "hidden_key.evaluator.json")
    shutil.copy(EXTRA_EXP_DIR / "inputs" / "phase0_queries.json", cdir / "inputs" / "phase0_queries.json")

    print(f"Generated {c['id']} (Bit {c['bit']}, Col {c['col']}, Row {c['row']}, {c['mult']})")

def main():
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    for c in TOPOLOGY_CASES:
        generate_case(c)
    print("All 8 topology cases successfully created!")

if __name__ == "__main__":
    main()
