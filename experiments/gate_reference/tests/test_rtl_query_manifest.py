from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_q131_manifest_has_unique_fixed_and_adaptive_query_ids():
    rows = [line.split() for line in (ROOT / "gate_reference/defense_boundary/results/q131.txt").read_text().splitlines()]
    ids = [int(row[0]) for row in rows]
    assert len(ids) == 131
    assert ids == list(range(131))
    assert rows[129][1] == "09000e00000b239a2d00597ea68b005a"
    assert rows[130][1] == "c8403200ee31323a148e004020170038"
