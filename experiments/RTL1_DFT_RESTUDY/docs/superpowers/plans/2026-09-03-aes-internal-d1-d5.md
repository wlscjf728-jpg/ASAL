# AES-Internal D1-D5 Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute an AES-internal-only D1-D5 DFT campaign that compares IARK/SB/SR/MC, AES non-stage random, host random control, and automatic AES candidate selection under an identical 1,024-FF scan budget, while excluding direct variable-FF faults from every case.

**Architecture:** Start from the existing one-round `mor1kx_aes_soc` pre-DFT checkpoint and create a new host-only 896-FF common scan set so that AES non-stage registers remain available as a random candidate pool. Generate one common AES-internal raw fault universe and one independently collapsed AES-internal universe, run the same DFT/TetraMAX flow for every case, and analyze direct-excluded residual detection by AES structural region. Existing `RTL1` and `RTL1_DFT_RESTUDY` outputs remain read-only inputs and are never overwritten.

**Tech Stack:** Python 3, POSIX `sh`, Synopsys Design Compiler S-2021.06-SP4, Synopsys TetraMAX Q-2019.12-SP5-5, Verilog netlist parsing, CSV/JSON reports, SVG figures, pytest.

**Spec:** `AES_INTERNAL_D1_D5_EXPERIMENT_DESIGN.md`

## Global Constraints

- Functional checkpoint: one-round `mor1kx_aes_soc`; no RTL or synthesis change between cases.
- New common scan set: 896 host-side scan-eligible FFs; variable set: 128 FFs; total: 1,024 FFs; one chain of length 1,024.
- Primary cases: `CASE_IARK`, `CASE_SB`, `CASE_SR`, `CASE_MC`, ten `CASE_RANDOM_AES_seedNN`, and `CASE_AUTO_AES`.
- Secondary control: ten `CASE_RANDOM_HOST_seedNN` cases using host FFs outside the new common set.
- Fault scope: AES hierarchy combinational faults only; exclude `aes_result_o`, `aes_done_o`, host/interface faults, scan-only faults, and all variable-candidate Q/QN direct faults.
- The same direct-exclusion union and the same fault source are loaded for every case.
- Run stuck-at and transition ATPG with identical options per fault model; record DRC/protocol warnings as status, never as silent success or zero coverage.
- Existing files under `../RTL`, `../RTL1`, and current `results/tmax` namespaces are not modified.
- No git operations are part of this implementation; every generated file is reproducible from the new scripts and manifests.

---

## File Map

**Create:**

- `tests/test_aes_internal_campaign.py` - unit tests for candidate partitioning, fault filtering, direct exclusion, cone boundaries, and summary classification.
- `scripts/aes_internal_prepare.py` - parse checkpoint/inventory and build all new scan candidate manifests and experiment manifest.
- `scripts/aes_internal_faults.py` - build AES-internal raw/stuck/transition sources and the fixed collapsed representative source.
- `scripts/aes_internal_cones.py` - sequential-boundary-aware region metadata and site classification.
- `scripts/aes_internal_rank.py` - deterministic topology ranking and AUTO_AES manifest generation.
- `scripts/dc/run_aes_internal_case.tcl` - DFT insertion from the shared checkpoint for one case.
- `scripts/run_aes_internal_dft.sh` - bounded case scheduler for all DFT cases.
- `scripts/tmax/run_aes_internal_case.tcl` - one-case stuck/transition ATPG driver for raw or collapsed source.
- `scripts/run_aes_internal_tmax.sh` - bounded TetraMAX scheduler with separate result namespaces.
- `scripts/analyze_aes_internal.py` - aggregate summaries, region tables, status transitions, D5 output, and figures.
- `scripts/verify_aes_internal.py` - final invariant and result-integrity verifier.
- `reports/AES_INTERNAL_D1_D5_REPORT.md` - final experiment report generated from raw outputs.
- `reports/AES_INTERNAL_COVERAGE_COMPARISON.svg` - raw/collapsed stage comparison figure.
- `reports/AES_INTERNAL_REGION_BREAKDOWN.svg` - region-level MC/random comparison figure.
- `reports/AES_INTERNAL_SECURITY_TESTABILITY_OVERLAY.svg` - D5 security/testability overlay with provenance labels.

**Modify only within the new campaign namespace:**

