# D1-D5 DFT Reassessment Report

This report is generated from the isolated `RTL1_DFT_RESTUDY` campaign. Missing or malformed runs remain unresolved and are never counted as successes.

## Scope

- One-round `mor1kx_aes_soc` functional checkpoint; no RTL or synthesis change between cases.
- Common scan set: 896 FF; variable budget: 128 FF; total: 1,024 FF; one chain.
- Cases: IARK, SB, SR, MC, ten random seeds, and pre-ATPG topology-ranked auto selection.
- Stuck-at source: 210,378 raw functional fault-list lines from the shared pre-DFT checkpoint.
- Direct variable output-site exclusions: 1311 sites / 2622 stuck-at polarity entries requested.
- Main comparison excludes the same union of variable candidate FF direct Q/QN sites from every case.

## D1/D2 Stuck-at Summary

| Case | Placement | Total faults | Detected | PT | AU | UD | ND | Coverage | Patterns | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CASE_IARK | IARK | 205616 | 8908 | 0 | 196608 | 76 | 24 | 4.33% | 11 | PASS |
| CASE_SB | SB | 205616 | 9436 | 0 | 196080 | 76 | 24 | 4.59% | 11 | PASS |
| CASE_SR | SR | 205616 | 9392 | 0 | 196124 | 76 | 24 | 4.57% | 12 | PASS |
| CASE_MC | MC | 205616 | 9550 | 0 | 195966 | 76 | 24 | 4.65% | 13 | PASS |
| CASE_RANDOM_seed01 | RANDOM | 205616 | 8894 | 0 | 196565 | 76 | 81 | 4.33% | 12 | PASS |
| CASE_RANDOM_seed02 | RANDOM | 205616 | 8932 | 0 | 196531 | 76 | 77 | 4.35% | 12 | PASS |
| CASE_RANDOM_seed03 | RANDOM | 205616 | 8906 | 0 | 196561 | 76 | 73 | 4.33% | 12 | PASS |
| CASE_RANDOM_seed04 | RANDOM | 205616 | 8890 | 0 | 196567 | 76 | 83 | 4.33% | 10 | PASS |
| CASE_RANDOM_seed05 | RANDOM | 205616 | 8890 | 0 | 196569 | 76 | 81 | 4.33% | 11 | PASS |
| CASE_RANDOM_seed06 | RANDOM | 205616 | 8882 | 0 | 196580 | 76 | 78 | 4.32% | 11 | PASS |
| CASE_RANDOM_seed07 | RANDOM | 205616 | 8936 | 0 | 196527 | 76 | 77 | 4.35% | 9 | PASS |
| CASE_RANDOM_seed08 | RANDOM | 205616 | 8894 | 0 | 196570 | 76 | 76 | 4.33% | 11 | PASS |
| CASE_RANDOM_seed09 | RANDOM | 205616 | 8862 | 0 | 196599 | 76 | 79 | 4.31% | 11 | PASS |
| CASE_RANDOM_seed10 | RANDOM | 205616 | 8914 | 0 | 196547 | 76 | 79 | 4.34% | 11 | PASS |
| CASE_AUTO_TOPOLOGY | AUTO_TOPOLOGY | 205616 | 8969 | 0 | 196486 | 76 | 85 | 4.36% | 11 | PASS |

### D1 decision

- MC coverage on the direct-fault-excluded universe: 4.65%.
- Random coverage range: 4.31%–4.35% (mean 4.33%).
- MC minus random mean: 0.32 percentage points.
- Raw MC/random status-change rows outside the direct-site exclusion, summed over ten pairwise comparisons: 52,075.
- A positive remaining gap is evidence for non-direct testability contribution; a zero gap supports only the direct-observability interpretation.

## D3 Region Attribution

See `results/analysis/stuck_region_breakdown.csv` and `mc_random_status_differences.csv`. Region labels are conservative: direct output sites are separated first; the MC backward cone is structural; remaining AES and host sites are disjoint lexical fallbacks; unresolved sites are retained.

The selected-FF direct region has zero rows in every final fault report. This is expected: the same union of 1,311 candidate Q/QN sites, corresponding to 2,622 stuck-at entries and 2,622 transition entries, was deleted from every case before ATPG. Hence the MC gain is not the direct SA0/SA1 count of the selected FFs.

