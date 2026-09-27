from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .transcript import build_q0_transcript


ROOT = Path(__file__).resolve().parents[2]
SOLVER = ROOT / "gate_reference" / "scripts" / "run_mc_hypothesis_solver.py"


def run_existing_solver(transcript_path: Path, output_path: Path, workers: int = 1) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(SOLVER),
        "--input", str(transcript_path),
        "--output", str(output_path),
        "--workers", str(max(1, int(workers))),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        combined = (completed.stdout or "") + (completed.stderr or "")
        if "all hypotheses are inconsistent" in combined:
            transcript = json.loads(transcript_path.read_text())
            result = {
                "schema": "mc9-anonymous-function-attribution-solver-v1",
                "input_transcript": str(transcript_path),
                "sbox_encoding": "uf_axiom",
                "initial_hypothesis_count": len(transcript.get("experiment", {}).get("hypotheses", [])),
                "branch_consistency": [],
                "surviving_hypotheses": [],
                "surviving_hypothesis_count": 0,
                "joint_key_uniqueness": {
                    "first_result": "unsat",
                    "second_result": "not_run",
                    "classification": "inconsistent",
                    "unknown": False,
                    "timeout": False,
                    "reason": "all hypotheses are inconsistent",
                },
                "attack_used_ground_truth_mc9": False,
                "attack_used_hidden_key": False,
                "solver_process_output": combined[-2000:],
            }
            output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            return result
        raise RuntimeError(f"solver failed ({completed.returncode}): {combined[-2000:]}")
    return json.loads(output_path.read_text())


def classify_solver_result(result: dict[str, Any]) -> str:
    joint = result.get("joint_key_uniqueness", result)
    first = str(joint.get("first_result", "")).lower()
    second = str(joint.get("second_result", "")).lower()
    if first == "sat" and second == "unsat":
        return "full_key_unique"
    if first == "sat" and second == "sat":
        return "ambiguity"
    if first == "sat" and second == "unknown":
        return "unresolved"
    if first == "unknown" or second == "unknown":
        return "unresolved"
    if first == "unsat":
        return "inconsistent"
    return "invalid_solver_result"