- `scripts/analysis/analysis_utils.py` - add small pure helpers only if the new tests require them; preserve existing callers.

**Generate under the new campaign namespace:**

- `config/common_scan_aes_internal.list`
- `config/iark_scan_aes_internal.list`, `sb_scan_aes_internal.list`, `sr_scan_aes_internal.list`, `mc_scan_aes_internal.list`
- `config/random_aes_seed01.list` through `random_aes_seed10.list`
- `config/random_host_seed01.list` through `random_host_seed10.list`
- `config/auto_aes_scan.list`
- `config/aes_internal_candidate_manifest.csv`
- `config/aes_internal_experiment_manifest.json`
- `config/aes_internal_raw_stuck.list`, `aes_internal_raw_transition.list`, `aes_internal_collapsed_stuck.list`
- `config/aes_internal_direct_exclusion_stuck.list`, `aes_internal_direct_exclusion_transition.list`
- `results/dft/aes_internal/<case>/`
- `results/tmax/aes_internal_raw_stuck/<case>/`
- `results/tmax/aes_internal_raw_transition/<case>/`
- `results/tmax/aes_internal_collapsed_stuck/<case>/`
- `results/analysis/aes_internal_*.csv`

---

### Task 1: Add failing tests for candidate and fault-domain invariants

**Files:**
- Create: `tests/test_aes_internal_campaign.py`
- Modify: `scripts/analysis/analysis_utils.py` only if a pure helper is needed after the RED run.

**Interfaces:**
- `partition_candidate_cells(inventory, common, stage_sets) -> dict[str, set[str]]`
- `filter_fault_line(line, allowed_prefixes, excluded_sites) -> str | None`
- `build_direct_exclusion_lines(sites, kind) -> list[str]`
- `classify_aes_region(site, metadata) -> str`
- `classify_atpg_state(code) -> str`

- [ ] **Step 1: Write tests for the candidate partition.**

```python
def test_candidate_partition_keeps_stage_banks_disjoint_from_common():
    inventory = {"a_stage[0]", "a_key[0]", "h0", "h1"}
    common = {"h0", "a_key[0]"}
    stages = {"MC": {"a_stage[0]"}}
    result = partition_candidate_cells(inventory, common, stages)
    assert result["MC"] == {"a_stage[0]"}
    assert result["AES_NON_STAGE"] == set()
    assert result["COMMON"] == common
```

- [ ] **Step 2: Add tests proving interface and host faults are filtered.**

```python
def test_aes_fault_filter_excludes_interface_and_host():
    assert filter_fault_line("sa0 NC \\u_aes_peripheral/U1/Z", {"u_aes_peripheral/"}, set()) is not None
    assert filter_fault_line("sa0 NC aes_result_o[0]", {"u_aes_peripheral/"}, set()) is None
    assert filter_fault_line("sa0 NC iwb_adr_o[0]", {"u_aes_peripheral/"}, set()) is None
```

- [ ] **Step 3: Add tests for direct exclusion and cone boundaries.**

```python
def test_direct_exclusion_emits_nc_both_polarities():
    assert build_direct_exclusion_lines({"n0"}, "stuck") == ["sa0 NC n0", "sa1 NC n0"]

def test_region_classifier_does_not_follow_clock_or_reset():
    metadata = {"mc_cone_sites": {"aes/U1/Z"}, "clock_sites": {"clk"}, "reset_sites": {"rst"}}
    assert classify_aes_region("aes/U1/Z", metadata) == "MC_CONE"
    assert classify_aes_region("clk", metadata) == "UNRESOLVED"
```

- [ ] **Step 4: Add tests for TetraMAX status normalization and invalid class sums.**

```python
def test_atpg_state_normalization():
    assert classify_atpg_state("DS") == "DT"
    assert classify_atpg_state("AU") == "AU"
    assert classify_atpg_state("--") == "EQUIVALENT"
```

- [ ] **Step 5: Run the focused tests and confirm the new tests fail for missing interfaces.**

Run: `pytest -q tests/test_aes_internal_campaign.py`
Expected: FAIL with missing helper imports or missing implementations. Do not edit production scripts before observing the RED result.

---

### Task 2: Implement checkpoint parsing and AES-internal candidate manifests

**Files:**
- Create: `scripts/aes_internal_prepare.py`
- Test: `tests/test_aes_internal_campaign.py`
- Generate: `config/common_scan_aes_internal.list`, all candidate manifests, `config/aes_internal_candidate_manifest.csv`, `config/aes_internal_experiment_manifest.json`

