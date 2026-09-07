# MC Leakage-Channel Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether an anonymous randomized scan-out experiment can identify a repeatable pre-ARK MixColumns leakage slot without exposing the scan stitching map or exact MC coordinate.

**Architecture:** Reuse the existing AES concrete trace as an oracle-side generator, wrap one hidden MC FF plus AES-dependent and control decoys in a fixed-per-trial random scan permutation, and expose only schedule-tagged scan vectors to the analyzer. Rank slots from differential signatures and preserve ground truth in a separate evaluation artifact; export the selected anonymous slot and signatures for later key-recovery validation.

**Tech Stack:** Python 3, existing `aes_ref.py`, JSON/CSV artifacts, deterministic random generator, pytest. No Z3 in discovery; Z3 remains downstream for semantic-function refinement and key recovery.

## Global Constraints

- Do not expose scan stitching, FF instance names, physical location, exact MC coordinate, or secret key to the analyzer.
- Use one fixed scan permutation per trial and keep the same scan index across all queries and capture schedules.
- Use `P0` plus `16*4` coarse single-byte differentials with deltas `0x01,0x02,0x04,0x08`.
- Treat MC/ARK/round-register stage labels as generator-only ground truth.
- A discovery result is `PASS`, `FAIL`, or `UNRESOLVED`; score alone is never a proof of physical MC identity.
- Separate discovery artifacts from ground-truth evaluation artifacts.

---

### Task 1: Create discovery fixtures and generator

**Files:**
- Create: `scripts/scan_channel_generator.py`
- Create: `configs/discovery_config.yaml`
- Test: `tests/test_scan_channel_generator.py`

**Interfaces:**
- `coarse_plaintexts(base, deltas) -> list[bytes]`
- `build_trial(seed, config) -> (anonymous_observations, ground_truth)`
- `write_trial(...)` persists anonymous input and evaluator-only mapping separately.

- [ ] Write tests for 65 plaintext count, one-byte deltas, fixed per-trial scan ordering, and hidden-key exclusion from anonymous JSON.
- [ ] Run the generator tests and verify failure before implementation.
- [ ] Implement AES-trace-backed hidden sources: one pre-ARK MC bit, ARK/round-register alternatives, AES-dependent non-MC decoys, and constant/control decoys.
- [ ] Implement three capture schedules: `mc_capture`, `round_register_update`, and `post_update`.
- [ ] Apply a deterministic random permutation to scan slots once per trial.
- [ ] Persist anonymous scan vectors with plaintext id and schedule only; persist source labels and permutation only in ground truth.
- [ ] Run generator tests and a one-trial smoke generation.

### Task 2: Implement signature extraction and MC-aware scoring

**Files:**
- Create: `scripts/discover_mc_channel.py`
- Test: `tests/test_discover_mc_channel.py`

**Interfaces:**
- `differential_signatures(anonymous_trial) -> slot signatures`
- `score_slots(signatures, config) -> ranked candidate rows`
- `select_channel(ranked, ground_truth_optional) -> PASS/FAIL/UNRESOLVED summary`

- [ ] Write tests for differential signatures, inactive control rejection, schedule first-activity detection, and ShiftRows-aligned support sets.
- [ ] Run the tests and verify failure before implementation.
- [ ] Implement stable-slot checks across all coarse queries without using source metadata.
- [ ] Implement AES activity scoring using no-start/control comparisons and plaintext-dependent activity.
- [ ] Implement pre-round timing scoring: first activity at `mc_capture` is preferred; first activity only after register update is penalized/excluded.
- [ ] Implement MC support scoring against `C0..C3` and return top-10 rows without forcing a unique bit index.
- [ ] Implement PASS/FAIL/UNRESOLVED based on hidden ground truth only in the evaluator.
- [ ] Run unit tests and inspect a ranked smoke result.

### Task 3: Add refinement and held-out validation

**Files:**
- Modify: `scripts/scan_channel_generator.py`
- Modify: `scripts/discover_mc_channel.py`
- Create: `scripts/refine_mc_channel.py`
- Test: `tests/test_mc_channel_refinement.py`

**Interfaces:**
- `refinement_queries(top_slots, seed) -> plaintexts`
- `evaluate_refinement(candidate, held_out_trial) -> refinement metrics`
- `check_joint_superposition(response_a, response_b, response_ab) -> bool`

- [ ] Write tests for 8/16 deltas, held-out query separation, and joint-response XOR checks.
- [ ] Run the tests and verify failure before implementation.
- [ ] Add optional refinement for top-k only; do not scan or refine all slots with expensive logic.
- [ ] Add held-out random plaintexts and dual-source-byte joint changes.
- [ ] Record reproducibility, support agreement, and superposition consistency per candidate.
- [ ] Run refinement tests and a smoke refinement.

### Task 4: Export downstream key-recovery observation

**Files:**
- Create: `scripts/export_channel_observation.py`
- Test: `tests/test_channel_observation_export.py`

**Interfaces:**
- `export_observation(selected_slot, anonymous_trial, output_path)`
- Output schema contains anonymous `scan_slot`, schedule, `P0`, plaintexts, differential signatures, top-k semantic hypotheses, and no secret key.

- [ ] Write tests that reject exported secret keys and source instance labels.
- [ ] Implement an anonymous observation export compatible with a later fixed single-bit recovery adapter.
- [ ] Keep ground-truth semantic tap in a separate evaluation-only file.
- [ ] Run export tests and validate the JSON schema.

### Task 5: Run the validity campaign and report

**Files:**
- Create: `run_discovery_smoke.sh`
- Create: `run_discovery_campaign.sh`
- Create: `reports/MC_LEAKAGE_CHANNEL_DISCOVERY_REPORT.md`

- [ ] Run a positive-control smoke trial with one hidden MC FF and decoys.
- [ ] Run randomized trials with fixed-per-trial scan stitching.
- [ ] Measure total scan FFs, AES-dependent candidates, pre-round candidates, top-1/top-5/top-10 recall, selected-slot reproducibility, and held-out agreement.
- [ ] Classify each trial as PASS, FAIL, or UNRESOLVED using ground truth only after anonymous ranking.
- [ ] State clearly that PASS validates an experimental channel-discovery methodology under the synthetic scan wrapper; it does not prove RTL/physical mapping recovery.
- [ ] Run all focused tests, `py_compile`, and `git diff --check` before reporting.
