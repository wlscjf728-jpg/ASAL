# Experiments

Start with the top-level Makefile. Each directory represents a research question rather than a chronological development phase. Its local README identifies the entry point, inputs, outputs and evaluation boundary.

| Directory | Purpose |
|---|---|
| `temporal_key_recovery` | Main fixed/adaptive recovery, one-bit manifests and solver workers |
| `multibit_baselines` | Multibit semantic sweep/model support |
| `multibit_hard_cases` | Extended semantic/topology study |
| `adaptive_query_strategies` | Additional adaptive study source |
| `channel_discovery` | Anonymous channel discovery and handoff |
| `key_diversity` | Separate key-diversity campaign |
| `channel_tracking` | Behavioral tracking across scan-order epochs |
| `gate_reference` | RTL/EDA reference flow and capability-model examples |
| `gate_topologies` | Eight-target gate campaign and shared infrastructure |
| `partial_scan_testability` | Partial-scan placement and testability experiments |

[Method](../docs/METHOD.md) explains the research idea. [Experiments](../docs/EXPERIMENTS.md) describes commands and assumptions. [Evidence](../docs/EVIDENCE.md) describes stored results.

The individual families are not interchangeable experiments. Known-function software sweeps, anonymous discovery, physical response generation and ATPG address different questions. `scripts/` contains implementations, `configs/` or `config/` declares cases, `tests/` checks contracts, and `results/` retains useful recorded fixtures. Gate families additionally separate RTL, testbenches, DFT scripts and target cases.

Historical identifiers inside result payloads and under `evidence/source/` are preserved provenance, not executable paths. Server job-control launchers, presentation assets and transient synthesis files are not part of the public interface. Shared and case-specific gate fixtures are retained because they represent different targets; they are not interchangeable copies.
