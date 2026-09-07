# AES-Internal Balanced Four-Cycle Capture Follow-up

This campaign reuses the revision-2 DFT netlists and the 4,000-entry balanced AES-internal fault universe. The only ATPG change is `set_atpg -capture_cycles 4`; the original `balanced4/` basic-scan results are retained as a protocol baseline.

## Purpose

The one-round pipeline requires up to four clock edges for an IARK-side fault to reach MC_REG. This follow-up tests whether the prior MC-versus-random result was caused by a single-capture observation window.

## Stuck results

| Case | Detected | AU | UD | ND | Total | Coverage | Patterns | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CASE_MC | 865 | 2777 | 1 | 279 | 3992 | 22.55% | 19 | PASS |
| CASE_RANDOM_STAGE_seed01 | 2537 | 925 | 1 | 452 | 3992 | 64.53% | 67 | PASS |
| CASE_RANDOM_STAGE_seed02 | 2595 | 938 | 1 | 385 | 3992 | 65.94% | 61 | PASS |
| CASE_RANDOM_STAGE_seed03 | 2545 | 896 | 1 | 469 | 3992 | 64.78% | 70 | PASS |
| CASE_RANDOM_STAGE_seed04 | 2411 | 1007 | 1 | 500 | 3992 | 61.33% | 63 | PASS |
| CASE_RANDOM_STAGE_seed05 | 2422 | 1048 | 1 | 449 | 3992 | 61.59% | 61 | PASS |
| CASE_RANDOM_STAGE_seed06 | 2506 | 1000 | 1 | 418 | 3992 | 63.63% | 64 | PASS |
| CASE_RANDOM_STAGE_seed07 | 2512 | 948 | 1 | 464 | 3992 | 63.78% | 64 | PASS |
| CASE_RANDOM_STAGE_seed08 | 2360 | 1050 | 1 | 505 | 3992 | 60.09% | 64 | PASS |
| CASE_RANDOM_STAGE_seed09 | 2389 | 1083 | 1 | 459 | 3992 | 60.61% | 62 | PASS |
| CASE_RANDOM_STAGE_seed10 | 2373 | 1026 | 1 | 536 | 3992 | 60.16% | 67 | PASS |

### MC versus random

- MC: 865/3992 detected, 22.550%.
- Random mean: 2465.0/3992 detected, 62.644%; range 60.090% to 65.940%.
- MC minus random mean: -40.094 percentage points.
- This result is the protocol-corrected comparison; the earlier basic-scan result remains a sensitivity baseline and is not overwritten.

## Transition results

| Case | Detected | AU | UD | ND | Total | Coverage | Patterns | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CASE_MC | 108 | 3881 | 1 | 0 | 3990 | 2.71% | 9 | PASS |
| CASE_RANDOM_STAGE_seed01 | 255 | 3734 | 1 | 0 | 3990 | 6.39% | 10 | PASS |
| CASE_RANDOM_STAGE_seed02 | 282 | 3707 | 1 | 0 | 3990 | 7.07% | 10 | PASS |
| CASE_RANDOM_STAGE_seed03 | 309 | 3680 | 1 | 0 | 3990 | 7.75% | 9 | PASS |
| CASE_RANDOM_STAGE_seed04 | 282 | 3707 | 1 | 0 | 3990 | 7.07% | 11 | PASS |
| CASE_RANDOM_STAGE_seed05 | 317 | 3672 | 1 | 0 | 3990 | 7.95% | 12 | PASS |
| CASE_RANDOM_STAGE_seed06 | 294 | 3695 | 1 | 0 | 3990 | 7.37% | 10 | PASS |
| CASE_RANDOM_STAGE_seed07 | 238 | 3751 | 1 | 0 | 3990 | 5.97% | 12 | PASS |
| CASE_RANDOM_STAGE_seed08 | 265 | 3724 | 1 | 0 | 3990 | 6.64% | 11 | PASS |
| CASE_RANDOM_STAGE_seed09 | 286 | 3703 | 1 | 0 | 3990 | 7.17% | 9 | PASS |
| CASE_RANDOM_STAGE_seed10 | 261 | 3728 | 1 | 0 | 3990 | 6.54% | 13 | PASS |

### MC versus random

- MC: 108/3990 detected, 2.710%.
- Random mean: 278.9/3990 detected, 6.992%; range 5.970% to 7.950%.
- MC minus random mean: -4.282 percentage points.
- This result is the protocol-corrected comparison; the earlier basic-scan result remains a sensitivity baseline and is not overwritten.

- TetraMAX generated no `fast_sequential` patterns for the transition mode; this mode is retained as a reference run, not as evidence of four-cycle transition propagation.

## Interpretation rule

A positive MC-minus-random result under four-cycle capture supports an MC advantage that is not explained solely by a one-cycle observation cutoff. A non-positive result means the earlier MC-cone-local gain does not generalize to the balanced upstream-inclusive fault universe, even when the capture window is extended.

## Artifacts

- `scripts/tmax/run_aes_internal_v2_balanced_multicapture_case.tcl`
- `scripts/run_aes_internal_v2_balanced_multicapture4.sh`
- `results/analysis/aes_internal_v2_balanced_multicapture4_stuck_summary.csv`
- `results/analysis/aes_internal_v2_balanced_multicapture4_transition_summary.csv`
- `results/tmax/aes_internal_v2/balanced_multicapture4/`
