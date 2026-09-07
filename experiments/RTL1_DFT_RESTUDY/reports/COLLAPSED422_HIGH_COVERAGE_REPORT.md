# Collapsed-422 High-Coverage Companion Report

This is a supplementary comparison using the historical 422-entry collapsed stuck-at list. It is intentionally separate from the raw uncollapsed D1-D5 universe.

## Conditions

- The same 15 post-DFT cases and the same current 1,024-FF/one-chain checkpoint were used.
- `direct_included` reads all 422 entries.
- `direct_excluded` deletes the common 2,622-entry direct Q/QN list; only 256 entries overlap this 422-entry list, leaving 166 faults.
- Coverage is TetraMAX detected faults divided by the reported total fault count.

## Results

| Policy | Placement | Total | Detected | AU | ND | Coverage | Patterns | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| direct_included | IARK | 422 | 93 | 329 | 0 | 22.04% | 4 | PASS |
| direct_included | SB | 422 | 93 | 151 | 178 | 22.04% | 5 | PASS |
| direct_included | SR | 422 | 93 | 329 | 0 | 22.04% | 8 | PASS |
| direct_included | MC | 422 | 349 | 73 | 0 | 82.70% | 9 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 5 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 6 | PASS |
| direct_included | RANDOM | 422 | 93 | 285 | 44 | 22.04% | 6 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 5 | PASS |
| direct_included | RANDOM | 422 | 93 | 148 | 181 | 22.04% | 6 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 5 | PASS |
| direct_included | RANDOM | 422 | 93 | 151 | 178 | 22.04% | 5 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 6 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 5 | PASS |
| direct_included | RANDOM | 422 | 93 | 329 | 0 | 22.04% | 6 | PASS |
| direct_included | AUTO_TOPOLOGY | 422 | 93 | 151 | 178 | 22.04% | 4 | PASS |
| direct_excluded | IARK | 166 | 93 | 73 | 0 | 56.02% | 6 | PASS |
| direct_excluded | SB | 166 | 93 | 73 | 0 | 56.02% | 6 | PASS |
| direct_excluded | SR | 166 | 93 | 73 | 0 | 56.02% | 7 | PASS |
| direct_excluded | MC | 166 | 93 | 73 | 0 | 56.02% | 6 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 6 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 6 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 7 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 7 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | RANDOM | 166 | 93 | 73 | 0 | 56.02% | 5 | PASS |
| direct_excluded | AUTO_TOPOLOGY | 166 | 93 | 66 | 7 | 56.02% | 5 | PASS |

### direct_included

- MC: 349/422 (82.70%).
- Random range: 22.04%–22.04% (mean 22.04%).
- MC minus random mean: 60.66 percentage points.

### direct_excluded

- MC: 93/166 (56.02%).
- Random range: 56.02%–56.02% (mean 56.02%).
- MC minus random mean: 0.00 percentage points.

## Interpretation

The direct-included run reproduces the historical 82.70% versus 22.04% contrast. However, after removing the direct output faults that account for the MC-only detections, all placements converge to 93/166 (56.02%) in this legacy list. Therefore the historical 422-list result is not evidence of a residual MC-specific gain. The raw D1-D5 result remains the complementary evidence because it uses a much larger common uncollapsed universe and observes a residual MC advantage after direct-fault exclusion.

This companion must not be presented as a replacement for D1. It is a denominator/attribution control that explains why the legacy 22% versus 83% plot is visually strong but dominated by direct selected-output faults.
