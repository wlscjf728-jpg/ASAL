#!/usr/bin/env bash
set -euo pipefail

BASE="/srscl/home/jcjeong/Research/Scan_Secure/experiments/anonymous_subround_multiround_attack_7_1_oracle"
cd "$BASE"
mkdir -p logs

if [[ -f logs/gap_3_4_runner.pid ]] && kill -0 "$(cat logs/gap_3_4_runner.pid)" 2>/dev/null; then
  echo "already running: $(cat logs/gap_3_4_runner.pid)"
  exit 0
fi

setsid bash run_gap_3_4_background.sh > logs/gap_3_4_runner.out 2>&1 &
echo "$!" > logs/gap_3_4_runner.pid
echo "started gap 3/4 runner pid $(cat logs/gap_3_4_runner.pid)"
