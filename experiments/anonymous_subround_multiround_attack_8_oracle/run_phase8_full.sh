#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

cd "$ROOT"
exec "$PYTHON" scripts/run_phase8_campaign.py \
  --config configs/full_phase8_campaign.yaml \
  --workers 64 \
  --result-dir results/phase8_full_runs \
  --summary results/phase8_full_summary.jsonl \
  --errors logs/phase8_full_errors.jsonl
