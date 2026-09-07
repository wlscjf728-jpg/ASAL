# Phase 7 + Phase 7_1 Integrated Empirical Semantic Leakage Map

Date: 2026-07-09

This document integrates the Phase 7 and Phase 7_1 AES-128 sparse scan-visible 1-bit FF leakage experiments. It is intended as a durable reference for later empirical map construction, paper framing, and follow-up work that maps synthesized/retimed physical FFs back to clean AES semantic or Boolean-function locations.

The word FF in this project always means one 1-bit flip-flop. A 2-bit leakage model observes two 1-bit FFs, 3-bit observes three 1-bit FFs, and 4-bit observes four 1-bit FFs. None of these experiments assume that an attacker observes a full 128-bit register bank.

## 1. Scope And Interpretation

The experiments operate on a clean AES semantic reference surface:

- `SB_i`: SubBytes output bit `i`
- `SR_i`: ShiftRows output bit `i`
- `MC_i`: MixColumns output bit `i`
- `ARK_i`: AddRoundKey output bit `i`

This reference surface is used to define candidate semantic locations. It is not a physical netlist claim.

A result can be applied to a real synthesized/retimed AES implementation only when a scan-visible 1-bit FF stores the same Boolean value as the corresponding clean semantic bit. If the real FF stores an internal S-box node, a MixColumns partial XOR, a fused/retimed internal value, or any other non-clean Boolean function, then this map is only a guide; the actual FF requires D-input cone / Boolean support analysis.

Recommended name for the artifact:

> empirical semantic risk map of sparse scan-visible FF leakage

This is deliberately narrower than a physical FF vulnerability map.

## 2. Solver Oracle And Success Criterion

All Phase 7 / 7_1 outcomes use the same SAT-based uniqueness criterion:

1. Build AES leakage constraints `C(K)` from temporal observations of selected 1-bit semantic taps.
2. First solve: find one key satisfying `C(K)`.
3. Second solve: check `C(K) AND K != K*`, where `K*` is the first model.
4. Classification:
   - `full_key_unique`: first solve SAT and second solve UNSAT.
   - `ambiguity`: first solve SAT and second solve SAT, meaning an alternative key exists.
   - `undecided`: timeout/UNKNOWN; not counted as success.

For the final integrated data here, every recorded run is confirmed as either `full_key_unique` or `ambiguity`; no final UNKNOWN/blocked rows remain.

Common solver model:

- AES-128 known-mapping oracle over clean semantic taps.
- Temporal observations over multiple rounds/cycles.
- `depth = 2`.
- `mode = differential`.
- S-box encoding: `uf_axiom`.
- Query ladder used by monitored runs: `q = 32, 64, 96, 128, 192, 255`, with larger/no timeouts for final confirmation.

## 3. Source Files

Phase 7:

- `anonymous_subround_multiround_attack_7_oracle/configs/selected_2bit_cases_round1.csv`
- `anonymous_subround_multiround_attack_7_oracle/configs/selected_3bit_hard_cases.csv`
- `anonymous_subround_multiround_attack_7_oracle/configs/selected_4bit_hard_cases.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_2bit.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_3bit.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/raw_solver_runs_4bit.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/two_bit_risk_map.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/three_bit_hard_case_map.csv`
- `anonymous_subround_multiround_attack_7_oracle/results/four_bit_hard_case_map.csv`
- `anonymous_subround_multiround_attack_7_oracle/reports/FINAL_REPORT_7.md`

Phase 7_1:

- `anonymous_subround_multiround_attack_7_1_oracle/configs/selected_2bit_gap_parallel.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/configs/selected_3bit_gap_hard_cases.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/configs/selected_4bit_gap_hard_cases.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/results/raw_solver_runs_2bit_gap_confirmed.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/results/raw_solver_runs_3bit_gap_confirmed.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/results/raw_solver_runs_4bit_gap_confirmed.csv`
- `anonymous_subround_multiround_attack_7_1_oracle/scripts/select_gap_cases.py`
- `anonymous_subround_multiround_attack_7_1_oracle/scripts/select_gap_hard_cases.py`
- `anonymous_subround_multiround_attack_7_1_oracle/scripts/monitored_gap_runner.py`

