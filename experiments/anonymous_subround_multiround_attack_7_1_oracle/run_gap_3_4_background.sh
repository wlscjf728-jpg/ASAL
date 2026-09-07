#!/usr/bin/env bash
set -euo pipefail

BASE="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"
cd "$BASE"

"/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3" scripts/select_gap_hard_cases.py

"/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3" scripts/monitored_gap_runner.py \
  --cases configs/selected_3bit_gap_hard_cases.csv \
  --output results/raw_solver_runs_3bit_gap_confirmed.csv \
  --status results/monitored_gap_3bit_status.json \
  --log-dir logs/3bit_gap_confirmed \
  --seeds 3 \
  --batch-cases 32 \
  --workers 94 \
  --depth 2 \
  --mode differential

"/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3" scripts/monitored_gap_runner.py \
  --cases configs/selected_4bit_gap_hard_cases.csv \
  --output results/raw_solver_runs_4bit_gap_confirmed.csv \
  --status results/monitored_gap_4bit_status.json \
  --log-dir logs/4bit_gap_confirmed \
  --seeds 3 \
  --batch-cases 32 \
  --workers 94 \
  --depth 2 \
  --mode differential
