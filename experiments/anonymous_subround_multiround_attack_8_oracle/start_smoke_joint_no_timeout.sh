#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/logs/smoke_joint_no_timeout.pid"
LOG_FILE="$ROOT/logs/smoke_joint_no_timeout.out"

mkdir -p "$ROOT/logs" "$ROOT/results"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT"
setsid bash ./run_smoke_joint_no_timeout.sh > "$LOG_FILE" 2>&1 < /dev/null &
echo "$!" > "$PID_FILE"
echo "started smoke joint resolver pid $(cat "$PID_FILE")"
