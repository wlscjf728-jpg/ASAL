#!/usr/bin/env python3
"""Audit the copied repository for forbidden machine-local/generated files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {"ucli.key", "hidden_key.evaluator.json"}
FORBIDDEN_SUFFIXES = {".fsdb", ".vcd", ".vpd", ".ddc", ".sdb", ".daidir"}


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        is_dft_checkpoint = path == ROOT / "experiments/RTL1_DFT_RESTUDY/results/checkpoint/mor1kx_aes_soc_pre_dft.ddc"
        if (not is_dft_checkpoint) and (path.name in FORBIDDEN_NAMES or any(path.name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)):
            violations.append(str(path.relative_to(ROOT)))
    campaigns = ROOT / "configs" / "campaigns.yaml"
    if not campaigns.exists():
        violations.append("configs/campaigns.yaml (missing)")
    print(json.dumps({"root": str(ROOT), "forbidden_files": violations, "ok": not violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

