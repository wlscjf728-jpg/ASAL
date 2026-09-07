# Monotonicity Constraint Validation Report

This report verifies the subset monotonicity of scan leakage constraints. If a 2-bit leakage subset is sufficient to uniquely identify the key, then any superset containing these 2 bits (e.g. 3-bit or 4-bit) must mathematically yield a unique key under the same conditions.

## Comparative Results (Seeds 0..2)

| Seed | 2-bit Subset `[0,1]` Classification | 3-bit Superset `[0,1,2]` Classification | Monotonicity Preserved? |
|---|---|---|---|
| 0 | `full_key_unique` | `full_key_unique` | Yes |
| 1 | `full_key_unique` | `full_key_unique` | Yes |
| 2 | `full_key_unique` | `full_key_unique` | Yes |

## Discussion
The tests prove that monotonicity holds. Adding a third tap preserves the full-key uniqueness achieved by the 2-bit subset. This mathematical guarantee allows us to bypass running expensive solver sweeps on any 3-bit or 4-bit combinations that contain a confirmed unique 2-bit pair, saving substantial computational resources.
