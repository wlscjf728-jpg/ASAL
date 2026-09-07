#!/usr/bin/env bash
set -euo pipefail

EXP="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"

if [ -f "$EXP/logs/monitored_gap.pid" ]; then
  PID="$(cat "$EXP/logs/monitored_gap.pid" || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "runner: running pid $PID"
  else
    echo "runner: not running (stale pid ${PID:-none})"
  fi
else
  echo "runner: no pid file"
fi

if [ -f "$EXP/results/monitored_gap_status.json" ]; then
  echo
  cat "$EXP/results/monitored_gap_status.json"
fi

if [ -f "$EXP/results/raw_solver_runs_2bit_gap_confirmed.csv" ]; then
  echo
  wc -l "$EXP/results/raw_solver_runs_2bit_gap_confirmed.csv"
fi

echo
pgrep -af 'anonymous_subround_multiround_attack_7_1_oracle/scripts/monitored_gap_runner.py' || true
