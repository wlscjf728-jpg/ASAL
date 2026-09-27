# Key diversity

**Does the observed recovery behavior depend on one evaluator key?** A separate campaign repeats controlled tap/query settings over a deterministic synthetic key set.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make smoke
# Longer solver experiment:
make key-diversity-smoke
```

## Files and outputs

`configs/` declares cases; `reference/` supplies function labels. The launcher generates ignored evaluator fixtures in `inputs/` when absent. Frozen 80-run records are indexed by the evidence guide.

## Scope

A one-instance smoke solve is not a rerun of the full key-diversity campaign.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
