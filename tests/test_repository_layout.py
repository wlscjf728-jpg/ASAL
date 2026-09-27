from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_campaign_manifest_exists():
    assert (ROOT / "configs/campaigns.yaml").is_file()


def test_core_source_snapshot_exists():
    for relative in (
        "experiments/multibit_baselines/scripts",
        "experiments/temporal_key_recovery/scripts/run_late1bit_fixed_baseline.py",
        "experiments/temporal_key_recovery/scripts/run_late1bit_pair_rescue.py",
        "experiments/channel_discovery/scripts",
        "experiments/partial_scan_testability/scripts",
    ):
        assert (ROOT / relative).exists(), relative


def test_forbidden_evaluator_files_are_not_tracked_in_snapshot():
    forbidden = {"ucli.key", "hidden_key.evaluator.json"}
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    found = [path for path in tracked if Path(path).name in forbidden | {'evaluator_keys.csv'}]
    assert not found, found
