# Phase-Alpha Behavioral Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate behavioral reacquisition of the existing MC9 anonymous scan channel under hidden scan-slot permutations without changing the MC9 experiment or invoking key recovery.

**Architecture:** Copy attack-side MC9 Phase 0 artifacts into an isolated phase-alpha directory. A pure Python runner parses the existing three-field scan capture, applies hidden old-slot-to-new-slot permutations, reacquires the selected channel using differential fingerprints, and emits an auditable JSON result. The tracker never reads evaluator key or scan mapping.

**Tech Stack:** Python 3 standard library, Bash, pytest for focused tests.

## Global Constraints

- Existing MC9 files are read-only for this experiment.
- The copied attack-side Phase 0 capture has 65 queries, 3 schedules, and 256 scan bits.
- Fingerprint schedule is `1`; initial probe IDs are `0..15`.
- Additional probes are selected sequentially from `16..62` until one candidate remains; `63,64` are held-out validation probes.
- Stable permutation is required only within one reacquisition probe bundle.
- No Z3, hidden key, evaluator scan map, VCS, or full key-recovery run is used.
- Stable scenarios require 100% evaluator-checked reacquisition accuracy.
- Independent permutation per probe query is a negative control and must not reacquire uniquely.

---

### Task 1: Freeze isolated inputs and configuration

**Files:**
- Create: `inputs/phase0_gate_scan_attack.txt`
- Create: `inputs/phase0_queries.txt`
- Create: `inputs/phase0_discovery.json`
- Create: `inputs/q128_gate_observations_attack.json`
- Create: `inputs/q129_gate_observations_attack.json`
- Create: `configs/phase_alpha.json`

**Interfaces:**
- Consumes: existing `extra_exp/results/phase_b` attack-side artifacts.
- Produces: immutable phase-alpha-local input paths and scenario parameters.

- [x] Copy the five attack-side artifacts without editing their contents.
- [x] Define `selected_slot=255`, `schedule=1`, `initial_probe_ids=[0..15]`,
  `candidate_probe_ids=[16..64]`, and refresh intervals `[65,16,8,4,1]`.
- [x] Define the independent-per-observation negative control.

### Task 2: Implement the fingerprint tracker

**Files:**
- Create: `scripts/phase_alpha_tracking.py`
- Test: `tests/test_phase_alpha_tracking.py`

**Interfaces:**
- `parse_capture(path) -> dict[(int, int), int]`
- `parse_queries(path) -> dict[int, str]`
- `fingerprint(rows, schedule, slot, query_ids) -> tuple[int, ...]`
- `run_experiment(config_path) -> dict`

- [x] Parse the existing `query schedule vector` format.
- [x] Implement old-to-new slot permutation without exposing the permutation to
  the tracker logic.
- [x] Implement initial matching and sequential collision refinement.
- [x] Implement stable epoch refresh scenarios and the independent-per-query
  negative control.
- [x] Test that identity permutation preserves slot 255, a stable permutation
  reacquires the hidden current slot, and independent probe permutations do not
  produce a unique match.

### Task 3: Run and audit the alpha experiment

**Files:**
- Create: `run_phase_alpha.sh`
- Create: `README.md`
- Create: `results/phase_alpha_tracking.json`
- Create: `logs/phase_alpha.out`

- [x] Run the isolated tracker with the copied inputs.
- [x] Verify all stable refresh intervals have 100% tracking accuracy.
- [x] Verify the negative control is not accepted as a tracking success.
- [x] Record that the output is a tracking result, not a key-recovery result.

### Task 4: Self-review

- [x] Confirm no alpha script imports or modifies the original MC9 directories.
- [x] Confirm no hidden key or evaluator scan mapping is copied into inputs.
- [x] Confirm result schema distinguishes stable PASS from expected negative failure.
- [x] Confirm the 16-probe collision and adaptive extra-probe count are visible.
