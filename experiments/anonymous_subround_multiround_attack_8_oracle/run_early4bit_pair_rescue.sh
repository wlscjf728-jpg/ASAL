#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"
cd "$ROOT"
"$PYTHON" scripts/select_early4bit_ambiguity_runs.py
exec "$PYTHON" scripts/run_early4bit_pair_rescue.py --config configs/early4bit_pair_rescue.yaml --workers 23
