#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

cd "$ROOT"
exec "$PYTHON" scripts/run_phase7_q128_rescue.py \
  --config configs/phase7_q128_rescue.yaml \
  --workers 6 \
  --result-dir results/phase7_q128_rescue_runs \
  --summary results/phase7_q128_rescue_summary.jsonl \
  --errors logs/phase7_q128_rescue_errors.jsonl
