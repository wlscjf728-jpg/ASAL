# Partial-scan testability

**What testability benefit can motivate scanning an implementation-created AES boundary?** Controlled scan budgets and fault populations compare MC placement with other stages and random selections.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make dft-prepare
```

## Files and outputs

`config/` specifies scan selections and fault universes; `scripts/` separates preparation, DC/TetraMAX execution and analysis. `results/checkpoint/` is an intentional input fixture, not disposable cache; other `results/` folders retain measured counts.

## Scope

Preparation does not run ATPG. Fresh EDA work requires licensed tools and library setup. Preserve fault denominators when comparing coverage. Redistribution rights for existing checkpoint/netlist material remain an author decision.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
