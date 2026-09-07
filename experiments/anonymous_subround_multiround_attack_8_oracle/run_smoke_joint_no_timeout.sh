#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

cd "$ROOT"
exec "$PYTHON" scripts/adaptive_query_attack.py \
  --strategy adaptive_pairwise \
  --cases configs/smoke_two_cases.csv \
  --config configs/smoke_joint_no_timeout.yaml \
  --seeds 1 \
  --output results/smoke_joint_no_timeout.jsonl
