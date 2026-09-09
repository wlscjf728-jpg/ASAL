# AES-Internal D1-D5 DFT Reassessment

This report is generated from the revision-2 campaign. The only intended design variable is the 128-FF variable scan bank; the functional checkpoint, common scan set, scan chain, canonical AES-internal fault source, and ATPG procedure are shared.

## Scope and validity

- Functional design: one-round `mor1kx_aes_soc` with the synthesized AES pipeline under `u_aes_peripheral`.
- Common scan: 896 FF, including `key_reg` and `plaintext_reg`, plus the unchanged host/control common set.
- Variable scan: exactly 128 FF; total scan count 1,024; one scan chain.
- Primary stage cases: IARK, SB, SR, MC; controls: ten random selections from the 512 AES stage FFs, five MC-mix ratios, and one structural auto-ranking case.
- Fault scope: AES internal combinational sites only. All AES FF Q/QN direct sites are excluded from every case, not only from the selected bank. AES output interface, host, scan-only, and clock/reset sites are out of scope.
- TetraMAX DRC completed for every case, with repeatable partial-scan warnings S19=3101 and C26=493; these do not break the controlled fairness comparison but limit absolute commercial-DFT interpretation.
- The generated stuck-at source has 73022 entries over 36511 sites; TetraMAX adds 72866 valid faults consistently (156 source entries are invalid under the DFT model); it is not the historical 422-fault list.
- A missing report, class-total mismatch, unequal scan manifest, or failed scan-path audit remains `UNRESOLVED`/`INVALID`; it is never interpreted as a low score.

## DFT fairness audit

See `results/analysis/aes_internal_v2_dft_fairness.csv`. Every case must report the same 896 common FFs, 128 variable FFs, 1,024 total scan cells, and one chain. The manifest audit also checks that the post-DFT inventory equals the requested set exactly.

## Stuck-at summary

| Case | Placement | Total | Detected | PT | AU | UD | ND | Coverage | Patterns | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CASE_IARK | IARK | 72866 | 2840 | 0 | 70025 | 1 | 0 | 3.90% | 8 | PASS |
| CASE_SB | SB | 72866 | 2740 | 0 | 70125 | 1 | 0 | 3.76% | 8 | PASS |
| CASE_SR | SR | 72866 | 2696 | 0 | 70169 | 1 | 0 | 3.70% | 8 | PASS |
| CASE_MC | MC | 72866 | 2926 | 0 | 69939 | 1 | 0 | 4.02% | 9 | PASS |
| CASE_RANDOM_STAGE_seed01 | RANDOM_STAGE | 72866 | 2910 | 0 | 69657 | 1 | 298 | 3.99% | 9 | PASS |
| CASE_RANDOM_STAGE_seed02 | RANDOM_STAGE | 72866 | 2902 | 0 | 69963 | 1 | 0 | 3.98% | 9 | PASS |
| CASE_RANDOM_STAGE_seed03 | RANDOM_STAGE | 72866 | 2936 | 0 | 69929 | 1 | 0 | 4.03% | 9 | PASS |
| CASE_RANDOM_STAGE_seed04 | RANDOM_STAGE | 72866 | 2933 | 0 | 69932 | 1 | 0 | 4.03% | 8 | PASS |
| CASE_RANDOM_STAGE_seed05 | RANDOM_STAGE | 72866 | 2931 | 0 | 69934 | 1 | 0 | 4.02% | 11 | PASS |
| CASE_RANDOM_STAGE_seed06 | RANDOM_STAGE | 72866 | 2894 | 0 | 69971 | 1 | 0 | 3.97% | 11 | PASS |
| CASE_RANDOM_STAGE_seed07 | RANDOM_STAGE | 72866 | 2885 | 0 | 69980 | 1 | 0 | 3.96% | 9 | PASS |
| CASE_RANDOM_STAGE_seed08 | RANDOM_STAGE | 72866 | 2899 | 0 | 69966 | 1 | 0 | 3.98% | 9 | PASS |
| CASE_RANDOM_STAGE_seed09 | RANDOM_STAGE | 72866 | 2902 | 0 | 69963 | 1 | 0 | 3.98% | 10 | PASS |
| CASE_RANDOM_STAGE_seed10 | RANDOM_STAGE | 72866 | 2879 | 0 | 69986 | 1 | 0 | 3.95% | 10 | PASS |
| CASE_MIX_MC_000 | MIX_MC | 72866 | 2840 | 0 | 70025 | 1 | 0 | 3.90% | 10 | PASS |
| CASE_MIX_MC_032 | MIX_MC | 72866 | 2866 | 0 | 69995 | 1 | 4 | 3.93% | 8 | PASS |
| CASE_MIX_MC_064 | MIX_MC | 72866 | 2896 | 1 | 69968 | 1 | 0 | 3.98% | 9 | PASS |
| CASE_MIX_MC_096 | MIX_MC | 72866 | 2912 | 0 | 69953 | 1 | 0 | 4.00% | 9 | PASS |
| CASE_MIX_MC_128 | MIX_MC | 72866 | 2926 | 0 | 69939 | 1 | 0 | 4.02% | 8 | PASS |
| CASE_AUTO_STAGE | AUTO_STAGE | 72866 | 2792 | 0 | 70073 | 1 | 0 | 3.83% | 8 | PASS |

