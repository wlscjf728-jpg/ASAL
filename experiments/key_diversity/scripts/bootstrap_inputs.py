"""Create the frozen evaluator key manifest for the diversity campaign."""
from __future__ import annotations

import argparse
from pathlib import Path

from key_diversity_common import ROOT, generate_new_key_rows, write_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output", type=Path, default=ROOT / "inputs/evaluator_keys.csv")
    args = parser.parse_args()
    rows = generate_new_key_rows(args.seed, args.count)
    write_csv(
        args.output if args.output.is_absolute() else ROOT / args.output,
        rows,
        ["key_id", "key_hex", "key_sha256", "generation_seed", "generation_index", "evaluator_only"],
    )
    print(f"generated_keys={len(rows)} output={args.output}")


if __name__ == "__main__":
    main()
