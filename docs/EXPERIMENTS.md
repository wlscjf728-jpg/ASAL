# Experiments

Run commands from the repository root after the README installation steps.

## Environment and quick checks

`make check` runs the full public verification entry point, including the extended gate checks described below. It does not launch a full recovery campaign or commercial EDA tools.

The packaged software environment uses Python 3.10+, Z3 4.13.4.0, cvc5 1.3.4, PyYAML and pytest. Dependencies are installed into a virtual environment, not the system interpreter.

```sh
make test
make smoke
make evidence-verify
make audit
```

`test` runs repository regression tests. `smoke` runs source setup checks and tests for recovery, discovery, key diversity and tracking. `evidence-verify` checks bundled records; it does not regenerate solver proofs or physical captures. `audit` examines Git-tracked files, so an ignored local simulator or virtual environment does not become a publication error.

Key-diversity smoke bootstraps twenty synthetic evaluator keys with seed 20260903 under the source family's ignored `inputs/evaluator_keys.csv`. These are experiment fixtures, not device credentials. A regression test confirms that the twenty generated key hashes match the key set in the archived 80-run results. Generating those inputs does not rerun their recovery proofs.

## One-bit fixed-to-adaptive recovery

```sh
make one-bit-384-dry-run
make one-bit-startup
ASAL_WORKERS=4 make one-bit-384
```

The manifest contains 64 MC and 64 ARK reference positions, each with seeds 0,1,2. It observes a fixed tap over two rounds. Here q counts nonreference differential plaintexts: q128 uses 129 encryptions including the shared reference.

The complete run validates the fixed-stage identities before scheduling only ambiguous cases for adaptive recovery. Outputs go to `run-output/paper384/`; terminal rows are resumed on a repeat invocation. For a separate run:

```sh
ASAL_WORKERS=4 python scripts/paper384.py --output-root run-output/new-campaign
```

The default is four workers; valid values are 1–64. The source reference configs retain 64 as their campaign setting; the wrapper applies the requested runtime worker count consistently to both stages. Full-campaign solver timeouts are unlimited. CPU/memory needs depend on the instance and concurrency; no universally validated minimum or completion time is claimed.

The dry-run loads and validates both configurations and real task inputs. The startup check executes actual Q128 fixed/adaptive worker code in isolated processes with 1-second solver-call limits and a 180-second process limit per worker. It uses a recorded ambiguous input to exercise the adaptive path. It can return UNKNOWN and still confirm startup; it is not a recovery proof or a full-campaign reproduction. Output: `run-output/startup-check.json`.

A smaller 96-run campaign is available through `make one-bit-96-dry-run` and `make one-bit-96`. It defaults to four workers and supports 1–32. Fresh output and checkpoints go to `run-output/one-bit-96/`, not the bundled completed records. The adaptive dry-run validates against bundled ambiguous inputs; actual execution uses its newly computed fixed-stage outputs.

## Discovery, tracking and key diversity

```sh
make discovery-smoke
make tracking
make key-diversity-smoke
```

Discovery smoke generates two positive cases and one negative case. Tracking runs the configured channel-reacquisition scenarios. Key-diversity smoke runs one instance and can still require substantial solver time. These source runners write to their own ignored output paths; frozen evidence is under `evidence/source/`.

## Gate and DFT layers

```sh
make gate-smoke
```

This runs Python infrastructure tests and compilation checks, not synthesis or VCS. To solve a captured terminal transcript without regenerating the hardware response, use the hypothesis solver in `experiments/gate_topologies/shared/scripts/run_mc_hypothesis_solver.py` with an input from the evidence archive. That can be a long software solve.

Fresh physical capture requires licensed synthesis/DFT/simulation tools, technology libraries and appropriate evaluator inputs. The source EDA scripts retain environment-specific paths; they are not advertised as a portable one-command flow.

`make dft-prepare` runs DFT preparation/tests against the bundled checkpoint fixtures. `make dft-run` invokes commercial tools; set `DC_SHELL` and `TMAX_BIN` and review library paths first. The repository includes an existing DFT checkpoint/netlist snapshot; rights to redistribute EDA-derived and third-party material must be confirmed before further public distribution.

## Outputs and interpretation

### Extended software and record checks

`make gate-records-test` checks all eight bundled topology fixtures. `make gate-reference-test` exercises the reference AES and capability models and reports optional physical-run checks separately. Some historical checks require `gate_reference/defense_boundary/`, its original `results/` bundle, or `defense_python_matrix/results/`, none of which is distributed here. Their absence is an explicit skip, not a passing result. A present but incomplete bundle still fails its assertions. Use `python -m pytest experiments/gate_reference/tests --require-gate-records` to require those external records strictly.

For fresh gate synthesis, set `ASAL_LIBRARY_DB` to your licensed technology `.db` file; RTL paths resolve from the checkout. Partial-scan launchers use `DC_SHELL` / `TMAX_BIN` overrides or tools on PATH. Other technology-specific EDA configuration still needs review before use.

Keep configuration, seed, semantic tap, query accounting and solver status with each result. A different first candidate in a SAT→SAT result is valid ambiguity, not an execution error. Only a unique final candidate is checked as recovered.

[Evidence](EVIDENCE.md) provides a compact map from each experiment family to recorded inputs and outputs.
