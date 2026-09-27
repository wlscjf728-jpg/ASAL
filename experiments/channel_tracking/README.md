# Channel tracking

**Can a channel be reacquired after scan ordering changes?** Differential fingerprints match the same logical channel across stable-order epochs; held-out probes validate the match.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make tracking
```

## Files and outputs

`configs/` declares ordering scenarios. `inputs/` retains captured discovery fixtures; `scripts/` and `tests/` implement and check matching. Runs write ignored `results/`.

## Scope

Ordering is stable within a probe window; arbitrary per-probe permutation is outside this model.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