Compact region comparison (detected fault rows; random is the mean over ten seeds):

| Mode | Region | MC | Random mean | MC minus random |
|---|---|---:|---:|---:|
| Stuck-at | MC structural backward cone | 5,758 | 5,194.9 | +563.1 |
| Stuck-at | AES other | 1,058 | 1,058.0 | +0.0 |
| Stuck-at | Host | 56 | 56.0 | +0.0 |
| Stuck-at | Unresolved label | 139 | 169.3 | -30.3 |
| Transition | MC structural backward cone | 2,828 | 2,380.4 | +447.6 |
| Transition | AES other | 576 | 576.0 | +0.0 |
| Transition | Host | 0 | 0.0 | +0.0 |
| Transition | Unresolved label | 52 | 61.6 | -9.6 |

The MC backward-cone class is broad in this synthesized checkpoint and must not be read as an exact MC-internal-gate partition. The strongest defensible statement is that the residual gain is concentrated in the structural cone traced backward from MC register D inputs; a finer gate-level fault attribution requires a separate cone extraction with explicit sequential and hierarchy boundaries.

## D4 Transition-delay Result

All 15 cases loaded the same 195,404-fault transition universe after the same 2,622 direct transition entries were excluded. MC detected 5,054 faults (2.59%), versus 4,562 mean for random (2.34%), a gain of 492 faults and 0.25 percentage points. The transition runs completed and class sums matched the loaded fault totals. TetraMAX still reported the common protocol/DFT warnings V14=1, S19=3,101, and C26=493 per run; therefore this is a valid comparative run with a documented protocol caveat, not a clean warning-free production ATPG claim.

## D5 Automatic Selection

The auto case uses a deterministic pre-ATPG structural fanout/fanin ranking and has no ATPG-status, key, or ground-truth input. Its top-128 list contains 76 host-side and 52 AES-side FFs. It detected 8,969 stuck-at faults (4.36%) and 4,494 transition faults (2.30%), below MC in both modes. This demonstrates that the tested topology heuristic does not automatically rediscover MC as the best placement; it is a reproducible baseline, not evidence of commercial partial-scan selection behavior.

## Interpretation

Under the direct-fault-excluded universe, MC remains the best of the four AES stage placements and exceeds every random seed in aggregate stuck-at and transition detection. This supports a residual boundary-dependent testability effect in this checkpoint. It does not by itself establish a universal MC optimum, commercial partial-scan ranking equivalence, or causal attribution to only MC-internal gates. Those stronger claims require additional checkpoints, automatic industrial ranking, and a tighter cone/fault mapping.

## High-Coverage Companion Control

The separate `422`-entry collapsed-fault companion is documented in `reports/COLLAPSED422_HIGH_COVERAGE_REPORT.md`. Reading all 422 entries reproduces the historical `MC=349/422=82.70%` versus `random=93/422=22.04%` contrast. When the 256 entries corresponding to the 128 AES result bits and both polarities are removed, the remaining 166-entry list gives `93/166=56.02%` for every placement, including MC. This shows that the historical 22% versus 83% separation is dominated by direct selected-output faults in that small collapsed universe; the residual MC advantage reported above appears only in the larger raw uncollapsed universe.



### Security-testability overlay

The overlay in `results/analysis/security_testability_overlay.csv` uses the existing AES diffusion-support proxy (1-byte early, 4-byte MC, 0-byte non-AES random). Historical fixed-query MC/ARK rates are provenance from the prior security campaign, not a new DFT measurement. `reports/security_testability_pareto.svg` marks nondominated points under higher testability and lower leakage risk.

## Validity

The fairness table is `results/analysis/dft_fairness_audit.csv`. Any missing DFT audit, unequal scan count/chain length, unequal loaded fault totals, invalid fault-site warning, or class-total mismatch prevents a PASS label for that comparison.

## Outputs

- `results/analysis/stuck_summary.csv` and `transition_summary.csv`
- `results/analysis/stuck_region_breakdown.csv` and `transition_region_breakdown.csv`
- `results/analysis/stuck_fault_status.csv` and `transition_fault_status.csv`
- `results/analysis/mc_random_status_differences.csv`
- `results/analysis/topology_ranking.csv`
- `results/analysis/security_testability_overlay.csv`
- `reports/security_testability_pareto.svg`