**Interfaces:**
- `load_register_inventory(path: Path) -> set[str]`
- `parse_netlist_instances(path: Path) -> tuple[dict, dict, dict]`
- `select_host_common(inventory: set[str], old_common: set[str], forbidden: set[str], count: int) -> list[str]`
- `select_seeded_pool(pool: set[str], count: int, seed: int) -> list[str]`
- `build_candidate_manifests(root: Path) -> dict[str, list[str]]`
- CLI: `python3 scripts/aes_internal_prepare.py`

- [ ] **Step 1: Implement only the parser and deterministic partition helpers.**

Use the existing checkpoint at `results/checkpoint/mor1kx_aes_soc_pre_dft.v` and inventory at `results/checkpoint/register_inventory.rpt`. Preserve escaped hierarchy names exactly as they appear in fault sources and scan manifests. Treat `IARK_REG`, `SB_REG`, `SR_REG`, and `MC_REG` as four disjoint 128-cell stage sets.

- [ ] **Step 2: Build the new host-only common set.**

Keep old common host FFs first; fill to exactly 896 from host scan-eligible FFs in stable lexical order while excluding all AES FFs, all stage banks, and all future random-host candidates. Abort with a clear error if fewer than 896 eligible host cells remain.

- [ ] **Step 3: Build AES random and host random seeds.**

Use the 260 AES non-stage cells (`key_reg`, `plaintext_reg`, and four valid/done cells) as the AES random pool. Generate ten deterministic 128-cell seed subsets. Generate ten 128-cell host subsets from host cells outside the new common set. Save every selected instance name, seed, source pool, and rank order in the candidate CSV.

- [ ] **Step 4: Build `CASE_AUTO_AES` candidate input.**

The automatic candidate universe is all 772 AES FFs, including stage and non-stage groups. Do not use ATPG results or secret data. The later ranking task consumes this complete candidate list.

- [ ] **Step 5: Write the experiment manifest and assert invariants.**

Record checkpoint SHA256, all candidate counts, common count 896, variable count 128, total scan count 1,024, chain count 1, and the exact seed derivation. Assert no variable manifest intersects the new common set and each stage manifest has exactly 128 cells.

- [ ] **Step 6: Run tests and preparation.**

Run: `pytest -q tests/test_aes_internal_campaign.py`
Run: `python3 scripts/aes_internal_prepare.py`
Expected: all tests pass; common count is 896; AES non-stage pool is 260; each stage and random manifest has 128 entries; manifest is written.

---

### Task 3: Build AES-internal raw, transition, and collapsed fault sources

**Files:**
- Create: `scripts/aes_internal_faults.py`
- Test: `tests/test_aes_internal_campaign.py`
- Generate: all AES-internal fault lists and direct-exclusion lists

**Interfaces:**
- `is_aes_internal_site(site: str) -> bool`
- `is_interface_site(site: str) -> bool`
- `is_direct_variable_site(site: str, direct_sites: set[str]) -> bool`
- `build_raw_sources(raw_fault_path: Path, output_dir: Path, direct_sites: set[str]) -> dict[str, int]`
- `build_collapsed_source(reference_fault_report: Path, output_path: Path, allowed_sites: set[str]) -> int`
- CLI: `python3 scripts/aes_internal_faults.py`

- [ ] **Step 1: Extend the tests for exact scope rules.**

Test that `u_aes_peripheral/...` combinational sites are kept, `aes_result_o` and `aes_done_o` are removed, host paths are removed, and every selected Q/QN site is removed. Test that direct lists contain `sa0 NC`, `sa1 NC`, `str NC`, and `stf NC` lines exactly once per site/polarity.

- [ ] **Step 2: Implement raw stuck-at filtering.**

Read `config/canonical_faults_all.list` from the copied checkpoint, retain only valid `sa0/sa1` lines whose site is under AES hierarchy and is not an interface/direct site, and normalize to `sa{0,1} NC <site>`. Do not use fault status lines as source input. Write the accepted count and rejected-count breakdown to JSON.

- [ ] **Step 3: Implement transition source generation.**

Use exactly the same accepted AES site set and emit `str NC <site>` and `stf NC <site>`. The site set and direct exclusions must be identical to the stuck-at source after polarity expansion.

