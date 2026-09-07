#!/usr/bin/env bash
set -euo pipefail

BASE="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"
cd "$BASE"

if [[ -f logs/gap_3_4_runner.pid ]] && kill -0 "$(cat logs/gap_3_4_runner.pid)" 2>/dev/null; then
  echo "runner: running pid $(cat logs/gap_3_4_runner.pid)"
else
  echo "runner: not running"
fi

echo "== 3bit status =="
if [[ -f results/monitored_gap_3bit_status.json ]]; then
  cat results/monitored_gap_3bit_status.json
else
  echo "missing"
fi

echo "== 4bit status =="
if [[ -f results/monitored_gap_4bit_status.json ]]; then
  cat results/monitored_gap_4bit_status.json
else
  echo "missing"
fi

echo "== result rows =="
wc -l results/raw_solver_runs_3bit_gap_confirmed.csv results/raw_solver_runs_4bit_gap_confirmed.csv 2>/dev/null || true

echo "== recent log =="
tail -40 logs/gap_3_4_runner.out 2>/dev/null || true
