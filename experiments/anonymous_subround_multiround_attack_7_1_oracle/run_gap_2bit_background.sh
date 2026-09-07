#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PY="./anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

nohup "$PY" \
  anonymous_subround_multiround_attack_7_1_oracle/scripts/monitored_gap_runner.py \
  --cases configs/selected_2bit_gap_parallel.csv \
  --seeds 3 \
  --batch-cases 10 \
  --workers 32 \
  > anonymous_subround_multiround_attack_7_1_oracle/logs/gap_2bit_monitored.out \
  2>&1 &

echo $! > anonymous_subround_multiround_attack_7_1_oracle/logs/gap_2bit_monitored.pid
echo "started gap 2-bit runner pid $(cat anonymous_subround_multiround_attack_7_1_oracle/logs/gap_2bit_monitored.pid)"
