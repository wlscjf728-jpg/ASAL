# Anonymous Subround Multiround Attack Phase 7 (Known Exact Mapping)

This directory (`anonymous_subround_multiround_attack_7_oracle`) hosts the Phase 7 experiments for analyzing AES-128 master key $K_0$ recovery under sparse 1-bit flip-flop (FF) leakage using a known exact mapping oracle.

## Directory Structure

* `scripts/`: Python and shell scripts for generating maps, selecting cases, running the parallel solver, and plotting.
* `configs/`: CSV and YAML configurations for selecting cases and run settings.
* `logs/`: Separate logs for each case and seed execution.
* `results/`: CSV/JSONL output files of candidate maps, structural pair maps, imported prior results, and new execution logs.
* `reports/`: Markdown reports summarizing the inventory of prior experiments, reproduction checks, monotonicity checks, risk maps, and the final synthesis.
* `jobs/`: Scripts/job manifests for task tracking.
* `tmp/`: Temporary files used during simulation/solving.
* `plots/`: Figures and visual mappings of the risk maps.
