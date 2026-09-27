# Multibit baselines

**How does a tap set's diffusion and semantic location affect ambiguity?** Known-mapping AES models compare sparse two-, three- and four-bit observations under nested plaintext budgets.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
python experiments/multibit_baselines/scripts/parallel_runner.py --help
```

## Files and outputs

`configs/` defines candidate maps and case sets; `scripts/` contains AES, oracle and solver modules reused by recovery families. `results/` retains baseline tables and run records.

## Scope

This is controlled semantic analysis; it does not assign anonymous physical scan positions.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
