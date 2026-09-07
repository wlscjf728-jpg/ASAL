# Early-Only Adaptive Pair-Rescue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run pair-separator adaptive recovery on the 622 existing Phase 7/7_1 early-only 2/3-bit fixed-query ambiguity transcripts.

**Architecture:** A selector normalizes proof-grade source rows into immutable tasks preserving their original tap set, seed, and query budget. A new runner rebuilds each transcript, verifies `SAT -> SAT`, then iteratively generates and support-scores four pair separators before issuing one oracle query. It uses a global separator only when the pair is unseparable.

**Tech Stack:** Python 3, Z3, existing concrete AES oracle, `ProcessPoolExecutor`, YAML/CSV/JSON checkpoints.

## Global Constraints

- Use only source rows with all `SB_*`/`SR_*` taps and direct `SAT -> SAT`.
- Exclude `UNKNOWN`; never convert it into an ambiguity verdict.
- Preserve source depth, differential mode, key/query seed, and original query count.
- Use at most 32 spawned worker processes.
- Do not generate global separator candidates after a successful pair separator.
- Final recovery is only `SAT -> UNSAT`.

---

### Task 1: Normalize Early-Only Source Rows

**Files:**
- Create: `scripts/select_early_only_ambiguity_runs.py`
- Create: `configs/early_only_2_3bit_ambiguity_runs.csv`
- Test: `tests/test_early_only_adaptive_selector.py`

**Interfaces:**
- Produces CSV fields: `source_phase`, `tap_count`, `case_id`, `cand_a`, `cand_b`, `cand_c`, `seed`, `query_count`, `depth`, `mode`.
- Includes exactly direct `first_result=sat`, `second_result=sat` SB/SR-only rows.

- [ ] Write a failing selector test with one SB/SR `SAT -> SAT`, one mixed row, and one `UNKNOWN` row.
- [ ] Implement source loading for the four Phase 7/7_1 2/3-bit CSV files and reject rows outside the required model.
- [ ] Sort output by descending query count, then tap count, source phase, case ID, seed.
- [ ] Run the selector test and write the manifest from repository source results.

### Task 2: Add Multi-Candidate Pair Separator Scoring

**Files:**
- Modify: `scripts/adaptive_query_attack.py`
- Create: `scripts/early_only_pair_scoring.py`
- Test: `tests/test_early_only_pair_scoring.py`

**Interfaces:**
- `synthesize_for_candidate_pair(..., excluded_plaintexts: list[bytes]) -> dict`
- `rank_pair_plaintexts(points, key_a, key_b, taps, reference, depth, prior_active_bits) -> list[dict]`

- [ ] Write a failing test that verifies excluded separator plaintexts are not returned again.
- [ ] Extend pair synthesis with excluded plaintext constraints while retaining current past-observation exclusions.
- [ ] Implement full multi-tap, two-round concrete leakage signatures and key-bit flip influence over the differing bits of the pair.
- [ ] Rank by newly active differing bits, total active differing bits, influence balance, then deterministic plaintext order.
- [ ] Run scoring and synthesis tests.

### Task 3: Build the Early-Only Pair-Rescue Runner

**Files:**
- Create: `configs/early_only_pair_rescue.yaml`
- Create: `scripts/run_early_only_pair_rescue.py`
- Create: `run_early_only_pair_rescue.sh`
- Create: `start_early_only_pair_rescue.sh`
- Test: `tests/test_early_only_pair_rescue.py`

**Interfaces:**
- Consumes normalized manifest tasks.
- Produces per-task terminal JSON with source metadata, adaptive plaintexts, support scores, and exact solver verdict.

- [ ] Write tests for the reproduction gate, pair-only success path, and pair-UNSAT global fallback.
- [ ] Implement per-task q-preserving transcript reconstruction and fresh `SAT -> SAT` gate.
- [ ] Generate four pair separators, score them, query only the top candidate, and checkpoint after each accepted query.
- [ ] Invoke the global separator only on pair `UNSAT`; classify global `UNSAT` as proven non-recovery.
- [ ] Run dry-run to verify 622 selected tasks and 32-worker cap.

### Task 4: Validate and Launch

**Files:**
- Modify: `reports/` only if a campaign result report is requested after completion.

- [ ] Run selector, scorer, and runner unit tests.
- [ ] Run a one-task smoke recovery against a known 1-bit-style ambiguity fixture without writing into production result paths.
- [ ] Start the production campaign through the `setsid` launcher with 32 workers.
- [ ] Verify PID, queue size, checkpoint directory, and zero initial errors.
