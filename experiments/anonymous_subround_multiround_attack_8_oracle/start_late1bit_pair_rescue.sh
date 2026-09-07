#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/logs/late_1bit_pair_rescue.pid"
LOG_FILE="$ROOT/logs/late_1bit_pair_rescue.out"

mkdir -p "$ROOT/logs" "$ROOT/results/late_1bit_pair_rescue_runs" "$ROOT/results/late_1bit_pair_rescue_checkpoints"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT"
setsid bash ./run_late1bit_pair_rescue.sh >> "$LOG_FILE" 2>&1 < /dev/null &
echo "$!" > "$PID_FILE"
echo "started late one-bit pair rescue pid $(cat "$PID_FILE"); log: $LOG_FILE"
