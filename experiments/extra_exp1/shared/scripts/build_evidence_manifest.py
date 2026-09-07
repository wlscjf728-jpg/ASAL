#!/usr/bin/env python3
"""Hash the reproducibility-critical MC9 EDA evidence artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PATTERNS = [
    "inputs/*.json",
    "provenance/*",
    "*.md",
    "scripts/*.py",
    "scripts/*.sh",
    "rtl/*.sv",
    "rtl/*.v",
    "tb/*.sv",
    "tb/*.v",
    "dft/*.tcl",
    "dft/*.txt",
    "netlist/extra_exp_prescan.v",
    "netlist/extra_exp_postscan.v",
    "netlist/extra_exp_postscan.spf",
    "netlist/extra_exp_postscan.sdc",
    "results/evaluator/*.rpt",
    "results/evaluator/*.json",
    "results/phase_b/*.json",
    "results/phase_b/*_attack.txt",
    "results/phase_b/*_eval5.txt",
    "results/phase_b/*_check.json",
    "results/verdi/*.fsdb",
    "results/verdi/*.markers.txt",
    "results/verdi/*.summary.txt",
    "results/verdi/figures/*.png",
    "results/verdi/sessions/*",
    "logs/*.log",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    paths = set()
    for pattern in PATTERNS:
        paths.update(ROOT.glob(pattern))
    records = []
    for path in sorted(path for path in paths if path.is_file()):
        records.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        })
    payload = {
        "schema": "mc9-eda-evidence-manifest-v1",
        "experiment": "late1_MC_9__seed2",
        "artifact_count": len(records),
        "artifacts": records,
    }
    output = ROOT / "results/evidence_manifest.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"output": str(output), "artifact_count": len(records)}, indent=2))


if __name__ == "__main__":
    main()
