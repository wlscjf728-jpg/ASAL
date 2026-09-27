#!/usr/bin/env python3
"""Render portable PNG evidence panels from the Verdi marker streams."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/verdi/figures"


FUNCTIONAL = re.compile(
    r"(?P<time>\d+) functional query=(?P<query>\d+) schedule=(?P<schedule>\d+) "
    r"target_q=(?P<target>[01]) scan_out=(?P<scan>[01])"
)
SHIFT = re.compile(
    r"(?P<time>\d+) walking_one count=(?P<count>\d+) scan_in=(?P<in>[01]) "
    r"scan_out=(?P<out>[01]) target_q=(?P<target>[01])"
)


def rows(path: Path, pattern: re.Pattern[str]):
    result = []
    for line in path.read_text().splitlines():
        match = pattern.search(line)
        if match:
            result.append({key: int(value) for key, value in match.groupdict().items()})
    return result


def plot_functional(marker: Path, output: Path, title: str) -> None:
    data = rows(marker, FUNCTIONAL)
    if not data:
        raise SystemExit(f"no functional markers in {marker}")
    with tempfile.TemporaryDirectory() as temp:
        data_path = Path(temp) / "functional.dat"
        data_path.write_text("\n".join(f"{r['query']} {r['schedule']} {r['target']} {r['scan']}" for r in data) + "\n")
        script = Path(temp) / "plot.gp"
        script.write_text("\n".join([
            "set terminal png size 1200,700",
            f"set output '{output}'",
            f"set title '{title}'",
            "set xlabel 'query / capture schedule'",
            "set ylabel 'observed bit'",
            "set yrange [-0.15:1.15]",
            "set grid ytics",
            f"plot '{data_path}' using ($1*4+$2):3 with points pt 7 ps 1.4 title 'target Q', \\",
            f"     '{data_path}' using ($1*4+$2):4 with points pt 5 ps 1.2 title 'scan out'",
        ]) + "\n")
        subprocess.run(["gnuplot", str(script)], check=True)


def plot_shift(marker: Path, output: Path) -> None:
    data = rows(marker, SHIFT)
    if not data:
        raise SystemExit(f"no walking-one markers in {marker}")
    with tempfile.TemporaryDirectory() as temp:
        data_path = Path(temp) / "shift.dat"
        data_path.write_text("\n".join(f"{r['count']} {r['in']} {r['out']} {r['target']}" for r in data) + "\n")
        script = Path(temp) / "plot.gp"
        script.write_text("\n".join([
            "set terminal png size 1200,700",
            f"set output '{output}'",
            "set title 'Scan shift identity: walking-one marker stream'",
            "set xlabel 'shift count'",
            "set ylabel 'bit'",
            "set yrange [-0.15:1.15]",
            "set grid ytics",
            f"plot '{data_path}' using 1:2 with steps title 'scan in', \\",
            f"     '{data_path}' using 1:3 with steps title 'scan out', \\",
            f"     '{data_path}' using 1:4 with steps title 'target Q'",
        ]) + "\n")
        subprocess.run(["gnuplot", str(script)], check=True)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plot_functional(
        ROOT / "results/verdi/phase0_mc_slot_discovery.markers.txt",
        OUT / "phase0_timing.png",
        "Phase 0: MC/update/post timing and selected slot",
    )
    plot_functional(
        ROOT / "results/verdi/phase1_q30_depth2.markers.txt",
        OUT / "round_slot_identity.png",
        "Phase 1: round-1/round-2 selected slot identity",
    )
    plot_functional(
        ROOT / "results/verdi/phase2_separator.markers.txt",
        OUT / "adaptive_separator.png",
        "Phase 2: historical separator scan response",
    )
    plot_shift(
        ROOT / "results/verdi/scan_shift_identity.markers.txt",
        OUT / "scan_shift_identity.png",
    )
    print(f"rendered {len(list(OUT.glob('*.png')))} PNG evidence panels under {OUT}")


if __name__ == "__main__":
    main()