Note: Phase 7 reports describe the intended 220-case / 3-seed sweep and consensus resolution. The current integrated counts below are computed from the raw CSVs present in the workspace. Phase 7 2-bit raw rows contain 767 rows rather than exactly 660 because the raw file includes imported/reproduced/resolved entries. The final classification set contains no undecided rows.

## 4. Selection Logic

### Phase 7

Phase 7 built the original semantic risk-map campaign:

- Generate candidate map over clean AES semantic surfaces.
- Generate structural pair map for the extended 512-candidate surface: `SB/SR/MC/ARK x 128`.
- Select a stratified set of 2-bit cases across stage pairs and topology classes.
- Use 2-bit results to select 3-bit and 4-bit hard cases that do not contain already-confirmed unique 2-bit subsets.

Phase 7 higher-order interpretation:

- 3-bit and 4-bit are not exhaustive maps over all combinations.
- They are hard-case escalation studies seeded by 2-bit ambiguity/weakness.
- This makes them evidence for tap-count scaling and boundary transitions, not complete 3/4-bit coverage.

### Phase 7_1

Phase 7_1 was created as a gap-completion study:

- Exclude Phase 7 selected 2-bit cases.
- Exclude imported prior exact anchors already covered.
- Select uncovered structural cells from the same extended 512-candidate pair map.
- Run 2-bit gap cases with monitored confirmation so final outcomes are only `full_key_unique` or `ambiguity`.
- Select 3-bit and 4-bit gap hard cases from Phase 7_1 2-bit non-unique anchors.
- Exclude any 3/4-bit combination that overlaps Phase 7 higher-order configs.
- Exclude any 3/4-bit combination containing a known unique 2-bit subset.

This makes Phase 7_1 a positional coverage supplement rather than a separate oracle model.

## 5. Config Coverage

| Phase | Leakage | Config cases | Selection role | Topology / risk-class distribution |
|---|---:|---:|---|---|
| 7 | 2-bit | 220 | original stratified risk map | early_only 60; early_late_mixed 80; late_only 39; weak_same_column 35; redundant_late 6 |
| 7 | 3-bit | 100 | hard-case escalation | early_only 60; weak_same_column 40 |
| 7 | 4-bit | 45 | hard-case escalation | early_only 30; weak_same_column 15 |
| 7_1 | 2-bit | 198 | uncovered 2-bit structural gaps | early_late_mixed 104; late_only 64; early_only 26; weak_same_column 4 |
| 7_1 | 3-bit | 90 | gap hard-case escalation | early_late_mixed 60; early_only 26; weak_same_column 4 |
| 7_1 | 4-bit | 60 | gap hard-case escalation | early_late_mixed 30; early_only 26; weak_same_column 4 |

Overlap between Phase 7 and Phase 7_1 result combinations:

| Leakage | Phase 7 combos | Phase 7_1 combos | Overlap |
|---|---:|---:|---:|
| 2-bit | 220 | 198 | 0 |
| 3-bit | 100 | 90 | 0 |
| 4-bit | 45 | 60 | 0 |

## 6. Integrated Result Summary

Row counts are solver runs. Case counts are unique leakage configurations. `all_unique` means every seed/run for the case was `full_key_unique`. `all_ambiguity` means every seed/run was ambiguous. `some_unique` means mixed seed outcomes with at least one unique and at least one ambiguous run.

| Leakage | Runs | Cases | Row ambiguity | Row unique | Case all_ambiguity | Case all_unique | Case some_unique | Final unknown/blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2-bit | 1361 | 418 | 782 | 579 | 204 | 164 | 50 | 0 |
| 3-bit | 570 | 190 | 390 | 180 | 124 | 53 | 13 | 0 |
| 4-bit | 315 | 105 | 195 | 120 | 59 | 35 | 11 | 0 |

