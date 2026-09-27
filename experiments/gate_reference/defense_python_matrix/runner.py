from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .adapters import apply_observation_transform, transform_capture
from .evaluator import aggregate_verdict, evaluate_correctness
from .model import DefenseCondition, StageResult
from .phase0 import run_phase0_discovery
from .policy import authorize_access, authorize_query
from .scan_bank import build_scan_bank, write_attack_capture
from .solver_bridge import classify_solver_result, run_existing_solver
from .transcript import build_q0_transcript


PHASE_B = "gate_reference/results/phase_b"
BASELINE_TRANSCRIPT = "gate_reference/results/phase_b/q128_mc_hypotheses_attack.json"
BASELINE_FIXED = "gate_reference/results/phase_b/q128_mc_hypothesis_solver_attack.json"
BASELINE_FINAL = "gate_reference/results/phase_b/q131_mc_hypothesis_solver_attack.json"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _public_manifests(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    extra = root / "gate_reference" / "inputs"
    return _json(extra / "phase0_queries.json"), _json(extra / "mc9_seed2_q128.json")


def _allowed_plaintexts(manifest: dict[str, Any]) -> set[str]:
    return {str(row["plaintext_hex"]) for row in manifest["queries"]}


def _same_observations(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("experiment", {}).get("hypotheses") == right.get("experiment", {}).get("hypotheses")
        and left.get("observations") == right.get("observations")
    )


def _reuse_or_solve(
    root: Path,
    transcript: dict[str, Any],
    output_path: Path,
    workers: int,
) -> tuple[dict[str, Any], bool]:
    baseline_path = root / BASELINE_TRANSCRIPT
    baseline_solver_path = root / BASELINE_FIXED
    baseline = _json(baseline_path)
    if _same_observations(transcript, baseline):
        result = copy.deepcopy(_json(baseline_solver_path))
        result["source_reused"] = str(baseline_solver_path)
        result["transcript_equivalent_to_baseline"] = True
        _write(output_path, result)
        return result, True
    transcript_path = output_path.with_name("fixed_transcript.json")
    _write(transcript_path, transcript)
    result = run_existing_solver(transcript_path, output_path, workers=workers)
    result["source_reused"] = ""
    result["transcript_equivalent_to_baseline"] = False
    _write(output_path, result)
    return result, False


def _reuse_final(root: Path, output_path: Path) -> dict[str, Any]:
    source = root / BASELINE_FINAL
    result = copy.deepcopy(_json(source))
    result["source_reused"] = str(source)
    result["transcript_equivalent_to_baseline"] = True
    _write(output_path, result)
    return result


def _expected_output_slot(condition: DefenseCondition) -> int | None:
    if condition.transform in {"identity", "clear_post_mc", "reset_capture", "round_mask_only", "round_and_mc_mask", "fixed_inversion"}:
        return 255
    if condition.transform in {"static_permutation", "epoch_permutation", "probe_permutation"}:
        visible = apply_observation_transform(1 << 255, condition, 0, 1)
        if visible.bit_count() == 1:
            return visible.bit_length() - 1
    return None


def _save_evaluator_truth(condition_dir: Path, condition: DefenseCondition, key: bytes, expected_slot: int | None) -> None:
    _write(condition_dir / "evaluator_truth.json", {
        "schema": "python-defense-evaluator-only-v1",
        "condition_id": condition.condition_id,
        "true_key_hex": key.hex(),
        "source_target_slot": 255,
        "source_target_bit": 9,
        "expected_output_slot": expected_slot,
        "semantic_label": "evaluator-only-target",
    })


def _result_base(condition: DefenseCondition) -> dict[str, Any]:
    return {
        "schema": "python-defense-capability-result-v1",
        "condition_id": condition.condition_id,
        "family": condition.family,
        "attack_input_truth_free": True,
        "stages": [],
        "first_blocked_stage": "",
    }


def _finish(result: dict[str, Any], stages: list[StageResult], condition_dir: Path) -> dict[str, Any]:
    result["stages"] = [
        {"stage": item.stage, "status": item.status, "reason": item.reason, "details": item.details or {}}
        for item in stages
    ]
    result["attack_verdict"] = aggregate_verdict(stages)
    for item in stages:
        if item.status in {"access_denied", "query_denied", "no_channel", "identity_unstable", "unresolved", "unknown", "timeout"}:
            result["first_blocked_stage"] = item.stage
            break
    _write(condition_dir / "attack_result.json", result)
    return result


def run_condition(condition: DefenseCondition, root: Path, workers: int = 1) -> dict[str, Any]:
    condition_dir = root / "gate_reference" / "defense_python_matrix" / "results" / condition.condition_id
    condition_dir.mkdir(parents=True, exist_ok=True)
    result = _result_base(condition)
    stages: list[StageResult] = []
    key_doc = _json(root / "gate_reference" / "inputs" / "hidden_key.evaluator.json")
    key = bytes.fromhex(str(key_doc["true_key_hex"]))
    _save_evaluator_truth(condition_dir, condition, key, _expected_output_slot(condition))

    auth_value = "invalid" if condition.authorization == "deny_access" else "valid"
    access_ok, access_reason = authorize_access(condition, auth_value)
    result["access"] = {"allowed": access_ok, "reason": access_reason}
    stages.append(StageResult("access", "pass" if access_ok else "access_denied", access_reason))
    if not access_ok:
        return _finish(result, stages, condition_dir)

    phase0_manifest, fixed_manifest = _public_manifests(root)
    allowed_fixed = _allowed_plaintexts(fixed_manifest)
    for row in phase0_manifest["queries"]:
        allowed, reason = authorize_query(
            condition, int(row["query_id"]), "phase0", str(row["plaintext_hex"]), allowed_fixed
        )
        if not allowed:
            result["policy"] = {"phase": "phase0", "query_id": row["query_id"], "reason": reason}
            stages.append(StageResult("phase0_query_authorization", "query_denied", reason))
            return _finish(result, stages, condition_dir)

    raw_phase0 = build_scan_bank(phase0_manifest["queries"], key)
    transformed_phase0, phase0_audit = transform_capture(raw_phase0["attack"], condition)
    transformed_repeat, repeat_audit = transform_capture(raw_phase0["repeat"], condition)
    transformed_no_start, no_start_audit = transform_capture(raw_phase0["no_start"], condition)
    phase0_capture = condition_dir / "phase0_scan.txt"
    repeat_capture = condition_dir / "phase0_repeat.txt"
    no_start_capture = condition_dir / "phase0_no_start.txt"
    write_attack_capture(transformed_phase0, phase0_capture)
    write_attack_capture(transformed_repeat, repeat_capture)
    write_attack_capture(transformed_no_start, no_start_capture)
    _write(condition_dir / "transform_audit.json", {
        "condition_id": condition.condition_id,
        "transform": condition.transform,
        "row_count": len(phase0_audit),
        "identity_stable": condition.transform not in {"epoch_permutation", "probe_permutation"},
        "audit": phase0_audit + repeat_audit + no_start_audit,
    })
    phase0 = run_phase0_discovery(phase0_capture, repeat_capture, no_start_capture)
    result["phase0"] = {
        "status": "pass" if phase0.get("final_selected_slot") else "no_channel",
        "candidate_count": phase0["aes_dependent_candidate_count"],
        "pre_round_candidate_count": phase0["pre_round_candidate_count"],
        "mc_aware_candidate_count": phase0["mc_aware_candidate_count_overlap_ge_3"],
        "selected_slot": (phase0.get("final_selected_slot") or {}).get("scan_out_index"),
        "selected": phase0.get("final_selected_slot"),
    }
    stages.append(StageResult("phase0_discovery", "pass" if phase0.get("final_selected_slot") else "no_channel", details=result["phase0"]))
    selected = phase0.get("final_selected_slot")
    identity_stable = condition.transform not in {"epoch_permutation", "probe_permutation"}
    attributable = bool(selected and phase0["mc_aware_candidate_count_overlap_ge_3"] > 0 and identity_stable)
    if not attributable:
        status = "identity_unstable" if not identity_stable else "no_channel"
        reason = "scan slot identity changes across probes" if not identity_stable else "no stable MC-aware candidate"
        result["attribution"] = {"status": status, "reason": reason}
        stages.append(StageResult("phase0_5_attribution", status, reason))
        return _finish(result, stages, condition_dir)

    selected_slot = int(selected["scan_out_index"])
    raw_fixed = build_scan_bank(fixed_manifest["queries"], key)
    transformed_fixed, fixed_audit = transform_capture(raw_fixed["attack"], condition)
    fixed_transcript = build_q0_transcript(transformed_fixed, fixed_manifest, selected_slot)
    _write(condition_dir / "fixed_transcript.json", fixed_transcript)
    result["attribution"] = {
        "status": "pass",
        "selected_slot": selected_slot,
        "hypothesis_count": len(fixed_transcript["experiment"]["hypotheses"]),
        "identity_stable": identity_stable,
    }
    stages.append(StageResult("phase0_5_attribution", "pass", details=result["attribution"]))
    fixed_path = condition_dir / "fixed_solver.json"
    fixed_solver, transcript_reused = _reuse_or_solve(root, fixed_transcript, fixed_path, workers)
    fixed_classification = classify_solver_result(fixed_solver)
    result["fixed"] = {
        "classification": fixed_classification,
        "solver": fixed_solver,
        "transcript_equivalent_to_baseline": transcript_reused,
    }
    stages.append(StageResult("fixed_recovery", fixed_classification))
    if fixed_classification == "full_key_unique":
        result["adaptive"] = {"allowed": True, "required": False, "status": "not_required"}
        result["final"] = {"classification": fixed_classification, "solver": fixed_solver}
        stages.append(StageResult("final", fixed_classification))
        return _finish(result, stages, condition_dir)
    if fixed_classification == "inconsistent":
        result["attribution"] = {
            "status": "no_channel",
            "reason": "all MC-function hypotheses are inconsistent with the visible transcript",
            "selected_slot": selected_slot,
        }
        stages.append(StageResult("phase0_5_attribution", "no_channel", result["attribution"]["reason"]))
        return _finish(result, stages, condition_dir)
    if fixed_classification != "ambiguity":
        result["adaptive"] = {"allowed": condition.adaptive_allowed, "status": "unresolved"}
        stages.append(StageResult("adaptive", "unresolved", "fixed solver did not produce a usable ambiguity"))
        return _finish(result, stages, condition_dir)

    separator = str(_json(root / "gate_reference" / "inputs" / "frozen_case.json")["historical_separator_hex"])
    allowed, reason = authorize_query(condition, 0, "adaptive", separator, allowed_fixed)
    result["adaptive"] = {"allowed": allowed and condition.adaptive_allowed, "separator_probe": separator, "reason": reason}
    if not allowed or not condition.adaptive_allowed:
        stages.append(StageResult("adaptive_query_authorization", "query_denied", reason or "adaptive_not_allowed"))
        result["final"] = {"classification": fixed_classification, "solver": fixed_solver}
        return _finish(result, stages, condition_dir)
    if not transcript_reused:
        stages.append(StageResult("adaptive", "unresolved", "fresh adaptive transcript generation is not available for a changed relation"))
        return _finish(result, stages, condition_dir)
    final_solver = _reuse_final(root, condition_dir / "final_solver.json")
    final_classification = classify_solver_result(final_solver)
    result["adaptive"]["status"] = "completed_from_validated_closed_loop"
    result["final"] = {"classification": final_classification, "solver": final_solver}
    stages.append(StageResult("adaptive", "pass"))
    stages.append(StageResult("final", final_classification))
    return _finish(result, stages, condition_dir)


def run_matrix(config_path: Path, root: Path, workers: int = 1) -> dict[str, Any]:
    from .model import load_conditions

    conditions = load_conditions(config_path)
    results = []
    for condition in conditions:
        item = run_condition(condition, root, workers=workers)
        truth = _json(root / "gate_reference" / "defense_python_matrix" / "results" / condition.condition_id / "evaluator_truth.json")
        _write(root / "gate_reference" / "defense_python_matrix" / "results" / condition.condition_id / "evaluator_correctness.json", evaluate_correctness(item, truth))
        results.append(item)
    summary = {
        "schema": "python-defense-capability-matrix-summary-v1",
        "case_reference": "frozen_mc_case",
        "condition_count": len(results),
        "results": [
            {
                "condition_id": item["condition_id"],
                "family": item["family"],
                "attack_verdict": item["attack_verdict"],
                "first_blocked_stage": item["first_blocked_stage"],
                "phase0": item.get("phase0", {}),
                "attribution": item.get("attribution", {}),
                "fixed": {"classification": item.get("fixed", {}).get("classification")},
                "adaptive": item.get("adaptive", {}),
                "final": {"classification": item.get("final", {}).get("classification")},
            }
            for item in results
        ],
    }
    output = root / "gate_reference" / "defense_python_matrix" / "results" / "defense_matrix_summary.json"
    _write(output, summary)
    return summary

