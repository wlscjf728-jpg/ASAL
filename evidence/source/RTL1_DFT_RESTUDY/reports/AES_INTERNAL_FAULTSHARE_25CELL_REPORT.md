# AES Internal 25-Cell MC Fault/Scan Share Matrix

## Experiment

This campaign combines two variables while keeping the functional checkpoint,
DFT insertion style, scan chain, clock/protocol, and ATPG options unchanged.

- MC fault share: 7.85%, 20%, 40%, 60%, 80% of a fixed 4,000-entry source.
- MC scan share: 0, 32, 64, 96, 128 of the fixed 128-variable-FF budget.
- Source fault change: SB entries are exchanged for MC entries; IARK, SR, and
  AES-other entries remain fixed.
- Scan change: the existing `CASE_MIX_MC_000` through `CASE_MIX_MC_128`
  post-DFT netlists are reused.
- Direct AES FF Q/QN faults are excluded from every source.

The 25 cells were run for both stuck-at and transition faults, for 50 TetraMAX
runs total. Every generated source contains 4,000 entries. TetraMAX valid totals
are 3,989--3,997 because a small number of source sites are ignored during model
construction.

## Stuck-at coverage matrix

Rows are MC fault share and columns are MC scan FF count.

| MC fault share | 0 | 32 | 64 | 96 | 128 |
|---:|---:|---:|---:|---:|---:|
| 7.85% | 3.71% | 3.66% | 3.86% | 3.74% | 3.81% |
| 20% | 3.73% | 4.08% | 4.91% | 5.11% | 5.49% |
| 40% | 3.81% | 4.76% | 6.24% | 6.99% | 7.99% |
| 60% | 3.95% | 5.61% | 7.83% | 9.08% | 10.76% |
| 80% | 4.10% | 6.33% | 9.23% | 11.13% | 13.44% |

## Transition coverage matrix

| MC fault share | 0 | 32 | 64 | 96 | 128 |
|---:|---:|---:|---:|---:|---:|
| 7.85% | 3.03% | 2.96% | 3.18% | 3.23% | 3.18% |
| 20% | 3.08% | 3.36% | 3.73% | 4.26% | 4.61% |
| 40% | 3.13% | 4.11% | 5.16% | 6.16% | 7.04% |
| 60% | 3.28% | 5.03% | 6.66% | 8.19% | 9.57% |
| 80% | 3.38% | 5.76% | 7.86% | 10.06% | 12.14% |

## Marginal changes

Increasing MC scan from 0 to 128 produces the following coverage increase:

| MC fault share | Stuck-at | Transition |
|---:|---:|---:|
| 7.85% | +0.10 pp | +0.15 pp |
| 20% | +1.76 pp | +1.53 pp |
| 40% | +4.18 pp | +3.91 pp |
| 60% | +6.81 pp | +6.29 pp |
| 80% | +9.34 pp | +8.76 pp |

Increasing MC fault share from 7.85% to 80% produces the following increase:

| MC scan count | Stuck-at | Transition |
|---:|---:|---:|
| 0 | +0.39 pp | +0.35 pp |
| 32 | +2.67 pp | +2.80 pp |
| 64 | +5.37 pp | +4.68 pp |
| 96 | +7.39 pp | +6.83 pp |
| 128 | +9.63 pp | +8.96 pp |

## Conclusion

The two-dimensional matrix shows a clear positive interaction: MC fault share
has little effect when no MC scan FF is present, while the effect becomes much
larger as MC scan coverage increases. Conversely, adding MC scan FFs has little
effect at the natural MC fault share but produces a large gain when the fault
population is MC-heavy.

This supports the narrower claim that MC fault population and MC boundary scan
observability reinforce one another. It does not establish that MC is universally
the best scan placement, because the fault population is deliberately reweighted
and the current scan-mix manifests use an IARK-to-MC exchange for the non-MC
portion.

## Artifacts

- `config/aes_internal_v2_mc_faultshare_manifest.json`
- `scripts/run_aes_internal_v2_mc_faultshare_mix.sh`
- `scripts/tmax/run_aes_internal_v2_mc_faultshare_case.tcl`
- `results/tmax/aes_internal_v2/faultshare/`
- `logs/aes_internal_v2/tmax/faultshare_mix_driver.log`