Integrated topology-level case status:

| Leakage | Topology class | all_ambiguity | all_unique | some_unique |
|---|---|---:|---:|---:|
| 2-bit | early_only | 86 | 0 | 0 |
| 2-bit | early_late_mixed | 104 | 74 | 6 |
| 2-bit | late_only | 10 | 50 | 43 |
| 2-bit | redundant_late | 0 | 6 | 0 |
| 2-bit | weak_same_column | 4 | 34 | 1 |
| 3-bit | early_only | 86 | 0 | 0 |
| 3-bit | early_late_mixed | 36 | 12 | 12 |
| 3-bit | weak_same_column | 2 | 41 | 1 |
| 4-bit | early_only | 49 | 5 | 2 |
| 4-bit | early_late_mixed | 10 | 13 | 7 |
| 4-bit | weak_same_column | 0 | 17 | 2 |

## 7. Phase 7 Results

### Phase 7 2-bit

Raw rows: 767. Unique cases: 220. Final unknown/blocked: 0.

Row classifications:

| Classification | Runs |
|---|---:|
| ambiguity | 294 |
| full_key_unique | 473 |

Case classifications:

| Case status | Cases |
|---|---:|
| all_ambiguity | 60 |
| all_unique | 153 |
| some_unique | 7 |

Topology rows:

| Topology class | ambiguity runs | unique runs |
|---|---:|---:|
| early_only | 287 | 0 |
| early_late_mixed | 6 | 234 |
| late_only | 0 | 117 |
| redundant_late | 0 | 18 |
| weak_same_column | 1 | 104 |

Stage-pair case status:

| Stage pair | all_ambiguity | all_unique | some_unique |
|---|---:|---:|---:|
| SB-SB | 20 | 0 | 0 |
| SB-SR | 20 | 0 | 0 |
| SR-SR | 20 | 0 | 0 |
| SB-MC | 0 | 26 | 4 |
| SR-MC | 0 | 29 | 1 |
| SB-ARK | 0 | 9 | 1 |
| SR-ARK | 0 | 10 | 0 |
| MC-MC | 0 | 39 | 1 |
| MC-ARK | 0 | 20 | 0 |
| ARK-ARK | 0 | 20 | 0 |

Interpretation:

- Early-only 2-bit leakage (`SB-SB`, `SB-SR`, `SR-SR`) stayed ambiguous.
- Late-class 2-bit leakage (`MC`, `ARK`) was strongly unique across same-stage and cross-stage topologies.
- Mixed early+late pairs were usually unique in Phase 7, but a small number of mixed-seed cases remained.

### Phase 7 3-bit

Raw rows: 300. Unique cases: 100. Final unknown/blocked: 0.

| Topology class | Cases | Case all_ambiguity | Case all_unique | Case some_unique | Row ambiguity | Row unique |
|---|---:|---:|---:|---:|---:|---:|
| early_only | 60 | 60 | 0 | 0 | 180 | 0 |
| weak_same_column | 40 | 0 | 40 | 0 | 0 | 120 |

Interpretation:

- Adding a third early-only tap did not break the early-only ambiguity boundary in Phase 7.
- Weak same-column late cases became fully unique after the third tap.

### Phase 7 4-bit

Raw rows: 135. Unique cases: 45. Final unknown/blocked: 0.

| Topology class | Cases | Case all_ambiguity | Case all_unique | Case some_unique | Row ambiguity | Row unique |
|---|---:|---:|---:|---:|---:|---:|
| early_only | 30 | 23 | 5 | 2 | 71 | 19 |
| weak_same_column | 15 | 0 | 15 | 0 | 0 | 45 |

Interpretation:

- Phase 7 showed that early-only 4-bit leakage is not guaranteed ambiguous: 7/30 early-only cases had at least one unique seed, and 5/30 were unique for all observed seeds.
- Weak same-column late 4-bit cases were fully unique.

## 8. Phase 7_1 Results

