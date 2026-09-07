from __future__ import annotations

from typing import Any


C0_SOURCE_BYTES = [0, 5, 10, 15]


def hypotheses() -> list[dict[str, Any]]:
    return [
        {
            "hypothesis_id": f"h{bit_index:02d}",
            "stage": "MC",
            "bit_index": bit_index,
            "column": "C0",
            "source_byte_support": C0_SOURCE_BYTES,
            "row": bit_index // 8,
            "bit_in_byte": bit_index % 8,
        }
        for bit_index in range(32)
    ]


def _rows(capture: Any) -> list[dict[str, Any]]:
    if isinstance(capture, dict):
        capture = capture.get("rows", capture.get("attack", capture))
    if not isinstance(capture, list):
        raise ValueError("capture must be a list of anonymous scan rows")
    return capture


def _queries(manifest: dict[str, Any]) -> dict[int, str]:
    result = {}
    for row in manifest.get("queries", []):
        query_id = int(row["query_id"])
        plaintext = str(row["plaintext_hex"])
        if len(bytes.fromhex(plaintext)) != 16:
            raise ValueError("query plaintext must be 16 bytes")
        result[query_id] = plaintext
    if 0 not in result:
        raise ValueError("query manifest must contain reference query 0")
    return result


def build_q0_transcript(capture: Any, query_manifest: dict[str, Any], slot: int) -> dict[str, Any]:
    points = _queries(query_manifest)
    by_key = {}
    for row in _rows(capture):
        query_id = int(row["query_id"])
        schedule = int(row.get("capture_schedule", row.get("schedule")))
        by_key[(query_id, schedule)] = int(str(row.get("scan_vector_hex", row.get("vector"))), 16)
    required = {(query_id, schedule) for query_id in points for schedule in (1, 3)}
    missing = sorted(required - set(by_key))
    if missing:
        raise ValueError(f"capture is missing round observations: {missing[:3]}")

    observations = []
    for query_id in sorted(points):
        rounds = {}
        for round_id, schedule in ((1, 1), (2, 3)):
            current = (by_key[(query_id, schedule)] >> slot) & 1
            reference = (by_key[(0, schedule)] >> slot) & 1
            rounds[str(round_id)] = {"differential": current ^ reference}
        observations.append({
            "query_id": query_id,
            "plaintext_hex": points[query_id],
            "rounds": rounds,
        })
    return {
        "schema": "aes-sparse-gate-hypothesis-bridge-v1",
        "experiment": {
            "depth": 2,
            "mode": "differential",
            "base_query_id": 0,
            "hypothesis_family": "MC_output_bit_within_C0",
            "hypotheses": hypotheses(),
            "source": {
                "scan_slot": int(slot),
                "schedule_to_round": {"1": 1, "3": 2},
                "anonymous_input": True,
                "ground_truth_semantic_label_provided": False,
            },
        },
        "observations": observations,
    }

