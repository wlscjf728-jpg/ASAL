from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|")


def build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Python Defense Capability Matrix Report",
        "",
        "## Scope",
        "",
        "This report applies representative defense capability adapters to the existing Python AES-128 MC-channel oracle. It does not claim to reproduce the cited papers' RTL or netlist implementations. The attack core, frozen MC case, anonymous 256-cell Phase 0 scan model, 32 C0 MC hypotheses, and strict `SAT -> UNSAT` uniqueness rule are unchanged.",
        "",
        "## Pipeline Result",
        "",
        "| Condition | Access | Phase 0 | Attribution | Fixed | Adaptive | Final | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in summary["results"]:
        phase0 = item.get("phase0", {})
        attribution = item.get("attribution", {})
        fixed = item.get("fixed", {}).get("classification")
        adaptive = item.get("adaptive", {}).get("status")
        final = item.get("final", {}).get("classification")
        access = "allow" if item.get("condition_id") not in {"D6_invalid"} else "deny"
        discovery = phase0.get("status", "-")
        lines.append("| " + " | ".join([
            _cell(item["condition_id"]),
            access,
            _cell(discovery),
            _cell(attribution.get("status")),
            _cell(fixed),
            _cell(adaptive),
            _cell(final),
            _cell(item["attack_verdict"]),
        ]) + " |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `ATTACK_SUCCESS` means the final existing solver proof reached `SAT -> UNSAT`; a first model or hidden-key match alone is not sufficient.",
        "- `NO_ATTRIBUTABLE_CHANNEL` means the transformed observation could not be explained by the clean MC-function hypothesis family, even when Phase 0 produced an AES-dependent decoy candidate.",
        "- `BLOCKED_BY_POLICY` means access or an additional query was denied. In particular, D7 preserves fixed ambiguity and blocks the adaptive separator query.",
        "- `UNKNOWN` and timeout are not converted into success or defense success. The recorded matrix has no unresolved solver result.",
        "",
        "## Condition Notes",
        "",
        "| Condition | First blocked stage | Key evidence |",
        "|---|---|---|",
    ])
    for item in summary["results"]:
        condition = item["condition_id"]
        evidence = f"`results/{condition}/attack_result.json`, `results/{condition}/transform_audit.json`"
        lines.append(f"| {_cell(condition)} | {_cell(item.get('first_blocked_stage'))} | {evidence} |")
    lines.extend([
        "",
        "## Evidence and Trust Boundary",
        "",
        "Each condition directory contains attacker-visible captures/transcripts and a separate evaluator-only truth file. The attack artifacts do not contain the hidden key, MC9 label, physical mapping, or response-transform secret. Conditions with an unchanged differential transcript reuse the already completed Q128 fixed and Q131 adaptive solver checkpoints; the runner records this equivalence instead of silently copying a verdict.",
        "",
        "## Limitations",
        "",
        "This is a capability-boundary experiment over the established semantic oracle. D3 is DefScan-like response masking, D6 is DAF/SSA-style authorization, D7 is PASS-style pattern authorization, and D8 is a keyed response-hiding representative. The results do not establish universal security or insecurity of those named defenses, nor do they replace the separate EDA validation.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.input.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(summary))


if __name__ == "__main__":
    main()

