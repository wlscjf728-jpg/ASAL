#!/usr/bin/env bash
set -euo pipefail

EXP="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"

if [ -f "$EXP/logs/monitored_gap.pid" ]; then
  PID="$(cat "$EXP/logs/monitored_gap.pid" || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    pkill -P "$PID" 2>/dev/null || true
    kill "$PID" 2>/dev/null || true
    echo "stopped pid $PID"
  else
    echo "pid file exists but process is not running"
  fi
else
  echo "no pid file"
fi
