#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/logs/phase8_full.pid"
LOG_FILE="$ROOT/logs/phase8_full.out"

mkdir -p "$ROOT/logs" "$ROOT/results/phase8_full_runs"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT"
setsid bash ./run_phase8_full.sh > "$LOG_FILE" 2>&1 < /dev/null &
echo "$!" > "$PID_FILE"
echo "started Phase 8 full campaign pid $(cat "$PID_FILE")"
