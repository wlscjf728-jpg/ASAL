# AES-Internal Balanced-Fault Follow-up

This campaign keeps the existing v2 DFT netlists and scan placements unchanged. It replaces the naturally skewed AES-internal fault weighting with a deterministic balanced universe containing 1,000 fault entries from each of IARK, SB, SR, and MC backward cones.

## What changed

- Changed: fault source weighting only.
- Unchanged: functional checkpoint, 896 common scan FFs, 128 variable scan FFs, 1,024 total scan FFs, one chain, SPF, ATPG options, and case list.
- Direct AES FF Q/QN faults remain excluded by the source construction.
- AES control and AES-other regions are intentionally not part of the primary balanced universe because AES control has only eight raw entries; their natural-distribution results remain in the v2 report.
- Selected entries per mode: 4000 (1000 per major stage cone).

## Stuck-at summary

| Case | Placement | Total | Detected | AU | UD | ND | Coverage | Patterns | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| CASE_IARK | IARK | 3992 | 369 | 3622 | 1 | 0 | 9.25% | 3 | PASS |
| CASE_SB | SB | 3992 | 25 | 3966 | 1 | 0 | 0.63% | 3 | PASS |
| CASE_SR | SR | 3992 | 499 | 3492 | 1 | 0 | 12.50% | 4 | PASS |
| CASE_MC | MC | 3992 | 161 | 3771 | 1 | 59 | 4.03% | 5 | PASS |
| CASE_RANDOM_STAGE_seed01 | RANDOM_STAGE | 3992 | 297 | 3694 | 1 | 0 | 7.44% | 9 | PASS |
| CASE_RANDOM_STAGE_seed02 | RANDOM_STAGE | 3992 | 300 | 3691 | 1 | 0 | 7.52% | 8 | PASS |
| CASE_RANDOM_STAGE_seed03 | RANDOM_STAGE | 3992 | 329 | 3662 | 1 | 0 | 8.24% | 8 | PASS |
| CASE_RANDOM_STAGE_seed04 | RANDOM_STAGE | 3992 | 336 | 3655 | 1 | 0 | 8.42% | 7 | PASS |
| CASE_RANDOM_STAGE_seed05 | RANDOM_STAGE | 3992 | 366 | 3625 | 1 | 0 | 9.17% | 7 | PASS |
| CASE_RANDOM_STAGE_seed06 | RANDOM_STAGE | 3992 | 310 | 3681 | 1 | 0 | 7.77% | 6 | PASS |
| CASE_RANDOM_STAGE_seed07 | RANDOM_STAGE | 3992 | 287 | 3704 | 1 | 0 | 7.19% | 7 | PASS |
| CASE_RANDOM_STAGE_seed08 | RANDOM_STAGE | 3992 | 304 | 3687 | 1 | 0 | 7.62% | 8 | PASS |
| CASE_RANDOM_STAGE_seed09 | RANDOM_STAGE | 3992 | 347 | 3644 | 1 | 0 | 8.69% | 8 | PASS |
| CASE_RANDOM_STAGE_seed10 | RANDOM_STAGE | 3992 | 332 | 3659 | 1 | 0 | 8.32% | 7 | PASS |
| CASE_MIX_MC_000 | MIX_MC | 3992 | 369 | 3622 | 1 | 0 | 9.25% | 5 | PASS |
| CASE_MIX_MC_032 | MIX_MC | 3992 | 321 | 3670 | 1 | 0 | 8.04% | 4 | PASS |
| CASE_MIX_MC_064 | MIX_MC | 3992 | 260 | 3731 | 1 | 0 | 6.51% | 6 | PASS |
| CASE_MIX_MC_096 | MIX_MC | 3992 | 207 | 3710 | 1 | 74 | 5.19% | 5 | PASS |
| CASE_MIX_MC_128 | MIX_MC | 3992 | 161 | 3820 | 1 | 10 | 4.03% | 5 | PASS |
| CASE_AUTO_STAGE | AUTO_STAGE | 3992 | 422 | 3569 | 1 | 0 | 10.57% | 4 | PASS |

## Stuck balanced comparison

- MC coverage: 4.030%.
- Random-stage mean: 8.038%; range: 7.190% to 9.170%.
- MC minus random-stage mean: -4.008 percentage points.

## Transition balanced comparison

- MC coverage: 2.710%.
- Random-stage mean: 6.992%; range: 5.970% to 7.950%.
- MC minus random-stage mean: -4.282 percentage points.

## Interpretation

This is a weighting-sensitivity experiment, not a replacement for the natural whole-design fault distribution. A change here answers whether the aggregate MC conclusion was being dominated by the large SB cone. It does not imply that the physical AES netlist contains an equal number of faults in each region.

The MC-cone-local result and the balanced four-cone aggregate must be reported separately: MC can improve observability for MC_CONE while losing upstream IARK/SR observability when only the MC boundary is scanned.

## Artifacts

- `config/aes_internal_v2_balanced4_stuck.list`
- `config/aes_internal_v2_balanced4_transition.list`
- `config/aes_internal_v2_balanced4_fault_manifest.json`
- `results/analysis/aes_internal_v2_balanced4_stuck_summary.csv`
- `results/analysis/aes_internal_v2_balanced4_transition_summary.csv`
- `results/tmax/aes_internal_v2/balanced4/`
