from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from key_diversity_common import (  # noqa: E402
    classify_pair,
    load_keys,
    load_taps,
    sanitize_for_solver,
)
from key_diversity_campaign import build_tasks  # noqa: E402


def test_inputs_are_four_taps_and_twenty_new_keys():
    taps = load_taps(ROOT / "configs/representative_post_mc_taps.csv")
    keys = load_keys(ROOT / "inputs/evaluator_keys.csv")
    assert len(taps) == 4
    assert len(keys) == 20
    assert len({row["tap_id"] for row in taps}) == 4
    assert len({row["key_hex"] for row in keys}) == 20
    assert {row["column"] for row in taps} == {"0", "1", "2", "3"}


def test_solver_payload_has_no_secret_key():
    document = {"evaluator": {"true_key_hex": "00" * 16}, "observations": []}
    clean = sanitize_for_solver(document)
    assert "true_key_hex" not in json.dumps(clean)
    assert clean["evaluator"]["true_key_removed"] is True


def test_only_sat_to_unsat_is_unique():
    assert classify_pair("sat", "unsat") == "unique"
    assert classify_pair("sat", "sat") == "ambiguity"
    assert classify_pair("sat", "unknown") == "unresolved"


def test_campaign_has_exactly_eighty_tasks():
    tasks = build_tasks()
    assert len(tasks) == 80
    assert len({(task["key_id"], task["tap"]["tap_id"]) for task in tasks}) == 80


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [("sat", "unsat", "FIXED_UNIQUE"), ("sat", "sat", "FIXED_AMBIGUOUS")],
)
def test_terminal_classification_mapping(first, second, expected):
    from key_diversity_campaign import terminal_classification

    assert terminal_classification(first, second, adaptive=False) == expected
