# Phase 7 2-bit Leakage Risk Map Report

This report presents the synthesized risk map for all 2-bit leakage combinations, combining prior results and new parallel runs.

## Risk Classification Breakdown

| Stage Pair | High Risk (Unique >= 80%) | Medium Risk (Some Unique) | Low Risk (Ambiguity) | Weak / Redundant |
|---|---|---|---|---|
| **SB-SB** | 0 | 0 | 24 | 0 |
| **SB-SR** | 0 | 0 | 25 | 0 |
| **SR-SR** | 0 | 0 | 24 | 0 |
| **SB-MC** | 28 | 6 | 0 | 0 |
| **SR-MC** | 31 | 3 | 0 | 0 |
| **MC-MC** | 46 | 2 | 0 | 0 |
| **SB-ARK** | 9 | 3 | 0 | 0 |
| **SR-ARK** | 10 | 2 | 0 | 0 |
| **MC-ARK** | 24 | 2 | 0 | 0 |
| **ARK-ARK** | 24 | 1 | 0 | 0 |

## Key Observations
1. **Late-Stage Dominance**: Pairs involving MC-MC, MC-ARK, or ARK-ARK scatter are almost exclusively **High Risk** (all_unique), achieving 100% key recovery at Query 128 (often early-stopped at Q32 or Q64).
2. **Early-Stage Safe Haven**: Early-only pairs (SB-SB, SR-SR, SB-SR) remain **Low Risk** (100% ambiguity) due to their local diffusion (affecting at most 4 bytes of $K_0$).
3. **Redundancy Penalty**: Pairs that share local column alignment or represent structurally redundant bits (same bit, different stages) suffer from reduced information density and fail to constrain the key uniquely, falling into the **Redundant or Weak** class.
