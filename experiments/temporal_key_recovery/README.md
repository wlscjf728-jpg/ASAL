# Temporal key recovery

**Can repeated observations of the same tap make the master key unique?** Fixed-Q128 and ambiguity-only adaptive workers connect known semantic taps to AES key-schedule constraints.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make one-bit-384-dry-run
make one-bit-startup
```

## Files and outputs

`configs/` contains tap manifests and solver policies; `reference/` contains candidate maps. Bundled `results/` records are read-only reference fixtures. Public campaign outputs go to `run-output/` at the repository root.

## Scope

The known-function sweep is not an anonymous physical acquisition experiment.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