- [ ] **Step 4: Implement AES-internal collapsed source generation.**

Run a reference TetraMAX model/fault-collapse step on the functional checkpoint, then filter collapsed representatives to the same AES-internal allowed site domain before direct exclusion. Never reuse `historical_canonical_faults_422.list`; record the collapse command, reference digest, and representative count in the manifest.

- [ ] **Step 5: Validate source counts and direct exclusion.**

Run: `python3 scripts/aes_internal_faults.py`
Expected: raw stuck and transition sources have identical site sets; all direct candidates are absent; no host/interface site is present; collapsed source is non-empty or the run stops as `UNRESOLVED` with the exact collapse failure.

---

### Task 4: Implement sequential-boundary-aware AES region attribution

**Files:**
- Create: `scripts/aes_internal_cones.py`
- Modify: `scripts/analysis/analysis_utils.py` only for shared pure helpers
- Test: `tests/test_aes_internal_campaign.py`
- Generate: `config/aes_internal_region_metadata.json`

**Interfaces:**
- `build_netlist_graph(verilog_path: Path) -> tuple[dict, dict, dict]`
- `backward_cone_until_sequential(graph, target_nets: set[str]) -> set[str]`
- `build_region_metadata(checkpoint: Path, stage_manifests: dict) -> dict[str, list[str]]`
- `classify_aes_region(site: str, metadata: dict[str, set[str]]) -> str`
- CLI: `python3 scripts/aes_internal_cones.py`

- [ ] **Step 1: Implement parser tests for sequential boundaries.**

Use a small synthetic netlist fixture in the test to prove traversal stops at FF Q/QN and does not traverse CP, CD, reset, or scan enable as data inputs.

- [ ] **Step 2: Implement hierarchy-preserving graph extraction.**

Preserve full escaped instance/net names. Build driver and consumer edges only for combinational data pins. Mark sequential cells by cell type and never enqueue their clock/control pins.

- [ ] **Step 3: Build disjoint regions.**

Trace IARK/SB/SR/MC D cones, then assign overlaps to `SHARED_OR_OVERLAP`. Assign remaining AES combinational sites to `AES_OTHER`, AES control sites to `AES_CONTROL`, and unclassified sites to `UNRESOLVED`. Direct/interface sites are excluded before region assignment.

- [ ] **Step 4: Write metadata and validate disjointness.**

Run: `python3 scripts/aes_internal_cones.py`
Expected: no direct or host/interface site appears in the allowed region sets; every allowed site is either assigned once or listed as unresolved/overlap.

---

### Task 5: Add DFT insertion for the new scan manifests

**Files:**
- Create: `scripts/dc/run_aes_internal_case.tcl`
- Create: `scripts/run_aes_internal_dft.sh`
- Generate: `results/dft/aes_internal/<case>/`

**Interfaces:**
- TCL environment: `RTL_ROOT`, `CASE_NAME`, `VARIABLE_MANIFEST`
- Shell CLI: `CASE_NAMESPACE=aes_internal sh scripts/run_aes_internal_dft.sh`

- [ ] **Step 1: Write the DFT TCL case driver.**

Read the same pre-DFT DDC and Verilog checkpoint for every case, read `common_scan_aes_internal.list` plus the case-specific variable list, insert exactly 1,024 scan cells in one chain, and write post-DFT DDC/Verilog/SPF/SDC and scan inventory under the case directory.

- [ ] **Step 2: Add DFT preflight assertions.**

Parse the scan inventory and path report after each run. Abort the scheduler case if scan count is not 1,024, chain count is not 1, chain length is not 1,024, or DRC output is missing.

- [ ] **Step 3: Implement bounded scheduling.**

Run all stage, random AES, random host, and AUTO_AES cases in per-case directories with at most two concurrent `dc_shell` processes. Write a completion marker only after every expected case has valid DFT outputs.

- [ ] **Step 4: Run the DFT campaign and audit.**

Run: `sh scripts/run_aes_internal_dft.sh`
Expected: every case uses the same checkpoint digest and has exactly 1,024 scan cells and one 1,024-cell chain.

---

### Task 6: Add TetraMAX raw and collapsed ATPG runners

**Files:**
- Create: `scripts/tmax/run_aes_internal_case.tcl`
- Create: `scripts/run_aes_internal_tmax.sh`
- Generate: `results/tmax/aes_internal_*/*`

