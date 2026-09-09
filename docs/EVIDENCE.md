# Evidence navigation

The review archive contains source-identical experiment records. The paths in
`evidence/manifest.json` connect each archived file to its path under the original
experiment tree and record its size and SHA-256. Run `make evidence-verify` to
check the archive and cross-check the result relationships below without EDA tools.

The section/table references follow *ASAL: Adaptive Scan-Based Key Recovery
from Sparse AES Subround Leakage*, Sections V–VI. Experiment names below are
directories under `experiments/`; archived records use the same names under
`evidence/source/`.

| Paper item | Implementation | Evidence to inspect |
|---|---|---|
| Table II, discovery and handoff | `anonymous_subround_multiround_attack_Leakage_Channel_Discovery/scripts/` | Archived full discovery report, anonymous trial inputs, and `results/phase0_phase1_slot_handoff.json`: 32 positives, 8 decoys, per-trial slot reuse and signature agreement |
| Section VI-B, one-bit recovery | `anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_fixed_paper384.py` and `run_late1bit_pair_rescue_paper384.py` | Tracked `paper384` manifest and 519 fixed/adaptive result JSONs in that experiment's `results/`; `make one-bit-384-verify` checks all 384 identities |
| Section VI-B, key diversity | `anonymous_subround_multiround_attack_key_diversity/scripts/` | Archived `results/raw_runs.jsonl` and `summary.json`, linking individual runs to the 80-run summary |
| Table III, scan-order tracking | `anonymous_subround_multiround_attack_phase_alpha/scripts/phase_alpha_tracking.py` | Archived input captures, discovery record, and `results/phase_alpha_tracking.json`; 75 stable-window epochs with held-out validation |
| Table IV, commercial-EDA funnel | `extra_exp1/shared/scripts/analyze_phase0_capture.py`, `build_mc_hypothesis_observation.py`, `run_mc_hypothesis_solver.py` | Archived `cases/case_*/results/phase_b/`: query/capture text, discovery funnel, attacker transcripts, and solver outputs across all eight targets |
| Fig.5(a,b), natural faults and structural regions | `RTL1_DFT_RESTUDY/scripts/analyze_aes_internal_v2.py` | Archived `results/analysis/aes_internal_v2_*summary.csv`, region breakdowns, fairness/validity records, and original `results/tmax/aes_internal_v2/` summaries |
| Fig.5(c,d), fault-share and scan-share sweeps | `RTL1_DFT_RESTUDY/scripts/aes_internal_v2_mc_faultshare.py`, `run_aes_internal_v2_mc_faultshare.sh`, `run_aes_internal_v2_mc_faultshare_mix.sh` | Archived fault-source manifests, `faultshare/` ATPG summaries, and the fault-share/25-cell reports; plotting code: `plot_ieee_dft_figures.py` |

## Gate-level evidence chain

For each target, the phase-B directory includes the anonymous discovery capture
and its query list, `phase0_discovery.json`, the Q128 attacker hypothesis input,
and the successive solver records and available adaptive scan/query pairs.
The terminal solver record's `input_transcript` basename locates the corresponding
archived attacker input in the same directory. Original absolute paths inside
records are retained as provenance; reviewers can use the local basename.

`evidence.py` checks the 256→207→144→1 discovery funnel and that the final solver
record for each target has one surviving hypothesis and SAT→UNSAT, with its
input transcript included. These are record-consistency checks; they do not
execute VCS or rerun an UNSAT proof.

To rerun a terminal solver directly on an archived transcript, use
`experiments/extra_exp1/shared/scripts/run_mc_hypothesis_solver.py --input
<local-transcript.json> --output <new-result.json> --workers <count>` with the
software dependencies installed. Regenerating physical captures additionally
requires the documented commercial EDA environment.

The archive preserves complete-campaign evidence separately from smoke outputs,
so `make discovery-smoke` does not replace the archived 32/8 discovery records.
Only the natural-fault, region, and fault-share DFT campaigns are indexed for
Fig.5; balanced/multicapture exploratory campaigns are not part of this mapping.
