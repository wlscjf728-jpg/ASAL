# ASAL Key Diversity Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run an isolated 4-tap × 20-key AES-128 post-MC key-diversity validation using the existing oracle, Z3 model, fixed-query uniqueness test, and adaptive separator.

**Architecture:** Copy the `_8` AES/oracle/solver modules into a new experiment directory and add a thin campaign runner around them. The runner freezes four deterministic taps and twenty deterministic evaluator keys, strips the evaluator key before every solver call, writes checkpoint records atomically, and produces raw, summary, and report artifacts without modifying the source campaigns.

**Tech Stack:** Python 3, AES reference implementation, Z3, `concurrent.futures.ProcessPoolExecutor`, JSONL/CSV, shell/`setsid` for detached execution, pytest.

**Spec:** `docs/superpowers/specs/2026-09-03-key-diversity.md`

## Global Constraints

- Run exactly `4 taps × 20 new keys = 80` key/tap pairs.
- Keep one-bit post-MC semantic leakage and temporal depth `d=2`.
- Use one shared `P0` and one shared deterministic plaintext schedule for every key.
- Use the copied existing AES model, key schedule, Z3 formulation, solver options, and adaptive separator logic.
- Treat only `SAT -> UNSAT` as key uniqueness; `SAT -> SAT` is ambiguity and `UNKNOWN` is unresolved.
- Never pass `true_key_hex` into the solver document.
- Do not modify `_8`, `_7`, `_7_1`, `extra_exp`, or any currently running MC9 artifacts.
- Use `workers: 32` for the detached campaign.

---

### Task 1: Freeze the isolated experiment inputs

**Files:**
- Create: `anonymous_subround_multiround_attack_key_diversity/docs/superpowers/specs/2026-09-03-key-diversity.md`
- Create: `anonymous_subround_multiround_attack_key_diversity/configs/key_diversity.yaml`
- Create: `anonymous_subround_multiround_attack_key_diversity/configs/representative_post_mc_taps.csv`
- Create: `anonymous_subround_multiround_attack_key_diversity/inputs/evaluator_keys.csv`
- Create: `anonymous_subround_multiround_attack_key_diversity/reference/source_manifest.json`
- Copy: `anonymous_subround_multiround_attack_8_oracle/reference/candidate_map_extended512.csv` to `reference/candidate_map_extended512.csv`

**Interfaces:**
- Produces four tap records with `tap_id`, semantic position, byte, column, row, and bit.
- Produces twenty unique key records with `key_id`, `key_hex`, and SHA-256 digest.
- Produces a manifest identifying every copied source file and the unavailable all-128 `N_uniq` artifact.

- [ ] **Step 1: Write input validation tests**

```python
def test_inputs_are_four_taps_and_twenty_new_keys():
    taps = load_taps(ROOT / "configs/representative_post_mc_taps.csv")
    keys = load_keys(ROOT / "inputs/evaluator_keys.csv")
    assert len(taps) == 4
    assert len(keys) == 20
    assert len({row["tap_id"] for row in taps}) == 4
    assert len({row["key_hex"] for row in keys}) == 20
```

- [ ] **Step 2: Run the test and verify it fails before the loader exists**

Run: `pytest -q tests/test_key_diversity_campaign.py -k inputs`

Expected: collection or import failure because the new loader is not implemented yet.

- [ ] **Step 3: Copy the reference candidate map and existing solver dependencies**

Run: `cp ../anonymous_subround_multiround_attack_8_oracle/reference/candidate_map_extended512.csv reference/candidate_map_extended512.csv` and copy `aes_ref.py`, `z3_aes.py`, `oracle.py`, `adaptive_query_attack.py`, `solve_known_mapping.py`, and `late1bit_scoring.py` into `scripts/`.

- [ ] **Step 4: Implement deterministic tap/key generation and validation**

Use MC bit ranks `0, 42, 85, 127` from the copied 128-entry MC map. Generate key `i` as the first 16 bytes of `SHA-256("asal-key-diversity-{generation_seed}-{i}")`, reject the three existing `key_for_seed(0..2)` values and duplicates, and write the resulting CSV.

