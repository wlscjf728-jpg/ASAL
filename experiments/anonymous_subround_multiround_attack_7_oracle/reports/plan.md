# AES-128 Sparse Scan Leakage Phase 7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analyze AES-128 key recovery under sparse 1-bit scan leakage (core384 and extended512 maps) using Z3 solver optimization, query laddering, and parallel execution to produce risk maps and evaluate early-only/late topologies.

**Architecture:** A modular framework in Python. Taps are mapped to coordinates (byte, row, col, bit). A structural classifier groups pairs into risk classes. Prior results are imported, and new runs are executed using parallel multiprocessing with nested query early-stopping.

**Tech Stack:** Python 3, Z3 SMT solver, multiprocessing, CSV/JSON processing.

---

## Files to be Created or Modified

* `scripts/aes_ref.py`: Copy of AES reference implementation.
* `scripts/z3_aes.py`: Copy of AES Z3 graph builder.
* `scripts/oracle.py`: Copy of observation generator.
* `scripts/solve_known_mapping.py`: Copy of known mapping evaluator.
* `scripts/generate_candidate_map.py`: Coordinates mapper.
* `scripts/generate_pair_structural_map.py`: Structural topology classifier.
* `scripts/import_prior_results.py`: Parser to import Attack 5/6 results.
* `scripts/select_cases.py`: Script to select 2bit cases based on risk class.
* `scripts/parallel_runner.py`: Multiprocessing job runner with query laddering, early-stopping, and timeout escalation.
* `scripts/verify_reproduction_monotonicity.py`: Check reproduction accuracy and subset monotonicity.
* `configs/run_config.yaml`: Concurrency and timeout parameters.
* `configs/selected_2bit_cases_round1.csv`: Selected 2bit cases.
* `configs/selected_3bit_hard_cases.csv`: Hard 3bit cases.
* `configs/selected_4bit_hard_cases.csv`: Hard 4bit cases.
* `reports/00_prior_experiment_inventory.md`: Review of prior results.
* `reports/01_reproduction_validation.md`: Reproduction sanity check report.
* `reports/02_monotonicity_validation.md`: Monotonicity check report.
* `reports/03_two_bit_risk_map.md`: 2-bit risk map report.
* `reports/04_three_bit_hard_cases.md`: 3-bit hard case report.
* `reports/05_four_bit_hard_cases.md`: 4-bit hard case report.
* `reports/FINAL_REPORT_7.md`: Overall project synthesis report.

---

### Task 1: Inventory of Prior Experiments

**Files:**
- Create: `reports/00_prior_experiment_inventory.md`

- [ ] **Step 1: Write the inventory report**
  Analyze results of Attack 5 & 6, list confirmed unique/ambiguous/unknown topologies, and specify files to reuse.
- [ ] **Step 2: Commit Task 1**
  Commit the inventory report.

---

### Task 2: Copying and Adapting Core Code

**Files:**
- Create: `scripts/aes_ref.py`, `scripts/z3_aes.py`, `scripts/oracle.py`, `scripts/solve_known_mapping.py`, `scripts/local_candidates.py`

- [ ] **Step 1: Copy core files from Attack 6**
  Copy `aes_ref.py`, `z3_aes.py`, `oracle.py`, `solve_known_mapping.py`, `local_candidates.py` from `anonymous_subround_multiround_attack_6_oracle` to `scripts/`.
- [ ] **Step 2: Clean up imports and paths in the scripts**
  Adjust the local Python import paths in the scripts folder.
- [ ] **Step 3: Test z3 solver import**
  Run: `python3 -c "import scripts.solve_known_mapping"`
  Expected: No import errors.
- [ ] **Step 4: Commit Task 2**
  Commit the copied scripts.

---

### Task 3: Candidate Coordinate Map Generation

**Files:**
- Create: `scripts/generate_candidate_map.py`
- Create: `results/candidate_map_core384.csv`, `results/candidate_map_extended512.csv`

- [ ] **Step 1: Write generate_candidate_map.py**
  Create coordinate generator for 384 candidates (SB, SR, MC) and 512 candidates (SB, SR, MC, ARK). Coordinates: byte, row, col, bit_in_byte, class.
- [ ] **Step 2: Run coordinate map generation**
  Run: `python3 scripts/generate_candidate_map.py`
  Expected: CSV files generated with 384 and 512 rows respectively, headers matching candidate schema.
- [ ] **Step 3: Commit Task 3**
  Commit the candidate map scripts and CSVs.

---

### Task 4: Pair Topology Classifier

**Files:**
- Create: `scripts/generate_pair_structural_map.py`
- Create: `results/pair_structural_map_core384.csv`, `results/pair_structural_map_extended512.csv`

- [ ] **Step 1: Write generate_pair_structural_map.py**
  Write classifier for all $\binom{384}{2}$ and $\binom{512}{2}$ pairs. Set topological features (same_stage, same_byte, same_row, same_col, same_col_samebit, same_col_diagbit, distinct_row, distinct_diag, expected_risk_class, etc.).
- [ ] **Step 2: Run structural map generation**
  Run: `python3 scripts/generate_pair_structural_map.py`
  Expected: Two structural map CSVs generated.
- [ ] **Step 3: Commit Task 4**
  Commit scripts and maps.

---

### Task 5: Import Prior Results

