# Phase 7 Q128 Ambiguity Rescue Design

## Objective

Test whether the Phase 8 ambiguity-reuse attack can recover AES-128 `K0` from the exact Phase 7 early+late 2-bit seed-runs that remained directly ambiguous after the Phase 7 maximum transcript of 128 nested queries.

This experiment supports the claim that an ambiguity-guided continuation can rescue a transcript that the completed Phase 7 sweep did not identify uniquely. It does not, by itself, prove superiority over an equal-size random continuation beyond q128.

## Scope

Only direct `SAT -> SAT` rows from `anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_2bit.csv` are eligible. UNKNOWN, timeout consensus, and imputed outcomes are excluded.

| Case | Seed | Taps | Phase 7 baseline |
|---|---:|---|---|
| `SB_10__MC_16` | 0 | `SB_10`, `MC_16` | q128 `SAT -> SAT` |
| `SB_13__MC_14` | 0 | `SB_13`, `MC_14` | q128 `SAT -> SAT` |
| `SB_17__ARK_92` | 2 | `SB_17`, `ARK_92` | q128 `SAT -> SAT` |
| `SB_37__MC_78` | 2 | `SB_37`, `MC_78` | q128 `SAT -> SAT` |
| `SB_5__MC_75` | 2 | `SB_5`, `MC_75` | q128 `SAT -> SAT` |
| `SR_111__MC_6` | 1 | `SR_111`, `MC_6` | q128 `SAT -> SAT` |

Phase 7 contains no 3-bit or 4-bit early+late mixed runs, so no 3/4-bit run belongs in this rescue campaign.

## Execution Lifecycle

1. Stop the existing Phase 8 64-worker process group and verify that its parent and children have exited.
2. Preserve all existing result and log files; do not delete or overwrite the previous campaign.
3. Reconstruct each selected run with the original Phase 7 key seed, tap mapping, depth 2, differential leakage mode, and exact nested q128 plaintext prefix.
4. Re-run the q128 two-solver check and require direct `SAT -> SAT` before adaptive continuation. A baseline mismatch is an error, not an attack verdict.
5. Assign one selected run to each worker, for exactly six concurrent workers.
6. Continue from q128 with solver-generated distinguishing plaintexts, up to q255.

## Adaptive Attack

For transcript constraint `C_Q(K)`, first solve `C_Q(K)` for one candidate and then solve `C_Q(K) AND K != K*`.

- `UNSAT` on the second solve means `key_recovered`.
- `SAT` supplies an alternative key for ambiguity-guided query synthesis.
- A concrete candidate-pair separator is attempted first.
- If that pair is observationally equivalent, a global joint miter is required before declaring observational non-recovery.
- Every synthesized plaintext is queried through the same oracle and appended to the transcript before repeating the uniqueness check.

The query domain is unrestricted plaintext, and Z3 solver timeouts are disabled (`timeout=0`).

## Terminal Verdicts

- `key_recovered`: first solve SAT and second solve UNSAT.
- `proven_observational_non_recovery`: the global separator is UNSAT while multiple keys remain.
- `non_recovery_within_q255`: q255 still gives direct SAT -> SAT.
- Solver UNKNOWN, process failure, or baseline mismatch is unresolved/error and must never be converted into either verdict.

## Outputs and Resume

The rescue campaign uses dedicated PID, log, per-run JSON, summary JSONL, and error files under the Phase 8 directory. Existing Phase 8 output remains untouched. A completed per-run JSON is the resume marker; errors remain retryable.

Each result records the source Phase 7 row, seed, taps, initial q128 verdict, final query count, adaptive plaintext provenance, all SAT/UNSAT checks, terminal verdict, and wall time.

## Validation

Before launch:

- Confirm all six source rows are direct q128 `SAT -> SAT`.
- Confirm the reconstructed q128 transcript reproduces ambiguity for each run.
- Confirm the campaign plans exactly six tasks and six workers.
- Confirm dry-run output paths do not overlap the previous full campaign.

After launch, verify the detached process, six active workers, initial baseline checks, and an empty error log.