- [ ] **Step 5: Run input tests**

Run: `pytest -q tests/test_key_diversity_campaign.py -k inputs`

Expected: PASS, including four MC taps, four distinct columns, twenty unique keys, and no overlap with the original three keys.

### Task 2: Implement the attack-side boundary and checkpoint writer

**Files:**
- Create: `scripts/key_diversity_common.py`
- Create: `scripts/key_diversity_campaign.py`
- Create: `results/checkpoints.jsonl`
- Test: `tests/test_key_diversity_campaign.py`

**Interfaces:**
- `sanitize_for_solver(doc: dict) -> dict` removes `evaluator.true_key_hex` recursively from the solver input.
- `run_fixed_checkpoints(key_bytes: bytes, tap: dict, config: dict) -> dict` returns checkpoint history and fixed status.
- `run_one_case(task: dict) -> dict` returns one terminal result with fixed/adaptive classification.
- `append_checkpoint(path: Path, row: dict) -> None` appends one JSON object and flushes it.

- [ ] **Step 1: Write failing sanitization and classification tests**

```python
def test_solver_payload_has_no_secret_key():
    doc = {"evaluator": {"true_key_hex": "00" * 16}, "observations": []}
    clean = sanitize_for_solver(doc)
    assert "true_key_hex" not in json.dumps(clean)

def test_only_sat_to_unsat_is_unique():
    assert classify_pair("sat", "unsat") == "unique"
    assert classify_pair("sat", "sat") == "ambiguity"
    assert classify_pair("sat", "unknown") == "unresolved"
```

- [ ] **Step 2: Run the focused tests to verify failure**

Run: `pytest -q tests/test_key_diversity_campaign.py -k "sanitize or unique"`

Expected: FAIL because the boundary helpers do not yet exist.

- [ ] **Step 3: Implement the sanitized solver boundary and atomic checkpoint append**

Build oracle documents with the copied `generate_observation`, deep-copy them, remove only evaluator secret fields before calling `solver_result`, retain the evaluator key in the worker process for post-solve correctness checks, and write a checkpoint after each solve pair.

- [ ] **Step 4: Implement fixed-query ladder**

Use the same fixed query list for every key/tap pair, with checkpoints `[32, 64, 96, 128, 192, 255]` and a zero plaintext reference. At each checkpoint run first and second solves, record statuses/runtimes/model, stop at `SAT -> UNSAT`, and continue ambiguity to the last checkpoint.

- [ ] **Step 5: Run focused boundary tests**

Run: `pytest -q tests/test_key_diversity_campaign.py -k "sanitize or unique or checkpoint"`

Expected: PASS.

### Task 3: Reuse the adaptive separator without changing its semantics

**Files:**
- Modify: `scripts/key_diversity_campaign.py`
- Test: `tests/test_key_diversity_campaign.py`

**Interfaces:**
- `run_adaptive(key_bytes: bytes, tap: dict, plaintexts: list[bytes], config: dict) -> dict` returns adaptive history and a terminal status.
- Existing copied `synthesize_for_candidate_pair` and global separator are the only separator generators used.

- [ ] **Step 1: Write failing adaptive loop tests with stubbed solver/oracle**

```python
def test_adaptive_appends_separator_until_second_solve_unsat(monkeypatch):
    statuses = [("sat", "sat"), ("sat", "unsat")]
    result = run_adaptive_with_stubs(statuses)
    assert result["final_classification"] == "ADAPTIVE_UNIQUE"
    assert result["adaptive_queries"] == 1
```

- [ ] **Step 2: Run the test and verify failure**

Run: `pytest -q tests/test_key_diversity_campaign.py -k adaptive`

Expected: FAIL because the adaptive loop is not implemented.

- [ ] **Step 3: Implement the existing pair-first/global-fallback loop**

