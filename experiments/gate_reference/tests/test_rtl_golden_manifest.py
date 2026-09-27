import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "gate_reference" / "defense_boundary" / "results" / "software_golden_manifest.json"


def test_golden_manifest_excludes_extended_variants():
    doc = json.loads(MANIFEST.read_text())
    ids = [row["condition_id"] for row in doc["conditions"]]
    assert "D1" in ids
    assert "D1b" not in ids
    assert "D3b" not in ids
    assert all(
        row["golden_verdict"]
        in {"ATTACK_SUCCESS", "NO_ATTRIBUTABLE_CHANNEL", "BLOCKED_BY_POLICY"}
        for row in doc["conditions"]
    )


def test_golden_manifest_keeps_state_only_scope_explicit():
    doc = json.loads(MANIFEST.read_text())
    row = next(row for row in doc["conditions"] if row["condition_id"] == "D1")
    assert row["technique"] == "State-centric protection (post-MC exposed)"
    assert row["golden_verdict"] == "ATTACK_SUCCESS"
    assert row["golden_fixed"] == "ambiguity"
    assert row["golden_final"] == "full_key_unique"


def test_primary_manifest_has_expected_condition_count():
    doc = json.loads(MANIFEST.read_text())
    assert len(doc["conditions"]) == 13


def _comparison_module():
    import importlib.util

    path = ROOT / "gate_reference" / "defense_boundary" / "scripts" / "compare_rtl_to_software.py"
    spec = importlib.util.spec_from_file_location("compare_rtl_to_software", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compare_requires_rtl_artifact_for_each_condition():
    compare_manifest = _comparison_module().compare_manifest

    manifest = json.loads(MANIFEST.read_text())
    result = compare_manifest(manifest, {})
    assert result["matched"] == 0
    assert result["incomplete"] == 13


def test_compare_accepts_only_matching_phase_verdicts():
    compare_condition = _comparison_module().compare_condition

    manifest = json.loads(MANIFEST.read_text())
    golden = next(row for row in manifest["conditions"] if row["condition_id"] == "D1")
    rtl = {
        "rtl_verdict": "ATTACK_SUCCESS",
        "phase0": {"status": "pass"},
        "attribution": {"status": "pass"},
        "fixed": {"classification": "ambiguity"},
        "adaptive": {"status": "completed_from_validated_closed_loop"},
        "final": {"classification": "full_key_unique"},
        "first_blocked_stage": None,
    }
    result = compare_condition(golden, rtl)
    assert result["status"] == "MATCHED"
    assert result["errors"] == []


def test_compare_rejects_missing_final_key_proof():
    compare_condition = _comparison_module().compare_condition

    manifest = json.loads(MANIFEST.read_text())
    golden = next(row for row in manifest["conditions"] if row["condition_id"] == "D1")
    rtl = {
        "rtl_verdict": "ATTACK_SUCCESS",
        "phase0": {"status": "pass"},
        "attribution": {"status": "pass"},
        "fixed": {"classification": "ambiguity"},
        "adaptive": {"status": "completed_from_validated_closed_loop"},
        "first_blocked_stage": None,
    }
    result = compare_condition(golden, rtl)
    assert result["status"] == "MISMATCH"
    assert result["final_match"] is False