### Phase 7_1 2-bit Gap Sweep

Raw rows: 594. Unique cases: 198. Final unknown/blocked: 0.

Row classifications:

| Classification | Runs |
|---|---:|
| ambiguity | 488 |
| full_key_unique | 106 |

Case classifications:

| Case status | Cases |
|---|---:|
| all_ambiguity | 144 |
| all_unique | 11 |
| some_unique | 43 |

Topology rows:

| Topology class | ambiguity runs | unique runs |
|---|---:|---:|
| early_only | 78 | 0 |
| early_late_mixed | 312 | 0 |
| late_only | 86 | 106 |
| weak_same_column | 12 | 0 |

Stage-pair case status:

| Stage pair | all_ambiguity | all_unique | some_unique |
|---|---:|---:|---:|
| SB-SB | 8 | 0 | 0 |
| SB-SR | 10 | 0 | 0 |
| SR-SR | 8 | 0 | 0 |
| SB-MC | 28 | 0 | 0 |
| SR-MC | 28 | 0 | 0 |
| SB-ARK | 24 | 0 | 0 |
| SR-ARK | 24 | 0 | 0 |
| MC-MC | 5 | 3 | 14 |
| MC-ARK | 5 | 5 | 14 |
| ARK-ARK | 4 | 3 | 15 |

Interpretation:

- Phase 7_1 deliberately targeted uncovered 2-bit structural cells, not the same high-confidence cells already seen in Phase 7.
- All early-only 2-bit gap cases remained ambiguous.
- All early_late_mixed 2-bit gap cases in this selected gap set remained ambiguous, unlike the stronger mixed behavior seen in Phase 7. This is evidence that mixed early+late risk depends heavily on exact topology and redundancy/complementarity, not just stage membership.
- Late-only gap cases split: some were fully unique, many were mixed-seed, and a smaller set remained all ambiguous. These are useful boundary points for the empirical map.

### Phase 7_1 3-bit Gap Escalation

Raw rows: 270. Unique cases: 90. Final unknown/blocked: 0.

| Topology class | Cases | Case all_ambiguity | Case all_unique | Case some_unique | Row ambiguity | Row unique |
|---|---:|---:|---:|---:|---:|---:|
| early_only | 26 | 26 | 0 | 0 | 78 | 0 |
| early_late_mixed | 60 | 36 | 12 | 12 | 125 | 55 |
| weak_same_column | 4 | 2 | 1 | 1 | 7 | 5 |

Interpretation:

- Early-only remained ambiguous even after escalation from Phase 7_1 gap anchors to 3 taps.
- Early+late mixed gap anchors began transitioning into unique recovery under 3-bit leakage.
- Weak same-column gap anchors also showed transition, though the sample size is only 4 cases because the 2-bit gap anchor pool for this class was small.

### Phase 7_1 4-bit Gap Escalation

Raw rows: 180. Unique cases: 60. Final unknown/blocked: 0.

| Topology class | Cases | Case all_ambiguity | Case all_unique | Case some_unique | Row ambiguity | Row unique |
|---|---:|---:|---:|---:|---:|---:|
| early_only | 26 | 26 | 0 | 0 | 78 | 0 |
| early_late_mixed | 30 | 10 | 13 | 7 | 42 | 48 |
| weak_same_column | 4 | 0 | 2 | 2 | 4 | 8 |

Interpretation:

- Unlike Phase 7, the Phase 7_1 early-only 4-bit gap cases remained all ambiguous. This does not contradict Phase 7; it means the 4-bit early-only breakthrough is topology-dependent and was not triggered by the Phase 7_1 gap-selected early-only anchors.
- Early+late mixed gap cases became much stronger at 4 bits: 20/30 had at least one unique seed, and 13/30 were unique for all observed seeds.
- Weak same-column gap cases also strengthened at 4 bits, but again with a small sample size.

## 9. Key Cross-Phase Findings

### 9.1 2-bit map confidence is now stronger

