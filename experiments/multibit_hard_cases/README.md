# Multibit hard cases

**Which sparse tap combinations remain difficult after the baseline sweep?** Selected cases extend the structural and solver study around remaining ambiguity and unresolved instances.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
python experiments/multibit_hard_cases/scripts/monitored_gap_runner.py --help
```

## Files and outputs

`configs/` stores selected tap sets; `scripts/` contains selectors and the monitored runner. `results/` preserves the case-level study. Shared model variants are retained to avoid changing the original experiment semantics.

## Scope

Inspect solver limits and case selection before starting a long run. UNKNOWN is not proof of ambiguity.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
