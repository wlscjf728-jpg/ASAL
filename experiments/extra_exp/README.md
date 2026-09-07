# MC9 EDA End-to-End Replication

This directory contains the controlled `late1_MC_9__seed2` replication from
the frozen semantic campaign through a Synopsys-synthesized, scan-inserted
AES-128 gate-level DUT.

## Evidence flow

```text
frozen inputs
  -> RTL KAT and MC trace
  -> DC/DFT 256-cell scan path
  -> anonymous Phase 0 discovery
  -> gate Q128 observation and semantic bitwise bridge
  -> fixed-query Z3 SAT/SAT
  -> gate-measured adaptive separators
  -> final Q130 Z3 SAT/UNSAT
```

The attack-side files do not contain the evaluator key or the evaluator scan
mapping:

- `results/phase_b/phase0_gate_scan_attack.txt`
- `results/phase_b/q128_gate_observations_attack.json`
- `results/phase_b/q129_gate_observations_attack.json`

Evaluator-only artifacts are kept separately under `results/evaluator/` and
the solver wrapper injects the hidden key only for correctness checking, not
for constructing the leakage constraints.

The detailed outcome is recorded in
`MC9_EDA_END_TO_END_REPORT.md` after the final unlimited-time Q130 solve.
The Verdi FSDB viewing instructions are in
`results/verdi/README_VISUAL_EVIDENCE.md`.
