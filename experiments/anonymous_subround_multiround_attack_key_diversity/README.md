# ASAL Key Diversity Validation

This folder is an isolated copy of the Attack 8 AES/oracle/Z3/adaptive path for the additional master-key diversity validation. The source campaigns remain untouched.

The frozen design is four post-MC one-bit taps (`MC_0`, `MC_42`, `MC_85`, `MC_127`) across twenty new deterministic evaluator keys. Every pair uses the same zero reference plaintext, the same nested chosen-plaintext schedule, differential leakage, and temporal depth `d=2`.

The attack-side solver receives a sanitized observation document with evaluator secret key material removed. Each checkpoint performs a first solve and a second solve with `K != K_hat`. Only `SAT -> UNSAT` is unique. Fixed-query ambiguity is passed to the copied pair-first/global-fallback adaptive separator, without introducing a new attack algorithm.

Run tests with:

```bash
pytest -q tests/test_key_diversity_campaign.py
```

Inspect the plan/spec under `docs/superpowers/`. The complete campaign is intended to run detached:

```bash
setsid bash run_key_diversity.sh > logs/campaign.out 2>&1 < /dev/null &
```

Progress is durable in `results/checkpoints.jsonl`; terminal records are appended to `results/raw_runs.jsonl`. Generate the summary with `python scripts/summarize_results.py`.
