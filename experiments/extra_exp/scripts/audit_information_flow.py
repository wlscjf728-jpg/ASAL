#!/usr/bin/env python3
"""Audit the attacker/evaluator artifact boundary for the MC9 EDA run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ATTACKER_FILES = [
    ROOT / "results/phase_b/phase0_gate_scan_attack.txt",
    ROOT / "results/phase_b/phase0_heldout_gate_scan_attack.txt",
    ROOT / "results/phase_b/q128_mc_hypotheses_attack.json",
    ROOT / "results/phase_b/q129_mc_hypotheses_attack.json",
    ROOT / "results/phase_b/q130_mc_hypotheses_attack.json",
    ROOT / "results/phase_b/q129_mc_hypotheses_attack_pruned.json",
    ROOT / "results/phase_b/q130_mc_hypotheses_attack_closed_loop.json",
    ROOT / "results/phase_b/q130_mc_hypotheses_attack_pruned.json",
    ROOT / "results/phase_b/q131_mc_hypotheses_attack_closed_loop.json",
    ROOT / "results/phase_b/q131_mc_hypotheses_attack_pruned.json",
]

EVALUATOR_FILES = [
    ROOT / "inputs/hidden_key.evaluator.json",
    ROOT / "results/evaluator/target_mapping.json",
    ROOT / "results/evaluator/scan_path.rpt",
]

# These are evaluator truth or implementation identifiers. A selected numeric
# slot is allowed after Phase 0; the underlying target identity is not.
FORBIDDEN_ATTACK_TOKENS = (
    "a66f651322597191ab9f8f8af4c2db61",
    "aes_core/MC_REG_reg[9]",
    "aes_core.MC_REG[9]",
    "n10857",
    "true_key_hex",
    "post_dft_instance",
    "target_mapping.json",
    "scan_path.rpt",
    '"evaluator"',
    "MC_9",
    "MC9",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    missing = [str(path) for path in ATTACKER_FILES + EVALUATOR_FILES if not path.exists()]
    if missing:
        raise SystemExit("missing required artifact(s): " + ", ".join(missing))

    violations = []
    attacker_records = []
    for path in ATTACKER_FILES:
        text = path.read_text(errors="replace")
        hits = [token for token in FORBIDDEN_ATTACK_TOKENS if token in text]
        attacker_records.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size})
        violations.extend({"path": str(path.relative_to(ROOT)), "token": token} for token in hits)

    evaluator_records = [
        {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in EVALUATOR_FILES
    ]
    result = {
        "schema": "mc9-information-flow-audit-v1",
        "status": "PASS" if not violations else "FAIL",
        "attacker_files": attacker_records,
        "evaluator_only_files": evaluator_records,
        "forbidden_attack_tokens": list(FORBIDDEN_ATTACK_TOKENS),
        "violations": violations,
        "selected_numeric_slot_allowed": True,
        "semantic_MC9_not_in_attack_path": True,
    }
    output = ROOT / "results/evaluator/information_flow_audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
