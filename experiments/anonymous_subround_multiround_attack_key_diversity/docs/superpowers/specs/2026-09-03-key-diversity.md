# ASAL AES-128 Master-Key Diversity Validation

## Goal

Validate whether the existing one-bit temporal post-MixColumns (post-MC) key-identifiability result generalizes beyond the three master-key seeds used by the existing campaign.

## Scope

Run exactly four pre-registered representative MC semantic taps against twenty new deterministic AES-128 keys, for 80 key/tap runs. The only cryptographic independent variable is the master key. Do not repeat the 128-position sweep, 2/3/4-bit campaigns, stage comparison, anonymous discovery, synthesis, tracking, or reference-plaintext variation.

## Fixed conditions

- AES-128 reference model and key schedule: copied unchanged from `_8`.
- Leakage: one post-MC semantic bit, observed at temporal depth `d=2` for Round 1 and Round 2.
- Differential reference: the existing all-zero `P0` and one-byte chosen-plaintext schedule, with one fixed query seed shared by every key.
- Solver: copied Z3 bit-vector model and the existing first-solve/second-solve uniqueness test.
- Solver timeouts: unlimited (`0 ms`), so `UNKNOWN` is never converted into success or ambiguity.
- Success: the second solve for the current transcript returns `UNSAT` after a first `SAT` model.
- Ambiguity: first `SAT`, second `SAT`.
- Unresolved: solver returns `UNKNOWN` or an observation/model inconsistency is detected.
- The evaluator key is used only to create oracle observations and perform external correctness checks; the sanitized attacker document passed to Z3 contains no secret key.

## Tap selection

The preferred deterministic rule is quartile selection by the existing per-position earliest-uniqueness metric `N_uniq`. A repository-wide audit found no artifact containing that metric for all 128 MC positions. Therefore this run records and uses the non-cherry-picked fallback: sort all 128 MC entries by semantic `bit_index` and select ranks 0, 42, 85, and 127, yielding `MC_0`, `MC_42`, `MC_85`, and `MC_127`. These cover the four MC columns. The selection manifest explicitly records that `N_uniq` was unavailable; no result is used to choose the taps.

## Per-run procedure

For each `(key_id, tap_id)` pair:

1. Generate the complete observation transcript from the evaluator-side AES oracle.
2. At each configured fixed-query checkpoint, solve `C_Q(K)`, then solve `C_Q(K) AND K != K_hat`.
3. Record the first checkpoint that reaches `SAT -> UNSAT` as `N_uniq`.
4. If the last fixed checkpoint remains `SAT -> SAT`, run the existing pair-separator/global fallback adaptive loop. After each separator query, append the observed bit and rerun both solves.
5. Stop only at `SAT -> UNSAT`, a proven no-separator/non-recovery result, or `UNKNOWN`/inconsistency.

## Required artifacts

- `configs/representative_post_mc_taps.csv`: frozen four-tap manifest and selection rationale.
- `inputs/evaluator_keys.csv`: twenty generated keys plus hashes; evaluator-only metadata.
- `results/raw_runs.jsonl`: one terminal result per key/tap run, including checkpoint history.
- `results/checkpoints.jsonl`: durable progress record written after every fixed/adaptive solve.
- `results/summary.json`: aggregate counts and convergence statistics.
- `reports/KEY_DIVERSITY_VALIDATION_REPORT.md`: generated interpretation with limitations.
- `logs/campaign.out`: background execution log.

## Acceptance

The experiment is complete only when all 80 pairs have terminal records and the terminal status is explicitly one of `FIXED_UNIQUE`, `ADAPTIVE_UNIQUE`, `PROVEN_NON_RECOVERY`, `UNKNOWN`, or `MODEL_INCONSISTENT`. The report must separate fixed-query uniqueness from adaptive uniqueness and must not call a run successful merely because the returned model equals the evaluator key.
