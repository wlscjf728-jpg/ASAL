#!/usr/bin/env python3
"""Create evaluator-only scan mapping from the generated DC scan-path report."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CELL_LINE = re.compile(r"^\s*(?:I\s+1\s+)?(\d+)\s+(\S+)(?:\s+.*)?$")


def parse(path: Path) -> dict:
    cells = []
    for line in path.read_text().splitlines():
        match = CELL_LINE.match(line)
        if match is None:
            continue
        index = int(match.group(1))
        name = match.group(2)
        # The report contains a chain summary row (256 scan_in scan_out ...)
        # and detailed rows for the individual cells. Only detailed instance
        # rows are part of the mapping.
        if not 0 <= index < 256 or "/" not in name:
            continue
        cells.append({"scan_slot": index, "instance_name": name})
    cells.sort(key=lambda row: row["scan_slot"])
    if len(cells) != 256:
        raise ValueError(f"expected 256 scan cells, found {len(cells)}")
    if [row["scan_slot"] for row in cells] != list(range(256)):
        raise ValueError("scan slots are not a contiguous 0..255 chain")
    targets = [row for row in cells if "MC_REG_reg[9]" in row["instance_name"]]
    if len(targets) != 1:
        raise ValueError(f"expected one MC_REG[9] target, found {targets}")
    if any("KEY_REG" in row["instance_name"] for row in cells):
        raise ValueError("key register appears in scan path")
    return {
        "schema": "mc9-evaluator-scan-truth-v1",
        "scan_cell_count": len(cells),
        "target": {
            "rtl_signal": "aes_core.MC_REG[9]",
            "post_dft_instance": targets[0]["instance_name"],
            # scan_slot is the DFT path cell index. The testbench serializes
            # the last path cell first, so the anonymous scan-out index is the
            # reversed position used by Phase 0 discovery.
            "scan_slot": targets[0]["scan_slot"],
            "serialized_scan_out_index": len(cells) - 1 - targets[0]["scan_slot"],
        },
        "cells": cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = parse(args.scan_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"scan_cell_count": payload["scan_cell_count"], "target": payload["target"]}, indent=2))


if __name__ == "__main__":
    main()
