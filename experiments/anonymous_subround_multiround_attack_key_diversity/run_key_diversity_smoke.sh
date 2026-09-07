#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python scripts/key_diversity_campaign.py --limit 1 --workers 1