Start from the last fixed ambiguous transcript. Obtain candidate models from the copied solver, synthesize a separator for a candidate pair, fall back to the copied global separator when the pair is already equivalent, query the evaluator with that plaintext, append the observed leakage, and rerun first/second solves. An UNSAT separator search is `PROVEN_NON_RECOVERY`; `UNKNOWN` is `UNKNOWN`; no time limit is imposed by the experiment config.

- [ ] **Step 4: Run adaptive unit tests**

Run: `pytest -q tests/test_key_diversity_campaign.py -k adaptive`

Expected: PASS.

### Task 4: Add campaign scheduling, summary, and report generation

**Files:**
- Create: `configs/key_diversity.yaml`
- Create: `scripts/summarize_results.py`
- Create: `run_key_diversity.sh`
- Create: `README.md`
- Test: `tests/test_key_diversity_campaign.py`

**Interfaces:**
- `build_tasks() -> list[dict]` returns exactly 80 tasks.
- `summarize(raw_path: Path) -> dict` returns fixed/adaptive/unresolved counts and per-tap statistics.
- `write_report(summary: dict, output: Path) -> None` writes the bounded-claim markdown report.

- [ ] **Step 1: Write failing task-count and summary tests**

```python
def test_campaign_has_exactly_eighty_tasks():
    assert len(build_tasks()) == 80

def test_summary_separates_fixed_and_adaptive_unique():
    summary = summarize_fixture()
    assert summary["counts"]["FIXED_UNIQUE"] == 1
    assert summary["counts"]["ADAPTIVE_UNIQUE"] == 1
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `pytest -q tests/test_key_diversity_campaign.py -k "tasks or summary"`

Expected: FAIL because scheduling and summary functions are absent.

- [ ] **Step 3: Implement deterministic 32-worker scheduling and result persistence**

Use `ProcessPoolExecutor(max_workers=32)`, deterministic task order, one terminal JSONL record per pair, and a resume check keyed by `key_id/tap_id` so a detached process can be restarted without duplicating completed runs.

- [ ] **Step 4: Implement summary/report generation**

Count the terminal classifications, report `N_uniq` median/range for fixed successes, adaptive query counts, solver unresolved counts, and the structural tap-selection limitation. Never infer success from evaluator key equality alone.

- [ ] **Step 5: Run all unit tests**

Run: `pytest -q tests/test_key_diversity_campaign.py`

Expected: PASS.

### Task 5: Regression, smoke test, and detached 80-run execution

**Files:**
- Create: `logs/campaign.out`
- Create: `logs/campaign.pid`
- Create: `results/raw_runs.jsonl`
- Create: `results/summary.json`
- Create: `reports/KEY_DIVERSITY_VALIDATION_REPORT.md`

- [ ] **Step 1: Run static/input regression**

Run: `pytest -q tests/test_key_diversity_campaign.py` and `python scripts/key_diversity_campaign.py --dry-run`.

Expected: all tests pass; dry-run prints four taps, twenty keys, and 80 tasks without invoking Z3.

- [ ] **Step 2: Run one real isolated smoke case**

Run: `python scripts/key_diversity_campaign.py --limit 1 --workers 1`.

Expected: one result has a valid first/second status, the serialized solver input contains no evaluator key, and the original `_8` result files are unchanged.

- [ ] **Step 3: Launch the complete campaign detached**

Run: `setsid bash run_key_diversity.sh > logs/campaign.out 2>&1 < /dev/null & echo $! > logs/campaign.pid`.

Expected: the PID remains alive while work is pending and `results/checkpoints.jsonl` grows as cases finish.

- [ ] **Step 4: Verify completion**

Run: `python scripts/summarize_results.py --verify-complete`.

Expected: exactly 80 terminal records, zero duplicate `(key_id,tap_id)` pairs, and a generated summary/report. Any `UNKNOWN` or inconsistency is reported, never silently converted.

- [ ] **Step 5: Preserve evidence and report bounded conclusion**

Run: `git diff --check -- anonymous_subround_multiround_attack_key_diversity` and inspect the summary/report.

Expected: only the new directory is changed; the report states whether the original three-key claim appears key-generalized over the tested 20 new keys and explicitly describes any residual unresolved cases.
