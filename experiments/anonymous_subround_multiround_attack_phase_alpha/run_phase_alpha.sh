#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python3 scripts/phase_alpha_tracking.py --config configs/phase_alpha.json
