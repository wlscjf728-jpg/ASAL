import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _module():
    path = ROOT / "gate_reference" / "scripts" / "build_mc_hypothesis_observation.py"
    spec = importlib.util.spec_from_file_location("build_mc_hypothesis_observation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reference_differential_extracts_the_selected_bit(tmp_path):
    capture = tmp_path / "capture.txt"
    # The selected scan bit is slot 255. The reference bit is 1 at schedule 1
    # and 0 at schedule 3; query 0 must still have zero differential.
    capture.write_text(
        "0 1 " + "8" + "0" * 63 + "\n"
        "0 3 " + "0" * 64 + "\n"
        "1 1 " + "8" + "0" * 63 + "\n"
        "1 3 " + "8" + "0" * 63 + "\n"
    )
    queries = tmp_path / "queries.txt"
    queries.write_text(
        "0 00000000000000000000000000000000\n"
        "1 00000000000000000000000000000001\n"
    )

    doc = _module().build(capture, queries, 255)
    assert doc["observations"][0]["rounds"] == {
        "1": {"differential": 0},
        "2": {"differential": 0},
    }
    assert doc["observations"][1]["rounds"] == {
        "1": {"differential": 0},
        "2": {"differential": 1},
    }
