# Anonymous channel discovery

**Which anonymous scan response is compatible with the target AES function?** Repeatability, plaintext dependency, timing and held-out probes narrow the channel before key recovery.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make discovery-smoke
```

## Files and outputs

`configs/` controls the behavioral acquisition model. `scripts/` includes discovery and recovery handoff bridges; `tests/` checks the discovery contract. Fresh smoke output stays under ignored `results/`.

## Scope

The smoke model validates selection logic, not newly captured hardware traces.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
