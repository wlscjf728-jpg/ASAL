# Late 1-Bit Pair-Separator Rescue Design

## Goal

Apply adaptive recovery only to the 32 q128 fixed-query one-bit runs with an
exact `SAT -> SAT` result, while avoiding the per-step global separator cost.

## Input Selection

The campaign reads terminal q128 baseline result JSON files and selects only
runs classified as `finite_query_ambiguity`. Runs already classified as
`fixed_query_unique` are excluded. A selected task preserves its original
tap, hidden-key seed, and deterministic q128 transcript.

## Adaptive Loop

Each iteration rebuilds the exact transcript constraint and performs the
global first/second key solves. A `SAT -> UNSAT` result is full-key recovery.
For `SAT -> SAT`, the first and alternative key models form a concrete pair.
The campaign asks Z3 only for a new plaintext separating that pair, queries
the exact oracle, checkpoints the plaintext, and repeats.

## Global Separator Boundary

The global symbolic-key separator is not used to generate a portfolio query
after a pair separator succeeds. It is used only when the concrete pair is
unseparable. A global separator `SAT` supplies a fallback query; a global
separator `UNSAT` is the only non-recovery terminal result.

## Verdicts

- `adaptive_key_recovered`: exact first `SAT`, second `UNSAT` after at least
  one adaptive query.
- `proven_observational_non_recovery`: pair separator `UNSAT` and global
  separator `UNSAT` in the unrestricted fresh-plaintext domain.
- `solver_unresolved`: nonterminal; never a recovery or non-recovery claim.

## Resources and Isolation

The campaign uses at most 32 spawned worker processes. It writes to new
pair-rescue result and checkpoint directories and never reads or overwrites
the stopped global-portfolio campaign checkpoints.
