"""Track the existing MC9 anonymous channel after hidden scan permutations.

This module is deliberately independent of the MC9 RTL, VCS, evaluator key,
and Z3 solver.  It consumes only the copied attack-side Phase 0 capture and
implements the host-side behavioral reacquisition experiment.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

SCAN_BITS = 256


def parse_capture(path: Path) -> dict[tuple[int, int], int]:
    """Parse the attack-side ``query schedule vector`` capture format."""
    rows: dict[tuple[int, int], int] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"{path}:{line_number}: expected 3 fields")
        query_id, schedule, vector_hex = fields
        if len(vector_hex) != SCAN_BITS // 4:
            raise ValueError(
                f"{path}:{line_number}: expected 64 hex digits, got {len(vector_hex)}"
            )
        key = (int(query_id), int(schedule))
        if key in rows:
            raise ValueError(f"{path}:{line_number}: duplicate row {key}")
        rows[key] = int(vector_hex, 16)
    return rows


def parse_queries(path: Path) -> dict[int, str]:
    queries: dict[int, str] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 2:
            raise ValueError(f"{path}:{line_number}: expected query id and plaintext")
        query_id, plaintext_hex = fields
        queries[int(query_id)] = plaintext_hex
    return queries


def make_permutation(seed: int | None) -> list[int]:
    permutation = list(range(SCAN_BITS))
    if seed is not None:
        random.Random(seed).shuffle(permutation)
    return permutation


def permute_vector(vector: int, old_to_new: list[int]) -> int:
    """Apply an evaluator-only old-slot -> new-slot permutation."""
    output = 0
    remaining = vector
    while remaining:
        least_bit = remaining & -remaining
        old_slot = least_bit.bit_length() - 1
        output |= 1 << old_to_new[old_slot]
        remaining ^= least_bit
    return output


def fingerprint(
    rows_by_query: dict[int, int],
    slot: int,
    query_ids: Iterable[int],
) -> tuple[int, ...]:
    query_ids = list(query_ids)
    if not query_ids or query_ids[0] != 0:
        raise ValueError("fingerprint query IDs must start with reference query 0")
    reference = (rows_by_query[0] >> slot) & 1
    return tuple(((rows_by_query[q] >> slot) & 1) ^ reference for q in query_ids)


def find_matches(
    rows_by_query: dict[int, int],
    expected: tuple[int, ...],
    query_ids: Iterable[int],
) -> list[int]:
    return [
        slot
        for slot in range(SCAN_BITS)
        if fingerprint(rows_by_query, slot, query_ids) == expected
    ]


def reacquire(
    rows_by_query: dict[int, int],
    expected_fingerprint: tuple[int, ...],
    initial_probe_ids: list[int],
    candidate_probe_ids: list[int],
    evaluator_current_slot: int | None,
    validation_probe_ids: list[int] | None = None,
) -> dict:
    """Run tracker-side matching and evaluator-side correctness annotation."""
    used = list(initial_probe_ids)
    matches = find_matches(rows_by_query, expected_fingerprint[: len(used)], used)
    initial_matches = list(matches)
    for query_id in candidate_probe_ids:
        if len(matches) <= 1:
            break
        used.append(query_id)
        matches = find_matches(rows_by_query, expected_fingerprint[: len(used)], used)

    selected_slot = matches[0] if len(matches) == 1 else None
    validation_results = []
    if selected_slot is not None and validation_probe_ids:
        for query_id in validation_probe_ids:
            observed = ((rows_by_query[query_id] >> selected_slot) & 1) ^ ((rows_by_query[0] >> selected_slot) & 1)
            validation_results.append({
                "query_id": query_id,
                "observed": observed,
                "expected": expected_fingerprint[query_id],
                "match": observed == expected_fingerprint[query_id],
            })
    validation_passed = selected_slot is not None and all(
        row["match"] for row in validation_results
    )
    tracking_success = selected_slot is not None and validation_passed
    return {
        "initial_probe_count": len(initial_probe_ids),
        "initial_match_count": len(initial_matches),
        "initial_matches": initial_matches,
        "probe_count": len(used),
        "validation_probe_count": len(validation_probe_ids or []),
        "validation_results": validation_results,
        "validation_passed": validation_passed,
        "additional_probe_count": len(used) - len(initial_probe_ids),
        "final_match_count": len(matches),
        "final_matches": matches,
        "selected_slot": selected_slot,
        "evaluator_current_slot": evaluator_current_slot,
        "tracking_success": tracking_success,
        "tracking_correct": (
            tracking_success
            and evaluator_current_slot is not None
            and selected_slot == evaluator_current_slot
        ),
    }


def transformed_rows(
    capture_rows: dict[tuple[int, int], int], schedule: int, permutation: list[int]
) -> dict[int, int]:
    return {
        query_id: permute_vector(capture_rows[(query_id, schedule)], permutation)
        for query_id in range(65)
    }


def stable_scenario(
    capture_rows: dict[tuple[int, int], int],
    expected_fingerprint: tuple[int, ...],
    initial_probe_ids: list[int],
    candidate_probe_ids: list[int],
    validation_probe_ids: list[int],
    payload_query_ids: list[int],
    interval: int,
    seed: int,
) -> dict:
    epochs: list[dict] = []
    for epoch_index in range(0, len(payload_query_ids), interval):
        payload = payload_query_ids[epoch_index : epoch_index + interval]
        permutation = make_permutation(seed + epoch_index // interval)
        current_rows = transformed_rows(capture_rows, 1, permutation)
        result = reacquire(
            current_rows,
            expected_fingerprint,
            initial_probe_ids,
            candidate_probe_ids,
            permutation[255],
            validation_probe_ids=validation_probe_ids,
        )
        result.update(
            {
                "epoch_index": epoch_index // interval,
                "payload_query_start": payload[0],
                "payload_query_end": payload[-1],
                "payload_query_count": len(payload),
            }
        )
        epochs.append(result)

    return {
        "mode": "epoch_stable",
        "refresh_interval_payload_queries": interval,
        "epoch_count": len(epochs),
        "tracking_accuracy": sum(e["tracking_correct"] for e in epochs) / len(epochs),
        "all_epochs_correct": all(e["tracking_correct"] for e in epochs),
        "collision_epoch_count": sum(e["initial_match_count"] > 1 for e in epochs),
        "average_probe_count": sum(e["probe_count"] for e in epochs) / len(epochs),
        "epochs": epochs,
    }


def identity_scenario(
    capture_rows: dict[tuple[int, int], int],
    expected_fingerprint: tuple[int, ...],
    initial_probe_ids: list[int],
    candidate_probe_ids: list[int],
    validation_probe_ids: list[int],
) -> dict:
    identity = make_permutation(None)
    current_rows = transformed_rows(capture_rows, 1, identity)
    epoch = reacquire(
        current_rows,
        expected_fingerprint,
        initial_probe_ids,
        candidate_probe_ids,
        255,
        validation_probe_ids=validation_probe_ids,
    )
    return {
        "mode": "identity",
        "epoch_count": 1,
        "tracking_accuracy": 1.0 if epoch["tracking_correct"] else 0.0,
        "all_epochs_correct": epoch["tracking_correct"],
        "collision_epoch_count": int(epoch["initial_match_count"] > 1),
        "average_probe_count": epoch["probe_count"],
        "epochs": [epoch],
    }


def independent_probe_control(
    capture_rows: dict[tuple[int, int], int],
    expected_fingerprint: tuple[int, ...],
    initial_probe_ids: list[int],
    candidate_probe_ids: list[int],
    validation_probe_ids: list[int],
    repetitions: int,
    seed: int,
) -> dict:
    """Apply a new permutation to every probe query, not every epoch."""
    trials = []
    all_unique = True
    for repetition in range(repetitions):
        rows_by_query = {}
        for query_id in range(65):
            permutation = make_permutation(seed + repetition * 1000 + query_id)
            rows_by_query[query_id] = permute_vector(
                capture_rows[(query_id, 1)], permutation
            )
        result = reacquire(
            rows_by_query,
            expected_fingerprint,
            initial_probe_ids,
            candidate_probe_ids,
            None,
            validation_probe_ids=validation_probe_ids,
        )
        result["repetition"] = repetition
        result["tracking_success_is_expected"] = False
        all_unique = all_unique and result["tracking_success"]
        trials.append(result)

    return {
        "mode": "independent_per_observation",
        "repetition_count": repetitions,
        "expected_verdict": "FAIL_EXPECTED",
        "unexpected_unique_reacquisition": all_unique,
        "all_trials_non_unique": not all_unique,
        "trials": trials,
    }


def load_config(config_path: Path) -> tuple[dict, Path]:
    config = json.loads(config_path.read_text())
    return config, config_path.parent.parent


def run_experiment(config_path: Path) -> dict:
    config, root = load_config(config_path)
    capture_path = root / config["capture"]
    queries_path = root / config["queries"]
    discovery_path = root / config["discovery"]
    capture_rows = parse_capture(capture_path)
    queries = parse_queries(queries_path)
    discovery = json.loads(discovery_path.read_text())
    selected_slot = int(discovery["final_selected_slot"]["scan_out_index"])
    schedule = int(config["fingerprint_schedule"])
    initial_probe_ids = [int(q) for q in config["initial_probe_ids"]]
    candidate_probe_ids = list(
        range(int(config["candidate_probe_start"]), int(config["candidate_probe_end"]) + 1)
    )
    payload_query_ids = list(
        range(int(config["payload_query_start"]), int(config["payload_query_end"]) + 1)
    )
    baseline_rows = {
        query_id: capture_rows[(query_id, schedule)] for query_id in queries
    }
    all_probe_ids = initial_probe_ids + candidate_probe_ids + [int(q) for q in config["validation_probe_ids"]]
    expected_fingerprint = fingerprint(baseline_rows, selected_slot, all_probe_ids)
    initial_fingerprint = expected_fingerprint[: len(initial_probe_ids)]
    validation_probe_ids = [int(q) for q in config["validation_probe_ids"]]

    scenarios = {
        "identity_static": identity_scenario(
            capture_rows,
            expected_fingerprint,
            initial_probe_ids,
            candidate_probe_ids,
            validation_probe_ids,
        )
    }
    for interval in config["refresh_intervals"]:
        key = f"stable_refresh_{int(interval)}"
        scenarios[key] = stable_scenario(
            capture_rows,
            expected_fingerprint,
            initial_probe_ids,
            candidate_probe_ids,
            validation_probe_ids,
            payload_query_ids,
            int(interval),
            int(config["permutation_seed"]),
        )
    scenarios["negative_independent_probe_permutation"] = independent_probe_control(
        capture_rows,
        expected_fingerprint,
        initial_probe_ids,
        candidate_probe_ids,
        validation_probe_ids,
        repetitions=8,
        seed=int(config["negative_probe_permutation_seed"]),
    )

    stable_results = [
        value
        for key, value in scenarios.items()
        if key == "identity_static" or key.startswith("stable_refresh_")
    ]
    negative = scenarios["negative_independent_probe_permutation"]
    result = {
        "schema": "phase-alpha-behavioral-tracking-v1",
        "experiment": "MC9 anonymous channel reacquisition",
        "scope": "tracking_only_no_key_recovery",
        "source": {
            "capture": str(capture_path.relative_to(root)),
            "queries": str(queries_path.relative_to(root)),
            "discovery": str(discovery_path.relative_to(root)),
            "scan_bit_count": SCAN_BITS,
            "query_count": len(queries),
            "schedule": schedule,
            "initial_selected_slot": selected_slot,
        },
        "fingerprint": {
            "query_ids": initial_probe_ids,
            "bit_string": "".join(map(str, initial_fingerprint)),
            "initial_probe_count": len(initial_probe_ids),
        },
        "scenarios": scenarios,
        "summary": {
            "stable_scenario_count": len(stable_results),
            "stable_all_correct": all(r["all_epochs_correct"] for r in stable_results),
            "stable_min_accuracy": min(r["tracking_accuracy"] for r in stable_results),
            "stable_max_accuracy": max(r["tracking_accuracy"] for r in stable_results),
            "negative_control_expected": negative["expected_verdict"],
            "negative_control_all_trials_non_unique": negative["all_trials_non_unique"],
            "alpha_verdict": (
                "PASS"
                if all(r["all_epochs_correct"] for r in stable_results)
                and negative["all_trials_non_unique"]
                else "FAIL"
            ),
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase_alpha.json")
    )
    args = parser.parse_args()
    result = run_experiment(args.config)
    config = json.loads(args.config.read_text())
    output_path = args.config.parent.parent / config["output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
