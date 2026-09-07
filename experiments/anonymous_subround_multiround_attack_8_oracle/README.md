# Anonymous Subround Multiround Attack 8 Oracle

This folder is the sequential validation setup for dependency-guided adaptive sparse-FF key recovery.

The source cases are exact 2/3/4-bit tap sets from Phase 7 and Phase 7_1 for which at least one direct first-SAT/second-SAT ambiguity result exists and no direct first-SAT/second-UNSAT result exists for that case. Consensus-imputed outcomes are not accepted as proof rows.

## What is set up

- inherited AES reference, semantic oracle, and known-mapping uniqueness solver;
- proof-grade ambiguous-case extraction from Phase 7/7_1;
- structural AES/K0/plaintext dependency profiles;
- fixed nested-query correction that continues ambiguity to the final budget;
- pairwise adaptive query synthesis over two transcript-compatible keys;
- explicit terminal labels for unique, budget exhausted, support limited, and unresolved;
- dry-run validation without launching solver campaigns.

The fixed tap set is never changed during a run. A 2-bit run always observes the same two 1-bit FF functions.

## Environment

Use the existing Phase 7 virtual environment unless the execution agent creates an independently validated environment:

```bash
PYTHON=../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3
```

Commands below assume the current directory is this Attack 8 folder.

## Rebuild setup artifacts

```bash
$PYTHON scripts/select_ambiguous_cases.py
$PYTHON scripts/dependency_support.py --cases configs/selected_2bit_proven_ambiguous.csv --output reference/dependency_support_2bit_candidates.csv
$PYTHON scripts/dependency_support.py --cases configs/selected_3bit_proven_ambiguous.csv --output reference/dependency_support_3bit_candidates.csv
$PYTHON scripts/dependency_support.py --cases configs/selected_4bit_proven_ambiguous.csv --output reference/dependency_support_4bit_candidates.csv
```

These commands only derive configuration/reference data. They do not execute key-recovery campaigns.

## Validate setup

```bash
$PYTHON -m compileall -q scripts
$PYTHON scripts/validate_setup.py
$PYTHON scripts/adaptive_query_attack.py --strategy fixed_nested --dry-run
$PYTHON scripts/adaptive_query_attack.py --strategy adaptive_pairwise --dry-run
```

## Sequential execution order for the next agent

Do not skip validation stages.

1. Stage 8A: run `fixed_nested` on a small 2-bit case subset. Ambiguity must continue through the final configured query budget.
2. Stage 8B: run `adaptive_pairwise` on the exact same case/seed subset with the one-byte query domain.
3. Stage 8C: after witness replay is validated, change `query_domain` to `unrestricted` and repeat paired cases.
4. Stage 8D: only after 2-bit correctness is established, extend to inherited 3-bit and 4-bit hard cases.
5. Dependency-aware replacement tap selection and multi-model MaxSAT optimization are later Attack 8 stages, not part of the first correctness experiment.

Example campaign commands, intentionally not executed during setup:

```bash
$PYTHON scripts/adaptive_query_attack.py --strategy fixed_nested --case-limit 5 --seeds 1 --output results/stage8a_smoke.jsonl
$PYTHON scripts/adaptive_query_attack.py --strategy adaptive_pairwise --case-limit 5 --seeds 1 --output results/stage8b_smoke.jsonl
```

## Correctness rules

- Unique means first solve SAT and second solve with `K != K_star` UNSAT.
- SAT/SAT at an intermediate query count is not terminal ambiguity.
- Support-limited means second solve SAT and the full symbolic separability miter UNSAT.
- UNKNOWN is never mapped to unique or ambiguity.
- The evaluator key generates oracle observations but is not used by query synthesis.
- Query count excludes the differential reference; `oracle_encryptions` includes it.
- Original Phase 7/7_1 files are read-only inputs and are never modified.
