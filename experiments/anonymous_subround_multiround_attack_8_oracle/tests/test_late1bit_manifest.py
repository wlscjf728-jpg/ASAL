from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dependency_support import profile_candidates
from experiment_common import load_candidate_map


APPROVED_CANDIDATES = {
    ("MC_0", "MC", 0, 0, 0),
    ("MC_9", "MC", 9, 1, 1),
    ("MC_18", "MC", 18, 2, 2),
    ("MC_27", "MC", 27, 3, 3),
    ("MC_36", "MC", 36, 4, 4),
    ("MC_45", "MC", 45, 5, 5),
    ("MC_54", "MC", 54, 6, 6),
    ("MC_63", "MC", 63, 7, 7),
    ("MC_64", "MC", 64, 8, 0),
    ("MC_73", "MC", 73, 9, 1),
    ("MC_82", "MC", 82, 10, 2),
    ("MC_91", "MC", 91, 11, 3),
    ("MC_100", "MC", 100, 12, 4),
    ("MC_109", "MC", 109, 13, 5),
    ("MC_118", "MC", 118, 14, 6),
    ("MC_127", "MC", 127, 15, 7),
    ("ARK_4", "ARK", 4, 0, 4),
    ("ARK_13", "ARK", 13, 1, 5),
    ("ARK_22", "ARK", 22, 2, 6),
    ("ARK_31", "ARK", 31, 3, 7),
    ("ARK_32", "ARK", 32, 4, 0),
    ("ARK_41", "ARK", 41, 5, 1),
    ("ARK_50", "ARK", 50, 6, 2),
    ("ARK_59", "ARK", 59, 7, 3),
    ("ARK_68", "ARK", 68, 8, 4),
    ("ARK_77", "ARK", 77, 9, 5),
    ("ARK_86", "ARK", 86, 10, 6),
    ("ARK_95", "ARK", 95, 11, 7),
    ("ARK_96", "ARK", 96, 12, 0),
    ("ARK_105", "ARK", 105, 13, 1),
    ("ARK_114", "ARK", 114, 14, 2),
    ("ARK_123", "ARK", 123, 15, 3),
}


def rows():
    with (ROOT / "configs/late_1bit_positions.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_manifest_is_balanced_and_nonredundant():
    manifest = rows()
    assert len(manifest) == 32
    assert {
        (
            row["candidate_id"],
            row["stage"],
            int(row["bit_index"]),
            int(row["byte_index"]),
            int(row["bit_in_byte"]),
        )
        for row in manifest
    } == APPROVED_CANDIDATES
    assert len({row["case_id"] for row in manifest}) == 32
    assert len({row["candidate_id"] for row in manifest}) == 32
    assert sum(row["stage"] == "MC" for row in manifest) == 16
    assert sum(row["stage"] == "ARK" for row in manifest) == 16
    for stage in ("MC", "ARK"):
        selected = [row for row in manifest if row["stage"] == stage]
        assert {int(row["byte_index"]) for row in selected} == set(range(16))
        assert sorted(int(row["bit_in_byte"]) for row in selected) == sorted(list(range(8)) * 2)
    mc = {int(row["bit_index"]) for row in manifest if row["stage"] == "MC"}
    ark = {int(row["bit_index"]) for row in manifest if row["stage"] == "ARK"}
    assert mc.isdisjoint(ark)


def test_manifest_matches_candidate_map_and_full_round2_support():
    manifest = rows()
    candidate_map = load_candidate_map()
    ids = {row["candidate_id"] for row in manifest}
    assert ids <= candidate_map.keys()
    for row in manifest:
        candidate = candidate_map[row["candidate_id"]]
        assert row["stage"] == candidate["stage"]
        assert int(row["bit_index"]) == int(candidate["bit_index"])
        assert int(row["byte_index"]) == int(candidate["byte_index"])
        assert int(row["bit_in_byte"]) == int(candidate["bit_in_byte"])
    profiles = profile_candidates(ids, depth=2)
    round2 = [row for row in profiles if row["round"] == 2]
    assert len(round2) == 32
    assert all(row["structural_k0_bit_count"] == 128 for row in round2)


def test_config_fixes_threat_model_and_resources():
    config = yaml.safe_load((ROOT / "configs/late_1bit_adaptive.yaml").read_text())
    assert config["campaign"] == {"workers": 32, "seeds": [0, 1, 2]}
    assert config["attack"]["depth"] == 2
    assert config["attack"]["mode"] == "differential"
    assert config["attack"]["initial_query_count"] == 64
    assert config["attack"]["max_adaptive_queries"] is None
    assert config["solver"]["first_timeout_ms"] == 0
    assert config["solver"]["second_timeout_ms"] == 0
    assert config["solver"]["separability_timeout_ms"] == 0
