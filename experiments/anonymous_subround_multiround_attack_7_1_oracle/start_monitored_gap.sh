#!/usr/bin/env bash
set -euo pipefail

ROOT="/srscl/home/jcjeong/Research/Scan_Secure/experiments"
EXP="$ROOT/anonymous_subround_multiround_attack_7_1_oracle"
PY="$ROOT/anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

if [ ! -x "$PY" ]; then
  PY="python3"
fi

mkdir -p "$EXP/logs" "$EXP/results"

if [ -f "$EXP/logs/monitored_gap.pid" ]; then
  OLD_PID="$(cat "$EXP/logs/monitored_gap.pid" || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "already running pid $OLD_PID"
    exit 0
  fi
fi

cd "$ROOT"

setsid "$PY" \
  "$EXP/scripts/monitored_gap_runner.py" \
  --cases configs/selected_2bit_gap_parallel.csv \
  --seeds 3 \
  --batch-cases 10 \
  --workers 96 \
  > "$EXP/logs/monitored_gap.out" \
  2>&1 < /dev/null &

PID="$!"
echo "$PID" > "$EXP/logs/monitored_gap.pid"
echo "started monitored gap runner pid $PID"
echo "status: $EXP/results/monitored_gap_status.json"
echo "results: $EXP/results/raw_solver_runs_2bit_gap_confirmed.csv"
echo "log: $EXP/logs/monitored_gap.out"
