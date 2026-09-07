#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"
cd "$ROOT"
exec "$PYTHON" scripts/run_discovery_campaign.py --config configs/discovery_config.yaml --positive 2 --negative 1
