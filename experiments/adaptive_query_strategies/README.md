# Adaptive query strategies

**When is a selected follow-up plaintext more informative than another fixed query?** Fixed nested and pairwise adaptive strategies operate on selected multibit ambiguous cases.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
python experiments/adaptive_query_strategies/scripts/validate_setup.py
python experiments/adaptive_query_strategies/scripts/adaptive_query_attack.py --strategy adaptive_pairwise --dry-run
```

## Files and outputs

`configs/` selects cases and query policies; `reference/` supplies candidate labels. `scripts/` separates query selection from AES consistency solving, and `results/` retains strategy records.

## Scope

This multibit strategy study is distinct from the primary one-bit 384-run campaign.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