**Interfaces:**
- TCL environment: `RTL_ROOT`, `CASE_NAME`, `FAULT_MODE`, `FAULT_UNIVERSE`
- Shell CLI: `FAULT_UNIVERSE=aes_internal_raw FAULT_MODE=stuck sh scripts/run_aes_internal_tmax.sh`

- [ ] **Step 1: Implement raw stuck-at runner.**

Read the case post-DFT netlist and SPF, run DRC, set stuck model, read the same AES-internal raw source, delete the same direct-exclusion list, run identical ATPG options, and write summary, fault summary, detailed uncollapsed report, and complete log.

- [ ] **Step 2: Implement raw transition runner.**

Use the same case netlists and transition source, configure launch/capture timing consistently, run DRC and transition ATPG, and preserve all V14/S19/C26/protocol warnings in the log and metadata.

- [ ] **Step 3: Implement collapsed stuck-at runner.**

Read the independently generated AES-internal collapsed source with the same direct-exclusion policy. Store the result in a separate namespace so it cannot be confused with raw results.

- [ ] **Step 4: Implement scheduler and terminal markers.**

Run primary cases with bounded parallelism, wait for every child, and create a mode marker only when every expected summary and detailed report exists. A TetraMAX process error, missing summary, invalid source warning, or class-sum mismatch remains `UNRESOLVED`/`INVALID`.

- [ ] **Step 5: Run all ATPG modes.**

Run:

```sh
FAULT_UNIVERSE=aes_internal_raw FAULT_MODE=stuck sh scripts/run_aes_internal_tmax.sh
FAULT_UNIVERSE=aes_internal_raw FAULT_MODE=transition sh scripts/run_aes_internal_tmax.sh
FAULT_UNIVERSE=aes_internal_collapsed FAULT_MODE=stuck sh scripts/run_aes_internal_tmax.sh
```

Expected: identical loaded fault total and direct deletion count across cases within each universe/mode; no result is inferred from a missing summary.

---

### Task 7: Implement D5 topology ranking and security overlay inputs

**Files:**
- Create: `scripts/aes_internal_rank.py`
- Test: `tests/test_aes_internal_campaign.py`
- Generate: `config/auto_aes_scan.list`, `results/analysis/auto_aes_topology_ranking.csv`

**Interfaces:**
- `rank_aes_candidates(graph, candidates) -> list[dict[str, object]]`
- `write_auto_manifest(ranking, count=128, path=Path) -> None`

- [ ] **Step 1: Test ranking independence.**

Provide two candidate graphs with identical structure but different fake ATPG labels and assert that rankings are identical. Assert the ranking does not receive key or historical security data.

- [ ] **Step 2: Implement structural ranking.**

Use only forward fanout nodes/nets, AES endpoint reachability, all endpoint reachability, and fanin depth. Freeze the score coefficients in the manifest. Rank all 772 AES eligible FFs, including stage banks, and save the top 128.

- [ ] **Step 3: Generate provenance-labeled security overlay input.**

Join current DFT coverage to the existing security metric only as a historical/proxy overlay. Mark the source as `historical_overlay` and never treat it as a new cryptographic measurement.

- [ ] **Step 4: Run ranking tests and generation.**

Run: `pytest -q tests/test_aes_internal_campaign.py -k ranking`
Run: `python3 scripts/aes_internal_rank.py`
Expected: exactly 128 auto candidates, deterministic output, no ATPG/key input dependency.

---

### Task 8: Implement raw/collapsed/region analysis and report generation

**Files:**
- Create: `scripts/analyze_aes_internal.py`
- Test: `tests/test_aes_internal_campaign.py`
- Generate: analysis CSVs, SVG figures, `reports/AES_INTERNAL_D1_D5_REPORT.md`

**Interfaces:**
- `parse_tmax_summary(path: Path) -> dict[str, object]`
- `load_case_results(root: Path) -> list[dict[str, object]]`
- `aggregate_region_status(detail_paths, metadata) -> list[dict[str, object]]`
- `compute_random_statistics(rows, placement="RANDOM_AES") -> dict[str, float]`
- `draw_coverage_comparison(rows, path: Path) -> None`
- CLI: `python3 scripts/analyze_aes_internal.py`

- [ ] **Step 1: Add parser tests for every result class.**

