#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

cd "$ROOT"
exec "$PYTHON" scripts/run_late1bit_campaign.py \
  --config configs/late_1bit_adaptive.yaml \
  --workers 32