Phase 7 and Phase 7_1 cover disjoint 2-bit combinations:

- Phase 7: 220 2-bit combinations.
- Phase 7_1: 198 additional 2-bit combinations.
- Combined: 418 distinct 2-bit semantic pair combinations.

The combined data supports these 2-bit claims:

- Early-only 2-bit leakage remains consistently ambiguous across 86 combined cases.
- Late-only 2-bit leakage is high-risk but not uniformly high-risk across every uncovered topology; Phase 7_1 exposed weaker late-only boundary cases.
- Mixed early+late 2-bit leakage is not a single class. Phase 7 found many unique mixed pairs, while Phase 7_1 deliberately found mixed gap pairs that remained ambiguous. Exact topology matters.

### 9.2 Higher-order data should be framed as escalation evidence

The 3-bit and 4-bit experiments are not exhaustive maps. They are structured hard-case escalations:

- Phase 7 escalated original hard classes.
- Phase 7_1 escalated gap-selected non-unique 2-bit anchors.
- Both excluded already unique 2-bit subsets when selecting higher-order cases.

Therefore, the right framing is:

> The 2-bit dataset is an empirical semantic risk map over a stratified and gap-extended set of AES subround surface pairs. The 3-bit and 4-bit datasets provide hard-case escalation evidence showing how ambiguity boundaries change as the number of observed 1-bit FFs increases.

### 9.3 Early-only class is low-risk at 2 and 3 bits, but not universally safe at 4 bits

Integrated early-only cases:

- 2-bit: 86/86 all ambiguous.
- 3-bit: 86/86 all ambiguous.
- 4-bit: 49 all ambiguous, 5 all unique, 2 mixed.

The 4-bit early-only unique cases came from Phase 7, not Phase 7_1. This suggests that early-only 4-bit success requires specific cross-round/cross-column complementarity, not merely four arbitrary SB/SR taps.

### 9.4 Late and weak-late classes remain high-risk

Integrated weak_same_column cases:

- 2-bit: 34 all unique, 1 mixed, 4 all ambiguous.
- 3-bit: 41 all unique, 1 mixed, 2 all ambiguous.
- 4-bit: 17 all unique, 2 mixed, 0 all ambiguous.

This supports the idea that late-class leakage has high attack leverage, even when topology is same-column or partially redundant.

### 9.5 Mixed early+late needs a topology-aware label

Combined early_late_mixed cases:

- 2-bit: 74 all unique, 6 mixed, 104 all ambiguous.
- 3-bit: 12 all unique, 12 mixed, 36 all ambiguous.
- 4-bit: 13 all unique, 7 mixed, 10 all ambiguous.

This is the most important nuance for a paper: `early+late` should not be described as automatically unique or automatically safe. The correct interpretation is topology-sensitive complementarity.

## 10. Suggested Map Labels

For later empirical-map construction, use case-level labels rather than row-level labels:

- `confirmed_high_risk`: all seeds/runs are `full_key_unique`.
- `confirmed_low_risk`: all seeds/runs are `ambiguity`.
- `boundary_or_seed_sensitive`: mixed unique/ambiguous seeds.
- `not_resolved`: any final UNKNOWN/timeout remains. This label should not appear in the current Phase 7 + 7_1 integrated results.

For paper-level abstraction, the following classes are useful:

- `early_only_low_risk_2_3bit`: SB/SR-only at 2 or 3 taps.
- `early_only_conditional_4bit`: SB/SR-only at 4 taps; topology-dependent breakthrough possible.
- `late_dominant_high_risk`: MC/ARK-containing late-only or strongly complementary late topologies.
- `weak_late_escalates`: same-column/redundant late class that may be weak at 2 taps but often becomes unique at 3/4 taps.
- `mixed_topology_sensitive`: early+late class where exact bit relation controls complementarity.

## 11. Implications For Physical FF Mapping

The next research step should not be another blind enumeration of clean semantic indices. The main value of this map is as a reference layer for real hardware classification:

