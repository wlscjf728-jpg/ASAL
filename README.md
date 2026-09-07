# ASAL reproduction repository

This repository is an executable reproduction bundle for the ASAL experiments.
It is organized around runnable campaigns rather than paper-report output. The
original experiment directory is never edited; the material under
`experiments/` is a copied snapshot, and the top-level scripts provide stable
entry points for smoke tests and resumable runs.

## Reproduction levels

| Level | Command | Needs |
|---|---|---|
| Software smoke | `make smoke` | Python 3.10+, `requirements.txt` |
| 96-run lightweight one-bit reproduction | `make one-bit-96-dry-run` / `make one-bit-96` | Z3, cvc5, several CPU cores |
| Discovery / key diversity / tracking | `make discovery-smoke`, `make key-diversity-smoke`, `make tracking` | Python dependencies |
| RTL/gate-level | `make gate-smoke` | VCS/Design Compiler artifacts and local evaluator inputs |
| Latest DFT | `make dft-prepare` / `make dft-run` | Synopsys Design Compiler/TetraMAX and licensed RTL/netlist inputs |

The 96-run campaign is deliberately a lightweight reproduction of the paper's
384-run one-bit sweep: 32 positions × 3 seeds, with the same fixed-q128 and
adaptive pair-rescue code path. It is not a replacement for the paper-scale
claim. The campaign metadata records the expansion target as 128 positions × 3
seeds.

## Quick start

```bash
cd /srscl/home/jcjeong/Research/Scan_Secure/ASAL
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
make smoke
make one-bit-96-dry-run
```

`make one-bit-96` is resumable. It runs the fixed q128 baseline first and then
uses the 32 q128 ambiguity rows as input to the adaptive pair-rescue stage.
Existing terminal JSON records are not overwritten.

## Repository layout

```text
experiments/                     copied source snapshot
  anonymous_subround_multiround_attack_7_oracle/
  anonymous_subround_multiround_attack_7_1_oracle/
  anonymous_subround_multiround_attack_8_oracle/
  anonymous_subround_multiround_attack_8_1_oracle/
  anonymous_subround_multiround_attack_Leakage_Channel_Discovery/
  anonymous_subround_multiround_attack_key_diversity/
  anonymous_subround_multiround_attack_phase_alpha/
  extra_exp/                     RTL/EDA source and small inputs
  extra_exp1/                    gate-level campaign scripts/fixtures
  RTL1_DFT_RESTUDY/              latest DFT source/config snapshot
configs/                         repository-level campaign metadata
scripts/                         reproducibility entry points and audits
tests/                           repository-level integrity tests
docs/                            execution and provenance notes
```

Generated simulators, FSDB/VCD databases, commercial EDA databases, and hidden
evaluator keys are intentionally not committed. The source snapshot contains
the scripts and deterministic inputs needed to regenerate them when the
corresponding tools and private inputs are available.

## Provenance

- Original source root: `/srscl/home/jcjeong/Research/Scan_Secure/experiments`
- Latest DFT source: `experiments/RTL1_DFT_RESTUDY`
- Gate-level case06 canonical status: Q133 completion is user-confirmed; the
  visible Q132 artifact is retained as an intermediate observation.
- Old 422-fault DFT material is not a canonical campaign.

See [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md) for the exact campaign
commands and environment assumptions.
