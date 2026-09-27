# Evidence and recorded results

The repository separates **record verification** from **experiment re-execution**. Frozen inputs and results are under `evidence/source/`; `evidence/manifest.json` records their original relative locations, sizes and SHA-256 hashes.

```sh
make evidence-verify
make one-bit-384-verify
```

These commands verify hashes, identities and relationships between existing records. They do not rerun an UNSAT proof, VCS capture or ATPG campaign.

## Data map

Historical names below identify the immutable archive under `evidence/source/`. Active code uses the descriptive directories in the [experiment index](../experiments/README.md). Archive paths and hashes retain their acquisition-era names.

| Study | Where to begin | What the records contain |
|---|---|---|
| Anonymous discovery | `anonymous_subround_multiround_attack_Leakage_Channel_Discovery/results/phase0_phase1_slot_handoff.json` in the archive | 32 positive and 8 decoy trials; slot reuse and common-query signature checks |
| One-bit recovery | `experiments/temporal_key_recovery/configs/late_1bit_positions_paper384.csv` and its `results/paper384_*/` directories | 384 fixed records and 135 adaptive terminal records |
| Key diversity | `anonymous_subround_multiround_attack_key_diversity/results/{raw_runs.jsonl,summary.json}` in the archive | 80 individually identified runs and their aggregate |
| Scan-order tracking | `anonymous_subround_multiround_attack_phase_alpha/results/phase_alpha_tracking.json` in the archive | Stable-window tracking epochs, probes and validation outcomes |
| Gate recovery | `extra_exp1/cases/case_*/results/phase_b/` in the archive | Anonymous captures, discovery, hypothesis inputs and solver results |
| Testability | `RTL1_DFT_RESTUDY/results/analysis/` and `results/tmax/` in the archive | Coverage summaries, structural regions, fault-share and scan-share studies |

For broader two-/three-/four-bit semantic experiments, see the [source-family index](../experiments/README.md).

## Reading a recovery record

Keep the case ID, seed, tap/function, query count and solver outcomes together. SAT→UNSAT denotes a unique key under the recorded model; SAT→SAT denotes residual ambiguity. Query counts in the software one-bit campaign exclude the shared reference plaintext. Gate filenames use their own acquisition convention; do not compare counts without the transcript metadata.

The bundled reference manifest's outcomes are 249 fixed-budget unique and 135 adaptively recovered runs. These are recorded results, not newly computed proofs whenever verification prints success.

## Gate evidence chain

Each target's phase-B folder links capture/query files, anonymous discovery, hypothesis-aware input transcripts and solver outputs. A terminal solver record's `input_transcript` basename identifies its input within that archive folder. Historical absolute paths in raw records are provenance, not required checkout locations.

Verification checks the 256→207→144→1 discovery funnel, terminal SAT→UNSAT status and input presence across eight targets. This establishes record consistency; fresh capture and independent solving remain separate operations.

## Preservation

Frozen report files are retained only where the evidence manifest indexes them. Development plans and duplicate narrative reports are not public navigation entry points. Historical identifiers within frozen records remain unchanged; active imports and launchers use current experiment names.

The archive is not overwritten by smoke runs. Keep new outputs in ignored locations and preserve the existing result identities when resuming a campaign.
