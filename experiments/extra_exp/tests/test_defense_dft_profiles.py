import json
from pathlib import Path


def test_each_variant_has_independent_artifact_root():
    doc = json.loads(Path("extra_exp/defense_boundary/configs/variant_matrix.json").read_text())
    roots = [item["artifact_root"] for item in doc["variants"]]
    assert len(roots) == len(set(roots))
    assert all(root.startswith("extra_exp/defense_boundary/results/") for root in roots)