### Primary comparison

- MC coverage: 4.02%.
- Random-stage range: 3.95% to 4.03%; mean 3.99%; stdev 0.0270 percentage points.
- MC minus random mean: 0.03 percentage points.
- Per-site final status differences are not claimed: this TetraMAX report path exposes source statuses in the unqualified dump. D3 uses region-scoped final ATPG summaries instead.
- This result is only a D1/D2 comparison because the common fault universe excludes all AES FF Q/QN sites; it is not promoted to a broad testability claim without region evidence.

## D3 region attribution

Region-level detected/AU/UD/ND counts are in `results/analysis/aes_internal_v2_stuck_region_breakdown.csv` and the transition counterpart. The regions use sequential-boundary-aware structural cones from the same functional checkpoint: IARK, SB, SR, MC, AES control, AES other, and explicit unresolved/out-of-scope buckets.

| Region | MC detected/total | MC coverage | Random mean detected/total | Random mean coverage | MC minus random (pp) |
|---|---:|---:|---:|---:|---:|
| IARK_CONE | 13/1954 | 0.665% | 192.60/1954 | 9.857% | -9.191 |
| SB_CONE | 4/58432 | 0.007% | 148.90/58432 | 0.255% | -0.248 |
| SR_CONE | 8/1068 | 0.749% | 187.60/1068 | 17.566% | -16.816 |
| MC_CONE | 770/5716 | 13.471% | 246.20/5716 | 4.307% | +9.164 |
| AES_CONTROL | 7/8 | 87.500% | 7.00/8 | 87.500% | +0.000 |
| AES_OTHER | 2124/5688 | 37.342% | 2124.80/5688 | 37.356% | -0.014 |

The MC cone is the key non-direct attribution: a positive regional delta supports improved observability for faults in the MC backward cone. A near-zero whole-design delta means upstream cones and non-MC regions can offset it; the experiment therefore does not justify a universal whole-design MC-superiority claim.

Per-site final fault-class diffs are intentionally not inferred from the source-status dump. The D3 region-scoped summaries provide final detected/AU/UD/ND counts by AES cone; direct Q/QN sites are absent from the source by construction.

## D4 transition fault

Transition results are generated with the same AES-internal source-site intersection and a launch/capture protocol loaded from each case SPF. See `aes_internal_v2_transition_summary.csv`, region breakdown, and SVG coverage figure. Any TetraMAX protocol or source error is retained as unresolved.
- MC_CONE transition coverage: 12.106%; random-stage mean: 3.726%; delta: +8.380 percentage points.
- Whole-design transition MC coverage is 3.43%; random-stage mean is 3.396%, so the absolute aggregate separation remains small even though the MC-cone separation persists.

## Interpretation

- D1: after globally excluding all AES FF Q/QN direct faults, the result is not a direct-observability artifact. However, whole-design MC superiority is not robust: the stuck-at gap is only +0.031 percentage points and random seeds reach 4.03% versus MC 4.02%.
- D2: MC is a meaningful stage-local candidate, but not a universal winner over every AES-internal fault region. The selected boundary trades MC-cone observability against loss of upstream IARK/SB/SR observability.
- D3: the regional result is the strongest supported claim. MC placement raises MC_CONE stuck-at coverage by +9.164 percentage points and transition coverage by +8.380 percentage points over the random-stage mean.
- D4: the same direction survives transition faults, supporting a timing-sensitive local effect rather than a stuck-at-only coincidence.
- D5: the structural auto-ranked placement is retained as a blind control; it is not used to claim commercial partial-scan optimality.
- Final classification: `LOCAL_MC_CONE_GAIN`, but `NO_ROBUST_WHOLE_DESIGN_ADVANTAGE`. The earlier host-inclusive 422-fault/22%-versus-83% result is not the evidence for this revised claim.

## D5 automatic selection

`CASE_AUTO_STAGE` uses the pre-ATPG structural ranking over the 512 AES stage FFs. The ranking does not consume TetraMAX labels, leakage transcripts, or secret-key data. Its selected manifest and ranking are retained for audit; it is not described as a commercial selector.

## Current validity decision

- DFT manifest/path audit: PASS.
- Complete stuck-at case count: 20/20.
- Complete transition case count: 20/20.
- Complete D3 stuck region count: 120/120.
- All 20 global stuck-at, 20 global transition, 120 stuck-at region, and 120 transition region runs passed summary/fault-class consistency checks; interpretation is therefore based on completed data.

## Artifacts

- `results/analysis/aes_internal_v2_dft_fairness.csv`
- `results/analysis/aes_internal_v2_stuck_summary.csv` and `aes_internal_v2_transition_summary.csv`
- `results/analysis/aes_internal_v2_*_region_breakdown.csv`
- `results/analysis/aes_internal_v2_mc_random_status_differences.csv`
- `reports/AES_INTERNAL_STUCK_COVERAGE_V2.svg`
- `reports/AES_INTERNAL_TRANSITION_COVERAGE_V2.svg`
