# 3-bit Hard Case Leakage Analysis Report

This report presents the outcomes of the 3-bit leakage sweeps on configurations that do **not** contain any confirmed unique 2-bit subsets.

## Summary of Evaluated Hard Cases

| Case ID | Candidate A | Candidate B | Candidate C | Unique Seeds | Ambiguous Seeds | Unknown Seeds | Final Label |
|---|---|---|---|---|---|---|---|
| `3bit_early__SR_104__SR_14__SR_58` | SR_104 | SR_14 | SR_58 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_15__SB_16__SB_47` | SB_15 | SB_16 | SB_47 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_3__SR_101__SR_14` | SB_3 | SR_101 | SR_14 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_119__SB_51__SR_66` | SB_119 | SB_51 | SR_66 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_23__SB_35__SB_98` | SB_23 | SB_35 | SB_98 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_125__SB_83__SB_87` | SB_125 | SB_83 | SB_87 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_49__SR_55__SR_66` | SB_49 | SR_55 | SR_66 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SR_10__SR_108__SR_66` | SR_10 | SR_108 | SR_66 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_22__SR_48__SR_7` | SB_22 | SR_48 | SR_7 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_107__SB_36__SR_8` | SB_107 | SB_36 | SR_8 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_81__SR_46__SR_88` | SB_81 | SR_46 | SR_88 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_47__SB_52__SR_44` | SB_47 | SB_52 | SR_44 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_40__SR_22__SR_57` | SB_40 | SR_22 | SR_57 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_12__SB_57__SR_12` | SB_12 | SB_57 | SR_12 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_126__SB_71__SR_7` | SB_126 | SB_71 | SR_7 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_33__SR_77__SR_9` | SB_33 | SR_77 | SR_9 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_101__SB_112__SR_86` | SB_101 | SB_112 | SR_86 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_63__SR_107__SR_65` | SB_63 | SR_107 | SR_65 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_111__SB_119__SB_13` | SB_111 | SB_119 | SB_13 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_110__SB_79__SR_14` | SB_110 | SB_79 | SR_14 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_44__SB_52__SR_88` | SB_44 | SB_52 | SR_88 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SR_0__SR_111__SR_67` | SR_0 | SR_111 | SR_67 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_32__SR_69__SR_88` | SB_32 | SR_69 | SR_88 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_56__SB_78__SB_81` | SB_56 | SB_78 | SB_81 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_114__SB_125__SB_71` | SB_114 | SB_125 | SB_71 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_1__SB_91__SR_6` | SB_1 | SB_91 | SR_6 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_101__SB_54__SR_24` | SB_101 | SB_54 | SR_24 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_83__SR_53__SR_61` | SB_83 | SR_53 | SR_61 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_117__SB_16__SR_33` | SB_117 | SB_16 | SR_33 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_112__SB_28__SR_38` | SB_112 | SB_28 | SR_38 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_108__SR_127__SR_33` | SB_108 | SR_127 | SR_33 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_57__SR_22__SR_46` | SB_57 | SR_22 | SR_46 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_122__SB_29__SR_29` | SB_122 | SB_29 | SR_29 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_73__SR_106__SR_74` | SB_73 | SR_106 | SR_74 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_5__SB_58__SR_8` | SB_5 | SB_58 | SR_8 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_24__SB_46__SR_124` | SB_24 | SB_46 | SR_124 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_35__SB_64__SR_120` | SB_35 | SB_64 | SR_120 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_123__SB_40__SB_43` | SB_123 | SB_40 | SB_43 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SR_103__SR_63__SR_96` | SR_103 | SR_63 | SR_96 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_65__SB_84__SR_115` | SB_65 | SB_84 | SR_115 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_116__SB_40__SR_20` | SB_116 | SB_40 | SR_20 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_80__SR_104__SR_94` | SB_80 | SR_104 | SR_94 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_102__SR_31__SR_76` | SB_102 | SR_31 | SR_76 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_109__SB_67__SR_120` | SB_109 | SB_67 | SR_120 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_112__SB_117__SB_3` | SB_112 | SB_117 | SB_3 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_121__SB_36__SR_14` | SB_121 | SB_36 | SR_14 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_112__SB_70__SR_57` | SB_112 | SB_70 | SR_57 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_78__SB_82__SR_63` | SB_78 | SB_82 | SR_63 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_124__SR_114__SR_80` | SB_124 | SR_114 | SR_80 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_57__SB_9__SR_57` | SB_57 | SB_9 | SR_57 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_48__SB_49__SB_97` | SB_48 | SB_49 | SB_97 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_0__SR_122__SR_37` | SB_0 | SR_122 | SR_37 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_16__SB_34__SR_41` | SB_16 | SB_34 | SR_41 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SR_53__SR_88__SR_92` | SR_53 | SR_88 | SR_92 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_15__ARK_27__MC_12` | ARK_15 | ARK_27 | MC_12 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_early__SB_115__SB_126__SB_61` | SB_115 | SB_126 | SB_61 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_26__ARK_31__MC_2` | ARK_26 | ARK_31 | MC_2 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_15__ARK_18__ARK_23` | ARK_15 | ARK_18 | ARK_23 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_23__MC_6__MC_7` | MC_23 | MC_6 | MC_7 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_16__MC_15__MC_19` | ARK_16 | MC_15 | MC_19 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_31__MC_12__MC_20` | ARK_31 | MC_12 | MC_20 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_early__SR_6__SR_76__SR_91` | SR_6 | SR_76 | SR_91 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_early__SB_27__SR_111__SR_82` | SB_27 | SR_111 | SR_82 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_26__MC_12__MC_7` | ARK_26 | MC_12 | MC_7 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_4__MC_18__MC_4` | ARK_4 | MC_18 | MC_4 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_13__MC_22__MC_7` | MC_13 | MC_22 | MC_7 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_17__ARK_2__MC_16` | ARK_17 | ARK_2 | MC_16 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_5__MC_21__MC_7` | ARK_5 | MC_21 | MC_7 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_early__SB_117__SB_30__SB_36` | SB_117 | SB_30 | SB_36 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_10__ARK_24__MC_21` | ARK_10 | ARK_24 | MC_21 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_early__SB_10__SB_32__SR_45` | SB_10 | SB_32 | SR_45 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_3__MC_13__MC_9` | ARK_3 | MC_13 | MC_9 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_early__SB_108__SR_7__SR_88` | SB_108 | SR_7 | SR_88 | 0 | 3 | 0 | `still_ambiguous` |
| `3bit_weak_late__ARK_8__MC_10__MC_16` | ARK_8 | MC_10 | MC_16 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_16__MC_23__MC_8` | ARK_16 | MC_23 | MC_8 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_23__ARK_28__MC_5` | ARK_23 | ARK_28 | MC_5 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_13__ARK_21__MC_10` | ARK_13 | ARK_21 | MC_10 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_15__ARK_2__MC_6` | ARK_15 | ARK_2 | MC_6 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_14__MC_23__MC_9` | MC_14 | MC_23 | MC_9 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_11__MC_16__MC_19` | MC_11 | MC_16 | MC_19 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_22__ARK_7__MC_13` | ARK_22 | ARK_7 | MC_13 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_14__ARK_31__ARK_6` | ARK_14 | ARK_31 | ARK_6 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_24__MC_18__MC_4` | ARK_24 | MC_18 | MC_4 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_0__MC_13__MC_15` | MC_0 | MC_13 | MC_15 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_11__MC_26__MC_4` | MC_11 | MC_26 | MC_4 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_1__ARK_31__MC_15` | ARK_1 | ARK_31 | MC_15 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_22__MC_24__MC_6` | MC_22 | MC_24 | MC_6 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_11__MC_16__MC_2` | ARK_11 | MC_16 | MC_2 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_18__ARK_20__ARK_9` | ARK_18 | ARK_20 | ARK_9 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_1__ARK_19__MC_24` | ARK_1 | ARK_19 | MC_24 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_12__MC_23__MC_6` | ARK_12 | MC_23 | MC_6 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_12__MC_14__MC_3` | ARK_12 | MC_14 | MC_3 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_11__ARK_17__ARK_26` | ARK_11 | ARK_17 | ARK_26 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_18__ARK_25__MC_19` | ARK_18 | ARK_25 | MC_19 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_17__MC_28__MC_7` | ARK_17 | MC_28 | MC_7 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_12__MC_24__MC_27` | ARK_12 | MC_24 | MC_27 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_6__MC_28__MC_29` | ARK_6 | MC_28 | MC_29 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_21__MC_15__MC_28` | ARK_21 | MC_15 | MC_28 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__ARK_1__MC_16__MC_28` | ARK_1 | MC_16 | MC_28 | 3 | 0 | 0 | `newly_unique_after_third_tap` |
| `3bit_weak_late__MC_0__MC_13__MC_31` | MC_0 | MC_13 | MC_31 | 3 | 0 | 0 | `newly_unique_after_third_tap` |

## Discussion
* By filtering out unique subsets, we focused the solver's computational budget entirely on borderline topologies.
* Adding a third tap to early-only configurations (e.g. SB-SB-SB) **does not** achieve key recovery, as early-only groups are bounded by localized diffusion limit of at most 4 bytes of $K_0$.
* However, in mixed-stage configurations (such as SB-SB-MC same column), the third tap can sometimes bridge the diffusion gap, converting previously ambiguous seeds into unique recoveries.
