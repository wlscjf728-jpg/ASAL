#!/usr/bin/env bash
set -euo pipefail

BASE="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"
cd "$BASE"

if [[ ! -f logs/gap_3_4_runner.pid ]]; then
  echo "no pid file"
  exit 0
fi

PID="$(cat logs/gap_3_4_runner.pid)"
if kill -0 "$PID" 2>/dev/null; then
  pkill -TERM -P "$PID" 2>/dev/null || true
  kill -TERM "$PID" 2>/dev/null || true
  echo "sent TERM to $PID and children"
else
  echo "pid $PID is not running"
fi
