#!/usr/bin/env python3
"""Audit the copied repository for forbidden machine-local/generated files."""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {"ucli.key", "hidden_key.evaluator.json"}
FORBIDDEN_SUFFIXES = {".fsdb", ".vcd", ".vpd", ".ddc", ".sdb", ".daidir"}


def tracked_files():
    top=subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip()
    if Path(top).resolve()!=ROOT.resolve():
        raise RuntimeError('Run this check in an ASAL Git checkout')
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    return [ROOT/path for path in paths if path]


def main() -> int:
    violations: list[str] = []
    for path in tracked_files():
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        is_dft_checkpoint = path == ROOT / "experiments/partial_scan_testability/results/checkpoint/mor1kx_aes_soc_pre_dft.ddc"
        if path.name=='evaluator_keys.csv' or 'private' in path.relative_to(ROOT).parts or ((not is_dft_checkpoint) and (path.name in FORBIDDEN_NAMES or any(path.name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES))):
            violations.append(str(path.relative_to(ROOT)))
    campaigns = ROOT / "configs" / "campaigns.yaml"
    if not campaigns.exists():
        violations.append("configs/campaigns.yaml (missing)")
    print(json.dumps({"root": str(ROOT), "forbidden_files": violations, "ok": not violations}, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