1. Extract scan-visible 1-bit FFs from synthesized/retimed AES netlists.
2. For each FF, classify its D-input function:
   - clean `SB_i`, `SR_i`, `MC_i`, or `ARK_i` semantic bit;
   - equivalent retimed version of a clean semantic bit;
   - internal S-box Boolean function;
   - MixColumns partial XOR;
   - fused or optimized logic cone;
   - unrelated control/key-schedule/state logic.
3. Apply the empirical semantic map only to FFs proven equivalent to clean semantic bits.
4. For non-clean FFs, compute Boolean support and build a new oracle/function-specific leakage model.

This distinction is essential for credibility: the current map is strong evidence about clean semantic FF leakage, not a blanket claim about every synthesized internal FF.

## 12. Paper-Ready Claims

Conservative wording:

> We construct an empirical semantic risk map for sparse scan-visible 1-bit FF leakage over AES subround surfaces. A leakage configuration is considered successful only when a SAT model exists and the second solve with `K != K*` is UNSAT; SAT/SAT is treated as ambiguity and UNKNOWN is never counted as success.

2-bit map wording:

> Across 418 disjoint 2-bit semantic leakage configurations from Phase 7 and Phase 7_1, early-only SB/SR pairs remained ambiguous, while late-stage MC/ARK-containing pairs frequently yielded unique full-key recovery. The gap study also shows that mixed early+late and late-only risk is topology-sensitive, motivating a map rather than a single tap-count threshold.

Higher-order wording:

> The 3-bit and 4-bit experiments are hard-case escalation studies. They show that weak late-stage ambiguity often collapses under additional taps, and that 4-bit early-only leakage can become uniquely identifying for selected cross-round/cross-column topologies.

Physical FF wording:

> The map should be interpreted as a semantic reference map. It applies directly to real scan FFs only when equivalence checking shows that the FF stores the same Boolean value as a clean AES subround output bit.

## 13. Open Gaps And Cautions

- The 3-bit and 4-bit datasets are not exhaustive over all combinations.
- Phase 7_1 higher-order selection is anchored on Phase 7_1 non-unique 2-bit gap pairs, so it is intentionally biased toward hard/boundary cases.
- `some_unique` cases need careful wording: they prove that unique recovery is possible for that topology/seed setting, but they are not as strong as `all_unique` cases.
- Phase 7 and Phase 7_1 use clean semantic taps, not synthesized physical netlist FFs.
- Real circuit application requires equivalence or Boolean cone analysis.
- The `early_late_mixed` class should be refined into sublabels based on byte/row/column/bit relation before drawing a final heatmap.

## 14. Minimal Data Model For The Future Map

A practical map row should contain:

- `tap_count`: 2, 3, or 4.
- `phase_source`: `7`, `7_1`, or later physical-netlist phase.
- `candidate_ids`: sorted list of semantic candidates.
- `stages`: stage multiset, e.g. `SB+MC`, `MC+ARK`, `SB+SR+SR`.
- `topology_class`: early_only, late_only, weak_same_column, redundant_late, early_late_mixed, refined subclasses.
- `case_status`: all_unique, all_ambiguity, some_unique, not_resolved.
- `unique_seed_count` and `seed_count`.
- `min_query_for_unique`, if any.
- `notes`: redundancy/complementarity explanation.
- `physical_applicability`: semantic-only, equivalent-FF, or function-specific-needed.

## 15. Bottom Line

The integrated Phase 7 + Phase 7_1 data supports a credible empirical semantic map:

- 2-bit coverage is now substantially stronger because Phase 7_1 filled disjoint structural gaps from Phase 7.
- Higher-order 3/4-bit data now exists for both the original Phase 7 hard cases and the Phase 7_1 gap hard cases.
- The strongest stable conclusion is not simply "more bits means break"; it is that sparse FF leakage risk is controlled by semantic stage, topology, redundancy, and cross-round diffusion.
- This is a useful bridge from clean AES semantic experiments to synthesized/retimed physical FF classification.
