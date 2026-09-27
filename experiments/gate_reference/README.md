# Gate-level reference

**Can an implementation-created post-MC channel support the discovery-to-recovery flow?** The reference design connects RTL, scan insertion, anonymous capture and hypothesis-aware solving for a selected target.

## Start here

Run from the ASAL repository root in the installed Python environment:

```sh
make gate-smoke
make gate-reference-test
```

## Files and outputs

`rtl/`, `tb/`, `dft/` and `netlist/` separate design source from physical fixtures. `inputs/` holds public acquisition settings; `scripts/` bridges captures and solver transcripts. `defense_python_matrix/` explores capability assumptions, not implementations of every deployed defense.

## Scope

Reference tests separate executable models from optional physical-run records. Missing `defense_boundary/`, reference `results/` and defense-matrix result bundles are reported as skips. Use `--require-gate-records` with pytest for strict record validation; missing records never count as verified experiments.

Fresh capture needs licensed EDA tools, a technology library (`ASAL_LIBRARY_DB`) and evaluator inputs. The top-level smoke checks topology infrastructure, not this entire physical flow. Original RTL module/netlist identifiers remain stable.

See the [experiment index](../README.md), [execution guide](../../docs/EXPERIMENTS.md) and [recorded evidence](../../docs/EVIDENCE.md).
