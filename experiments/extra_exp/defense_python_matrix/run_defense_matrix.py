from __future__ import annotations

import argparse
from pathlib import Path

from .runner import run_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    summary = run_matrix(args.config, root, workers=args.workers)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        import json
        args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print({"condition_count": summary["condition_count"], "output": str(args.output or root / "extra_exp/defense_python_matrix/results/defense_matrix_summary.json")})


if __name__ == "__main__":
    main()

