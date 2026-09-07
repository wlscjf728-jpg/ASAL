"""Summarize and audit the key-diversity JSONL result stream."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from key_diversity_common import ROOT, read_yaml, write_atomic
from key_diversity_campaign import RESULT_SCHEMA, load_campaign_config, rooted


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("schema") == RESULT_SCHEMA and row.get("state") == "terminal":
            rows.append(row)
    return rows


def summarize(raw_path: Path, expected: int = 80) -> dict[str, Any]:
    rows = load_rows(raw_path)
    run_ids = [row.get("run_id") for row in rows]
    duplicates = sorted(run_id for run_id, count in Counter(run_ids).items() if count > 1)
    counts = Counter(row.get("terminal_classification", "MISSING") for row in rows)
    by_tap: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_tap[row["tap"]["candidate_id"]].append(row)

    per_tap = {}
    for candidate_id, tap_rows in sorted(by_tap.items()):
        fixed_nuniq = [
            int(row["fixed_unique_query_count"])
            for row in tap_rows
            if row.get("fixed_unique_query_count") is not None
        ]
        adaptive_counts = [int(row.get("adaptive_query_count", 0)) for row in tap_rows]
        per_tap[candidate_id] = {
            "runs": len(tap_rows),
            "counts": dict(Counter(row["terminal_classification"] for row in tap_rows)),
            "fixed_nuniq_median": statistics.median(fixed_nuniq) if fixed_nuniq else None,
            "fixed_nuniq_min": min(fixed_nuniq) if fixed_nuniq else None,
            "fixed_nuniq_max": max(fixed_nuniq) if fixed_nuniq else None,
            "adaptive_query_median": statistics.median(adaptive_counts) if adaptive_counts else None,
        }

    return {
        "schema": "asal-key-diversity-summary-v1",
        "expected_runs": expected,
        "terminal_records": len(rows),
        "all_terminal": len(rows) == expected and not duplicates,
        "duplicate_run_ids": duplicates,
        "counts": dict(counts),
        "per_tap": per_tap,
        "key_ids": sorted({row.get("key_id") for row in rows}),
        "tap_ids": sorted({row.get("tap", {}).get("tap_id") for row in rows}),
    }


def write_report(summary: dict[str, Any], output: Path) -> None:
    counts = summary["counts"]
    lines = [
        "# ASAL AES-128 Master-Key Diversity Validation",
        "",
        "## Scope",
        "",
        "This isolated validation changes only the AES-128 master key. It evaluates four pre-registered post-MC one-bit taps across twenty new deterministic keys, for 80 key/tap runs. The AES model, differential reference plaintext, shared query schedule, temporal depth `d=2`, Z3 encoding, and SAT-to-UNSAT uniqueness rule are inherited from the copied Attack 8 implementation.",
        "",
        "## Solver boundary",
        "",
        "The evaluator uses the secret key to generate oracle observations and to perform an external sanity check. Before every Z3 call, `true_key_hex` is removed from the document. A run is successful only when the first solve is `SAT` and the second solve with `K != K_hat` is `UNSAT`; evaluator-key equality alone is not a success criterion.",
        "",
        "## Tap selection",
        "",
        "The repository audit found the 128-entry MC candidate map but no all-128 per-position `N_uniq` artifact. Therefore taps were frozen by a result-independent structural fallback: MC bit-index ranks 0, 42, 85, and 127, corresponding to `MC_0`, `MC_42`, `MC_85`, and `MC_127` in four distinct MC columns. This limitation is recorded rather than presented as an `N_uniq`-based selection.",
        "",
        "## Results",
        "",
        f"- Expected runs: **{summary['expected_runs']}**",
        f"- Terminal records: **{summary['terminal_records']}**",
        f"- Complete and duplicate-free: **{summary['all_terminal']}**",
        f"- Fixed-query unique: **{counts.get('FIXED_UNIQUE', 0)}**",
        f"- Adaptive unique: **{counts.get('ADAPTIVE_UNIQUE', 0)}**",
        f"- Proven non-recovery: **{counts.get('PROVEN_NON_RECOVERY', 0)}**",
        f"- Unknown: **{counts.get('UNKNOWN', 0)}**",
        f"- Model inconsistent: **{counts.get('MODEL_INCONSISTENT', 0)}**",
        "",
        "| Tap | Runs | Fixed unique | Adaptive unique | Non-recovery | Unknown | Fixed N_uniq median | Fixed N_uniq range |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for tap, data in summary["per_tap"].items():
        tap_counts = data["counts"]
        nuniq_range = (
            f"{data['fixed_nuniq_min']}–{data['fixed_nuniq_max']}"
            if data["fixed_nuniq_min"] is not None else "-"
        )
        lines.append(
            f"| {tap} | {data['runs']} | {tap_counts.get('FIXED_UNIQUE', 0)} | "
            f"{tap_counts.get('ADAPTIVE_UNIQUE', 0)} | {tap_counts.get('PROVEN_NON_RECOVERY', 0)} | "
            f"{tap_counts.get('UNKNOWN', 0)} | {data['fixed_nuniq_median'] or '-'} | {nuniq_range} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "If all 80 runs are fixed or adaptive unique, the original three-key result is supported as key-diverse over this 20-key sample, but not as a universal theorem. If convergence varies by key, that is reported as key-dependent query efficiency. Any `UNKNOWN` remains unresolved and is not converted to ambiguity or success. `PROVEN_NON_RECOVERY` means the adaptive separator search proved observational non-recovery under the configured unrestricted plaintext model.",
        "",
        "## Evidence",
        "",
        "- Raw terminal results: `results/raw_runs.jsonl`",
        "- Per-solve checkpoints: `results/checkpoints.jsonl`",
        "- Frozen taps: `configs/representative_post_mc_taps.csv`",
        "- Evaluator-only key manifest: `inputs/evaluator_keys.csv`",
        "- Source and selection audit: `reference/source_manifest.json`",
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "configs/key_diversity.yaml"))
    parser.add_argument("--verify-complete", action="store_true")
    args = parser.parse_args()
    config = load_campaign_config(args.config)
    raw = rooted(config["paths"]["raw_results"])
    summary = summarize(raw)
    write_atomic(rooted(config["paths"]["summary"]), summary)
    write_report(summary, rooted(config["paths"]["report"]))
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.verify_complete and not summary["all_terminal"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
