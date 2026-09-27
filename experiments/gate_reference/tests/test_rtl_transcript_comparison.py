import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _module():
    path = ROOT / "gate_reference" / "defense_boundary" / "scripts" / "compare_transcript_to_software.py"
    spec = importlib.util.spec_from_file_location("compare_transcript_to_software", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_baseline_rtl_q128_matches_software():
    result = _module().compare(
        ROOT / "gate_reference/results/phase_b/q128_mc_hypotheses_attack.json",
        ROOT / "gate_reference/defense_boundary/results/baseline/attack/q128_mc_hypotheses_rtl.json",
    )
    assert result["exact_observation_match"] is True
    assert result["software_observation_count"] == 129
    assert result["rtl_observation_count"] == 129


def test_primary_rtl_q131_transcripts_match_software():
    software = ROOT / "gate_reference/results/phase_b/q131_mc_hypotheses_attack_pruned.json"
    for variant in ("baseline", "state_protected", "round_only"):
        result = _module().compare(
            software,
            ROOT / "gate_reference/defense_boundary/results" / variant / "attack/q131_mc_hypotheses_rtl.json",
        )
        assert result["status"] == "MATCHED"
        assert result["rtl_observation_count"] == 131
