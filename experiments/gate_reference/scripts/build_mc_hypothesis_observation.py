#!/usr/bin/env python3
"""Build an attacker-visible MC-column hypothesis transcript from scan vectors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


C0_SOURCE_BYTES = [0, 5, 10, 15]
C0_OUTPUT_BITS = list(range(32))


def parse_capture(path: Path) -> dict[tuple[int, int], int]:
    rows: dict[tuple[int, int], int] = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 4:
            query_id, schedule, _evaluator_probe, vector = fields
        elif len(fields) == 3:
            query_id, schedule, vector = fields
        else:
            continue
        rows[(int(query_id), int(schedule))] = int(vector, 16)
    if not rows:
        raise ValueError(f"no scan rows in {path}")
    return rows


def parse_queries(path: Path) -> dict[int, bytes]:
    queries: dict[int, bytes] = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        query_id, plaintext = fields
        queries[int(query_id)] = bytes.fromhex(plaintext)
    if 0 not in queries:
        raise ValueError("query manifest must contain reference query 0")
    return queries


def hypotheses() -> list[dict[str, object]]:
    result = []
    for index, bit_index in enumerate(C0_OUTPUT_BITS):
        result.append({
            "hypothesis_id": f"h{index:02d}",
            "stage": "MC",
            "bit_index": bit_index,
            "column": "C0",
            "source_byte_support": C0_SOURCE_BYTES,
            "row": bit_index // 8,
            "bit_in_byte": bit_index % 8,
        })
    return result


def load_hypotheses(path: Path | None) -> list[dict[str, object]]:
    if path is None:
        return hypotheses()
    payload = json.loads(path.read_text())
    if "surviving_hypotheses" in payload:
        result = payload["surviving_hypotheses"]
    elif "hypotheses" in payload:
        result = payload["hypotheses"]
    elif "experiment" in payload and "hypotheses" in payload["experiment"]:
        result = payload["experiment"]["hypotheses"]
    else:
        raise ValueError(f"no hypothesis list in {path}")
    if not result:
        raise ValueError("cannot build an empty hypothesis transcript")
    return result


def build(capture: Path, queries: Path, slot: int, hypothesis_file: Path | None = None) -> dict[str, object]:
    rows = parse_capture(capture)
    points = parse_queries(queries)
    hs = load_hypotheses(hypothesis_file)
    if any("MC_9" in json.dumps(item) or "MC9" in json.dumps(item) for item in hs):
        raise ValueError("ground-truth MC9 label is not allowed in attacker hypotheses")
    observations = []
    reference = rows[(0, 1)]
    for query_id in sorted(points):
        rounds = {}
        for round_id, schedule in ((1, 1), (2, 3)):
            observed = (rows[(query_id, schedule)] >> slot) & 1
            base = ((reference if schedule == 1 else rows[(0, schedule)]) >> slot) & 1
            rounds[str(round_id)] = {"differential": observed ^ base}
        observations.append({
            "query_id": query_id,
            "plaintext_hex": points[query_id].hex(),
            "rounds": rounds,
        })
    return {
        "schema": "aes-sparse-gate-hypothesis-bridge-v1",
        "experiment": {
            "depth": 2,
            "mode": "differential",
            "base_query_id": 0,
            "hypothesis_family": "MC_output_bit_within_C0",
            "hypotheses": hs,
            "source": {
                "scan_slot": slot,
                "schedule_to_round": {"1": 1, "3": 2},
                "anonymous_input": True,
                "ground_truth_semantic_label_provided": False,
            },
        },
        "observations": observations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hypotheses-from", type=Path)
    args = parser.parse_args()
    doc = build(args.capture, args.queries, args.slot, args.hypotheses_from)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "query_count": len(doc["observations"]),
        "hypothesis_count": len(doc["experiment"]["hypotheses"]),
        "slot": args.slot,
    }, indent=2))


if __name__ == "__main__":
    main()
