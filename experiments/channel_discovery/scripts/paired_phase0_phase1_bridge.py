"""Validate Phase 0 -> Phase 1 handoff on one persistent anonymous scan slot.

This is intentionally not a key-recovery experiment.  It keeps the generated
trial, key, scan permutation, and MC source fixed, then feeds the slot selected
from Phase 0 into a Phase 1-shaped observation document.  Ground truth is used
only for evaluator-side source identity and round-2 rendering checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_ROOT = ROOT / "channel_discovery"
sys.path.insert(0, str(DISCOVERY_ROOT / "scripts"))

from aes_ref import encrypt_with_trace  # noqa: E402
from scan_channel_generator_legacy import MC_COLUMNS, _bit  # noqa: E402


TRIAL_DIR = DISCOVERY_ROOT / "results" / "discovery_trials"


def load_campaign() -> list[dict]:
    return json.loads((TRIAL_DIR / "discovery_results.json").read_text())


def load_trial(trial_id: str) -> tuple[dict, dict, dict, dict]:
    anonymous = json.loads((TRIAL_DIR / f"{trial_id}.anonymous.json").read_text())
    ground_truth = json.loads((TRIAL_DIR / f"{trial_id}.ground_truth.json").read_text())
    discovery = next(row["discovery"] for row in load_campaign() if row["trial_id"] == trial_id)
    observation = json.loads((TRIAL_DIR / f"{trial_id}.observation.json").read_text())
    return anonymous, ground_truth, discovery, observation


def phase0_signature(anonymous: dict, slot: int) -> tuple[list[str], list[int]]:
    rows = [
        row for row in anonymous["observations"]
        if row["aes_started"] and row["schedule"] == "mc_capture"
    ]
    rows.sort(key=lambda row: int(row["query_id"]))
    if not rows:
        raise ValueError("trial has no Phase 0 mc_capture rows")
    base = int(rows[0]["scan_bits"][slot])
    plaintexts = [str(row["plaintext_hex"]) for row in rows]
    signature = [int(row["scan_bits"][slot]) ^ base for row in rows]
    return plaintexts, signature


def make_hypotheses(column: int) -> list[dict[str, object]]:
    if not 0 <= column < len(MC_COLUMNS):
        raise ValueError(f"invalid MC column: {column}")
    result = []
    for row in range(4):
        byte_index = 4 * column + row
        for bit in range(8):
            result.append({
                "hypothesis_id": f"MC_C{column}_BYTE{byte_index}_BIT{bit}",
                "stage": "MC",
                "column": column,
                "byte_index": byte_index,
                "bit_in_byte": bit,
                "bit_index": 8 * byte_index + bit,
            })
    return result


def round_signature(
    plaintexts: list[str],
    key: bytes,
    source: dict,
    round_index: int,
) -> list[int]:
    traces = [encrypt_with_trace(bytes.fromhex(point), key) for point in plaintexts]
    values = [
        _bit(trace["rounds"][round_index]["MC"], int(source["bit_index"]))
        for trace in traces
    ]
    base = values[0]
    return [value ^ base for value in values]


def run_positive(trial_id: str) -> dict[str, object]:
    anonymous, ground_truth, discovery, phase0_observation = load_trial(trial_id)
    selected_slot = int(phase0_observation["scan_slot"])
    ranked_slot = int(discovery["ranked_slots"][0]["scan_slot"])
    if selected_slot != ranked_slot:
        raise AssertionError("exported Phase 0 slot differs from discovery top-1")

    plaintexts, phase0_y = phase0_signature(anonymous, selected_slot)
    source = ground_truth["scan_sources"][selected_slot]
    key = bytes.fromhex(ground_truth["key_hex"])
    column = int(discovery["ranked_slots"][0]["closest_mc_column"])
    hypotheses = make_hypotheses(column)
    true_hypothesis = next(
        (hypothesis for hypothesis in hypotheses
         if int(hypothesis["bit_index"]) == int(source["bit_index"])),
        None,
    )

    # Round 1 is the exact Phase 0 raw signature.  Round 2 uses the same scan
    # slot/source identity with the next AES trace round, not a new FF location.
    phase1_round1_y = list(phase0_y)
    phase1_round2_y = round_signature(plaintexts, key, source, 2)
    phase1_document = {
        "schema": "anonymous-mc-phase1-observation-v1",
        "trial_id": trial_id,
        "scan_slot": selected_slot,
        "source_handoff": "phase0_selected_slot_reused",
        "reference_plaintext_hex": plaintexts[0],
        "rounds": {
            "1": {"capture_schedule": "mc_capture", "differential_signatures": phase1_round1_y},
            "2": {"capture_schedule": "mc_capture", "differential_signatures": phase1_round2_y},
        },
        "semantic_hypotheses": [{"stage": "MC", "column": column}],
    }

    common_queries_equal = phase0_y == phase1_round1_y
    source_is_mc = source["kind"] == "mc" and source["stage"] == "MC"
    same_source_identity = source_is_mc and int(source["scan_slot"]) == selected_slot
    same_round1_source = same_source_identity and int(source["round"]) == 1
    return {
        "trial_id": trial_id,
        "cohort": "positive",
        "phase0_selected_slot": selected_slot,
        "phase1_reused_slot": int(phase1_document["scan_slot"]),
        "slot_identity_preserved": selected_slot == int(phase1_document["scan_slot"]),
        "phase0_query_count": len(phase0_y),
        "phase0_raw_signature_reused": common_queries_equal,
        "common_query_signature_match_count": sum(a == b for a, b in zip(phase0_y, phase1_round1_y)),
        "common_query_signature_count": len(phase0_y),
        "round2_same_slot": int(phase1_document["scan_slot"]) == selected_slot,
        "ground_truth_same_mc_source_evaluation_only": same_source_identity,
        "ground_truth_round1_mc_source_evaluation_only": same_round1_source,
        "true_hypothesis_retained_evaluation_only": true_hypothesis is not None,
        "source_evaluation_only": {
            "source_id": source["source_id"],
            "kind": source["kind"],
            "stage": source["stage"],
            "round": source["round"],
            "bit_index": source["bit_index"],
        },
        "phase1_observation": phase1_document,
        "classification": "PASS" if all((
            selected_slot == int(phase1_document["scan_slot"]),
            common_queries_equal,
            same_round1_source,
            true_hypothesis is not None,
        )) else "FAIL",
    }


def run_negative(trial_id: str) -> dict[str, object]:
    row = next(item for item in load_campaign() if item["trial_id"] == trial_id)
    selected_slot = row["discovery"]["selected_slot"]
    return {
        "trial_id": trial_id,
        "cohort": "negative",
        "phase0_selected_slot": selected_slot,
        "handoff_attempted": selected_slot is not None,
        "classification": "PASS" if selected_slot is None else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive-limit", type=int, default=32)
    parser.add_argument("--negative-limit", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = load_campaign()
    positives = [row["trial_id"] for row in rows if row["cohort"] == "positive"][:args.positive_limit]
    negatives = [row["trial_id"] for row in rows if row["cohort"] == "negative"][:args.negative_limit]
    result = {
        "schema": "phase0-phase1-slot-handoff-v1",
        "purpose": "lightweight identity-preserving bridge; no key recovery",
        "conditions": {
            "same_trial": True,
            "same_key": True,
            "same_scan_stitching": True,
            "phase0_schedule": "mc_capture",
            "phase1_rounds": [1, 2],
            "phase1_round1_input": "raw_phase0_signature",
            "phase1_round2_input": "same_slot_next_trace_round_oracle_render",
            "ground_truth_used": "evaluator_only",
        },
        "positive": [run_positive(trial_id) for trial_id in positives],
        "negative": [run_negative(trial_id) for trial_id in negatives],
    }
    result["summary"] = {
        "positive_pass": sum(row["classification"] == "PASS" for row in result["positive"]),
        "positive_total": len(result["positive"]),
        "negative_pass": sum(row["classification"] == "PASS" for row in result["negative"]),
        "negative_total": len(result["negative"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
