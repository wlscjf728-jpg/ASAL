from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_manifest_exists():
    assert (ROOT / "configs/campaigns.yaml").is_file()


def test_core_source_snapshot_exists():
    for relative in (
        "experiments/anonymous_subround_multiround_attack_7_oracle/scripts",
        "experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_fixed_baseline.py",
        "experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_pair_rescue.py",
        "experiments/anonymous_subround_multiround_attack_Leakage_Channel_Discovery/scripts",
        "experiments/RTL1_DFT_RESTUDY/scripts",
    ):
        assert (ROOT / relative).exists(), relative


def test_forbidden_evaluator_files_are_not_tracked_in_snapshot():
    forbidden = {"ucli.key", "hidden_key.evaluator.json"}
    found = [path for path in ROOT.rglob("*") if path.is_file() and path.name in forbidden]
    assert not found, found
