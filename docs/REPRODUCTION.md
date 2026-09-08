# Reproduction guide

## 1. Environment

The software campaigns use Python 3.10 or newer, Z3 4.13.4, cvc5 1.3.4,
PyYAML, and pytest. The one-bit solver intentionally uses unlimited solver
timeouts in the source configs; use a scheduler or a bounded smoke config when
testing on a shared machine.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## 2. Software campaigns

Run the repository smoke suite first:

```bash
make smoke
make discovery-smoke
make key-diversity-smoke
make tracking
```

Run the lightweight one-bit reproduction in two resumable stages:

```bash
make one-bit-96-dry-run
make one-bit-96
```

The runner executes these copied source scripts:

```text
experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_fixed_baseline.py
experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_pair_rescue.py
```

The fixed stage consumes `configs/late_1bit_positions.csv` and produces 96
terminal JSON rows. The pair-rescue stage consumes exactly the 32 q128
ambiguity rows and appends adaptive terminal JSON rows. Existing terminal rows
are treated as checkpoints and are not regenerated.

## 3. Discovery, diversity, and tracking

The repository wrappers invoke the copied source entry points. They preserve
the original working-directory assumptions so that relative config and result
paths remain valid.

```bash
make discovery-smoke
make key-diversity-smoke
make tracking
```

Full discovery and key-diversity campaigns may require more CPU and time. Their
source `run_*.sh` scripts are preserved under their respective experiment
directories.

## 4. Gate-level reproduction

Gate-level campaigns require the simulator and synthesis tools used to create
the original cases. Public/source fixtures are copied, but generated netlists,
compiled simulators, and evaluator key files are excluded from Git by design.
Place private inputs under `private/extra_exp1/` and set `ASAL_PRIVATE_ROOT`
before invoking the full EDA wrapper.

```bash
make gate-smoke
```

Case06 is complete through Q135. The fixed Q128 transcript is followed by
adaptive Q133 and Q134 SAT→SAT checks and a Q135 SAT→UNSAT uniqueness proof
with key match. Compact Q133–Q135 solver certificates are included and linked
by SHA-256 in `configs/gate_level_case06.yaml`; large gate-level captures and
evaluator inputs remain excluded from Git.

## 5. Latest DFT reproduction

Only `experiments/RTL1_DFT_RESTUDY` is canonical. The scripts require licensed
Design Compiler/TetraMAX binaries and the checkpoint netlist/database. Set
`DC_SHELL` and `TMAX_BIN` explicitly in the environment rather than relying on
the original machine-specific defaults.

```bash
DC_SHELL=/path/to/dc_shell TMAX_BIN=/path/to/tmax make dft-prepare
DC_SHELL=/path/to/dc_shell TMAX_BIN=/path/to/tmax make dft-run
```

The old `RTL` 422-fault experiment is not used by any reproduction target.