Test summary parsing, `DT/PT/AU/UD/ND` normalization, missing CPU fields, missing detail reports, and `class_sum != total` invalidation.

- [ ] **Step 2: Aggregate fairness data.**

For every case record checkpoint digest, scan count, chain count/length, loaded fault count, direct exclusion count, ATPG options hash, DRC status, summary status, and detail row count.

- [ ] **Step 3: Aggregate D1/D2 metrics.**

For raw and collapsed universes separately, compute detected, possibly detected, AU, UD, ND, total, coverage, patterns, runtime, random AES mean/median/std/min/max, and MC-minus-random deltas. Keep random host outside the primary random AES statistics.

- [ ] **Step 4: Aggregate D3 regions and status transitions.**

Produce per-case/per-region totals and detected counts. Produce pairwise transitions such as `RANDOM: AU/ND -> MC: DT` while keeping `SHARED_OR_OVERLAP` and `UNRESOLVED` explicit.

- [ ] **Step 5: Generate figures.**

Generate a raw-versus-collapsed coverage comparison, an AES region breakdown, and a security/testability overlay. Figures must include direct-exclusion and historical-proxy labels where applicable.

- [ ] **Step 6: Generate the report.**

The report must state the actual fault counts and warnings, reproduce the 422 control as context only, distinguish direct-included historical results from direct-excluded AES-internal results, and select one of the specified interpretation classes without hard-coding an expected outcome.

- [ ] **Step 7: Run analysis.**

Run: `python3 scripts/analyze_aes_internal.py`
Expected: all available valid cases are summarized; missing/invalid cases are marked and never counted as coverage zero or success.

---

### Task 9: Add final integrity verifier and execute the full campaign

**Files:**
- Create: `scripts/verify_aes_internal.py`
- Modify: `reports/AES_INTERNAL_D1_D5_REPORT.md` only through the generator, not manual result edits.

**Interfaces:**
- CLI: `python3 scripts/verify_aes_internal.py`
- Exit code 0 only when every required invariant is proven.

- [ ] **Step 1: Verify candidate manifests.**

Check stage sizes, random sizes, common size 896, total per-case scan budget 1,024, no common/variable intersections, and deterministic seed manifests.

- [ ] **Step 2: Verify fault sources.**

Check raw/collapsed source presence, AES-only path membership, interface/host exclusion, direct exclusion, equal site sets between stuck and transition, and equal loaded/deleted counts across cases.

- [ ] **Step 3: Verify DFT and ATPG outputs.**

Check every expected case has post-DFT netlist, SPF, scan inventory, summary, and detailed report. Check all DFT fairness fields and ATPG class sums. Check no invalid fault syntax appears in final logs.

- [ ] **Step 4: Verify D3/D5 outputs.**

Check region disjointness, direct region zero, auto manifest count 128, topology ranking determinism, report existence, and figure existence.

- [ ] **Step 5: Execute the verifier and tests.**

Run:

```sh
pytest -q tests/test_aes_internal_campaign.py
python3 scripts/verify_aes_internal.py
```

Expected: all tests pass and the verifier exits 0. Any failure is fixed in the implementation or reported as `UNRESOLVED`/`INVALID`; no result is manually altered.

---

## Execution Order and Checkpoints

1. Tasks 1-3: candidate and fault-source construction. Checkpoint: manifests and source lists pass unit tests.
2. Task 4: cone metadata. Checkpoint: regions are sequential-boundary-aware and disjoint.
3. Task 5: DFT insertion. Checkpoint: all case scan inventories show 1,024/1/1,024.
4. Task 6: ATPG. Checkpoint: raw/collapsed summaries and logs exist for every expected case.
5. Tasks 7-8: D5 and analysis. Checkpoint: CSVs, figures, and report are generated from results only.
6. Task 9: final verification. Checkpoint: exit code 0 and no unresolved invariant.

## Final Interpretation Rules

- If AES-internal raw direct-excluded MC gain survives random seed variation and is region-localized, report residual AES-internal testability support.
- If only collapsed/direct-included results show a gap, report direct output observability, not MC internal DfT superiority.
- If raw and collapsed disagree, report the abstraction sensitivity explicitly.
- If transition protocol warnings remain, report a comparative result with warnings, not clean transition sign-off.
- If AUTO_AES does not select MC, report that the tested topology heuristic did not rediscover MC; do not tune the ranking after seeing coverage.