**Files:**
- Create: `scripts/import_prior_results.py`
- Create: `results/prior_2bit_results_imported.csv`

- [ ] **Step 1: Write import_prior_results.py**
  Write a script to parse csv results from Attack 5/6 and write them to `results/prior_2bit_results_imported.csv` using canonical column names.
- [ ] **Step 2: Run import script**
  Run: `python3 scripts/import_prior_results.py`
  Expected: imported CSV with 2bit results and correct statuses.
- [ ] **Step 3: Commit Task 5**
  Commit import files.

---

### Task 6: Smart Case Selection

**Files:**
- Create: `scripts/select_cases.py`
- Create: `configs/selected_2bit_cases_round1.csv`

- [ ] **Step 1: Write select_cases.py**
  Implement logic to sample representative 2bit pairs from core384 and extended512 topologies (around 100-250 cases total) and assign selection reasons.
- [ ] **Step 2: Generate config**
  Run: `python3 scripts/select_cases.py`
  Expected: CSV generated containing around 150 unique 2bit cases with selection reasons.
- [ ] **Step 3: Commit Task 6**
  Commit case selection files.

---

### Task 7: Concurrency Config and Parallel Runner

**Files:**
- Create: `configs/run_config.yaml`
- Create: `scripts/parallel_runner.py`

- [ ] **Step 1: Create configs/run_config.yaml**
  Set `max_workers` to 16, default timeouts (first=60s, second=300s, diagnostic=30s), and debug levels.
- [ ] **Step 2: Write parallel_runner.py with query laddering & nested query sets**
  Implement runner that launches Z3 solver threads/processes. Implement early-stopping (if unique at q32, don't run q64/q96/q128 for that seed). Save logs to `logs/{2bit,3bit,4bit}/{case_id}/seed_{seed}/q{query}.log`. Write intermediate results to JSONL.
- [ ] **Step 3: Commit Task 7**
  Commit the config and parallel runner code.

---

### Task 8: Reproduction and Monotonicity Validation Checks

**Files:**
- Create: `scripts/verify_reproduction_monotonicity.py`
- Create: `reports/01_reproduction_validation.md`, `reports/02_monotonicity_validation.md`

- [ ] **Step 1: Write verify_reproduction_monotonicity.py**
  Implement reproduction test of mc_same_byte_2 (should be 20/20 unique at depth2/q128/differential) and sb_same_byte_2 (should be 0/20 unique, 20/20 ambiguity). Implement monotonicity test (add random 3rd bit to unique 2bit case, check that 3bit is unique).
- [ ] **Step 2: Run verification script**
  Run: `python3 scripts/verify_reproduction_monotonicity.py`
  Expected: Both tests pass. Markdown reports written.
- [ ] **Step 3: Commit Task 8**
  Commit code and reports.

---

### Task 9: Full 2bit Sweep and Risk Map

**Files:**
- Create: `results/two_bit_risk_map.csv`, `reports/03_two_bit_risk_map.md`

- [ ] **Step 1: Run parallel sweep on selected 2bit cases**
  Run: `python3 scripts/parallel_runner.py --cases configs/selected_2bit_cases_round1.csv --type 2bit`
  Expected: Execution completes, logging detailed status, and producing `results/two_bit_risk_map.csv`.
- [ ] **Step 2: Generate 2bit risk map markdown report**
  Compile findings into `reports/03_two_bit_risk_map.md` showing unique/ambiguity counts per topology.
- [ ] **Step 3: Commit Task 9**
  Commit risk maps.

---

### Task 10: 3bit & 4bit Hard Case Selection and Run

**Files:**
- Create: `scripts/select_hard_cases.py`
- Create: `configs/selected_3bit_hard_cases.csv`, `configs/selected_4bit_hard_cases.csv`
- Create: `results/three_bit_hard_case_map.csv`, `reports/04_three_bit_hard_cases.md`
- Create: `results/four_bit_hard_case_map.csv`, `reports/05_four_bit_hard_cases.md`

- [ ] **Step 1: Write select_hard_cases.py**
  Select 3bit/4bit cases that do NOT contain any 2bit confirmed unique subsets. Ensure early-only combinations (like 4bit early-only) are included.
- [ ] **Step 2: Generate selections**
  Run: `python3 scripts/select_hard_cases.py`
  Expected: CSVs containing hard cases generated.
- [ ] **Step 3: Run hard cases sweep**
  Run: `python3 scripts/parallel_runner.py --cases configs/selected_3bit_hard_cases.csv --type 3bit`
  Run: `python3 scripts/parallel_runner.py --cases configs/selected_4bit_hard_cases.csv --type 4bit`
  Expected: Solver runs finish.
- [ ] **Step 4: Generate reports**
  Produce `reports/04_three_bit_hard_cases.md` and `reports/05_four_bit_hard_cases.md`.
- [ ] **Step 5: Commit Task 10**
  Commit all 3bit/4bit files.

---

### Task 11: Final Synthesis Report

**Files:**
- Create: `reports/FINAL_REPORT_7.md`

- [ ] **Step 1: Write FINAL_REPORT_7.md**
  Synthesize all phase 7 results, highlighting early vs. late leakage, early-only 4bit conclusions, monotonicity validation, and transition steps.
- [ ] **Step 2: Commit Task 11**
  Commit the final report.

---
