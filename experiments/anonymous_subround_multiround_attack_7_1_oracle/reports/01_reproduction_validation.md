# Reproduction Sanity Check Report

This report documents the reproduction test carried out to verify the correctness of the Z3 solver setup, key/plaintext generation, and semantic bit mappings compared to Phase 6.

## Test Results (Seeds 0..2)

### 1. `mc_same_byte_2` (MC Bits [0,1])
* Expectation: All seeds unique (`full_key_unique`).
* Actual Results:
  * Seed 0: `full_key_unique` (solved at Query 96, true key satisfies: sat)
  * Seed 1: `full_key_unique` (solved at Query 96, true key satisfies: sat)
  * Seed 2: `full_key_unique` (solved at Query 96, true key satisfies: sat)

### 2. `sb_same_byte_2` (SB Bits [0,1])
* Expectation: All seeds ambiguous (`ambiguity`).
* Actual Results:
  * Seed 0: `ambiguity` (solved at Query 128, true key satisfies: sat)
  * Seed 1: `ambiguity` (solved at Query 128, true key satisfies: sat)
  * Seed 2: `ambiguity` (solved at Query 128, true key satisfies: sat)

## Conclusion
The reproduction results align perfectly with prior baseline sweeps. Late-stage (MC) output bits propagate full key diffusion within 2 rounds and yield unique key recoveries, whereas early-stage (SB) bits suffer from information redundancy and underconstraint (ambiguity).
