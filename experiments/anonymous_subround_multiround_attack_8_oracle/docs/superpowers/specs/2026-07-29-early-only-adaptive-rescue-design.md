# Early-Only Adaptive Pair-Rescue Design

## Goal

Re-evaluate every proof-grade fixed-query ambiguity from the existing Phase 7
and Phase 7_1 early-only 2-bit and 3-bit experiments with a fixed-tap,
pair-separator adaptive chosen-plaintext attack.

## Cohort

The source is the existing raw solver rows whose taps are all `SB_*` or `SR_*`
and whose direct fixed-query result is `SAT -> SAT`. The one `SAT -> UNKNOWN`
row is excluded. Every task preserves the source tap set, source key/query
seed, original query count, depth 2, and differential observation mode.

The expected source cohort is 622 tasks: 286 Phase 7 2-bit, 180 Phase 7
3-bit, 78 Phase 7_1 2-bit, and 78 Phase 7_1 3-bit tasks.

## Queue and Resources

Use a 32-process spawned worker pool. Queue tasks in descending source query
budget (`q255`, `q192`, `q128`, `q32`) to avoid a long high-budget tail.
Within a budget, schedule 2-bit before 3-bit. Each task writes an independent
atomic checkpoint after every accepted adaptive plaintext.

## Reproduction Gate

Before adaptive synthesis, reconstruct the source oracle transcript and rerun
the exact first/second solves. The task enters the adaptive loop only if it
reproduces `SAT -> SAT`; any mismatch or `UNKNOWN` is nonterminal and is not
classified as a recovery or non-recovery result.

## Pair-Only Adaptive Loop

For current transcript `C_n`, obtain concrete models `K_a` and `K_b`. Generate
up to four distinct plaintexts satisfying

`G_T(P, K_a) != G_T(P, K_b)`.

Score these candidates using concrete functional influence on the unresolved
key-difference bits of `K_a` and `K_b`, novelty relative to prior selected
queries, and deterministic plaintext order. Query only the highest-ranked
candidate. Re-run the global first/second key solves after every oracle update.

The global two-symbolic-key separator is not used after pair success. It is
used only when no pair separator exists. Its `UNSAT` result is the only
proven-observational-non-recovery verdict.

## Soundness Boundary

Dependency support is a query-ranking heuristic and cannot determine a final
classification. Recovery remains exact `SAT -> UNSAT`; `UNKNOWN` remains
nonterminal. The report must distinguish support-guided pair rescue from a
demonstrated independent support ablation benefit.
