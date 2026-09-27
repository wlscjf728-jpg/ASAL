#!/usr/bin/env python3
"""Stable command-line entry points for the copied ASAL campaigns."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import yaml
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
PYTHON = Path(sys.executable)


def run(command: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("+", " ".join(command), f"(cwd={cwd})", flush=True)
    subprocess.run(command, cwd=cwd, env=merged, check=True)


def attack8_script(name: str, *args: str) -> None:
    cwd = EXP / "temporal_key_recovery"
    run([str(PYTHON), "scripts/" + name, *args], cwd)


def one_bit_96(dry_run: bool) -> None:
    from paper384 import verify
    workers = int(os.environ.get("ASAL_WORKERS", "4"))
    if not 1 <= workers <= 32:
        raise ValueError('96-run ASAL_WORKERS must be between 1 and 32')
    source=EXP/'temporal_key_recovery'
    output=ROOT/'run-output/one-bit-96'
    flag=['--dry-run'] if dry_run else []
    with tempfile.TemporaryDirectory(prefix='asal96-config-') as temporary:
        for stage,script in [('fixed_q128','run_late1bit_fixed_baseline.py'),('pair_rescue','run_late1bit_pair_rescue.py')]:
            config=yaml.safe_load((source/f'configs/late_1bit_{stage}.yaml').read_text())
            config['campaign']['workers']=workers
            config['paths'].update(result_dir=str(output/stage),summary=str(output/f'{stage}_summary.jsonl'),errors=str(output/f'{stage}_errors.jsonl'))
            if stage=='pair_rescue':
                if not dry_run and not verify(output/'fixed_q128',manifest=source/'configs/late_1bit_positions.csv',expected_runs=96):
                    (output/'pair_rescue').mkdir(parents=True,exist_ok=True)
                    verify(output/'fixed_q128',output/'pair_rescue',manifest=source/'configs/late_1bit_positions.csv',expected_runs=96)
                    return
                baseline=source/'results/late_1bit_fixed_q128_runs' if dry_run else output/'fixed_q128'
                config['paths'].update(baseline_result_dir=str(baseline),checkpoint_dir=str(output/'checkpoints'))
                if dry_run:
                    print('Adaptive dry-run uses bundled ambiguous inputs; actual execution uses the new fixed outputs.',flush=True)
            path=Path(temporary)/f'{stage}.yaml'
            path.write_text(yaml.safe_dump(config))
            attack8_script(script,'--config',str(path),'--workers',str(workers),*flag)
            if not dry_run:
                verify(output/'fixed_q128',output/'pair_rescue' if stage=='pair_rescue' else None,
                    manifest=source/'configs/late_1bit_positions.csv',expected_runs=96)


def smoke() -> None:
    attack8 = EXP / "temporal_key_recovery"
    discovery = EXP / "channel_discovery"
    diversity = EXP / "key_diversity"
    phase_alpha = EXP / "channel_tracking"
    run([str(PYTHON), "-m", "compileall", "-q", "scripts"], attack8)
    run([str(PYTHON), "scripts/validate_setup.py"], attack8)
    run([str(PYTHON), "scripts/adaptive_query_attack.py", "--strategy", "fixed_nested", "--dry-run"], attack8)
    run([str(PYTHON), "scripts/adaptive_query_attack.py", "--strategy", "adaptive_pairwise", "--dry-run"], attack8)
    run([str(PYTHON), "-m", "pytest", "-q", "tests"], attack8)
    run([str(PYTHON), "-m", "pytest", "-q", "tests"], discovery)
    key_manifest = diversity / "inputs/evaluator_keys.csv"
    if not key_manifest.exists():
        run([str(PYTHON), "scripts/bootstrap_inputs.py", "--seed", "20260903", "--count", "20"], diversity)
    run([str(PYTHON), "-m", "pytest", "-q", "tests"], diversity)
    run([str(PYTHON), "-m", "pytest", "-q", "tests"], phase_alpha)


def discovery_smoke() -> None:
    cwd = EXP / "channel_discovery"
    run([str(PYTHON), "scripts/run_discovery_campaign.py", "--config", "configs/discovery_config.yaml", "--positive", "2", "--negative", "1"], cwd)


def key_diversity_smoke() -> None:
    cwd = EXP / "key_diversity"
    key_manifest = cwd / "inputs/evaluator_keys.csv"
    if not key_manifest.exists():
        run([str(PYTHON), "scripts/bootstrap_inputs.py", "--seed", "20260903", "--count", "20"], cwd)
    run([str(PYTHON), "scripts/key_diversity_campaign.py", "--limit", "1", "--workers", "1"], cwd)


def tracking() -> None:
    cwd = EXP / "channel_tracking"
    run([str(PYTHON), "scripts/phase_alpha_tracking.py", "--config", "configs/phase_alpha.json"], cwd)


def gate_smoke() -> None:
    cwd = EXP / "gate_topologies"
    run([str(PYTHON), "-m", "pytest", "-q", "tests/test_shared_infrastructure.py", "tests/test_topology_generator.py"], cwd)
    run([str(PYTHON), "-m", "py_compile", "scripts/generate_topology_cases.py"], cwd)


def dft_prepare() -> None:
    cwd = EXP / "partial_scan_testability"
    (cwd / "results/analysis").mkdir(parents=True, exist_ok=True)
    run([str(PYTHON), "-m", "pytest", "-q", "tests"], cwd)
    run([str(PYTHON), "scripts/aes_internal_v2_prepare.py"], cwd)


def dft_run() -> None:
    cwd = EXP / "partial_scan_testability"
    env = {}
    if os.environ.get("DC_SHELL"):
        env["DC_SHELL"] = os.environ["DC_SHELL"]
    if os.environ.get("TMAX_BIN"):
        env["TMAX_BIN"] = os.environ["TMAX_BIN"]
    run(["bash", "scripts/run_aes_internal_v2_dft.sh"], cwd, env=env)
    run(["bash", "scripts/run_aes_internal_v2_tmax.sh"], cwd, env=env)
    run([str(PYTHON), "scripts/analyze_aes_internal_v2.py"], cwd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke", "one-bit-96", "discovery-smoke", "key-diversity-smoke", "tracking", "gate-smoke", "dft-prepare", "dft-run"))
    parser.add_argument("--dry-run", action="store_true", help="only print the one-bit campaign task counts")
    args = parser.parse_args()
    if args.command == "smoke":
        smoke()
    elif args.command == "one-bit-96":
        one_bit_96(args.dry_run)
    elif args.command == "discovery-smoke":
        discovery_smoke()
    elif args.command == "key-diversity-smoke":
        key_diversity_smoke()
    elif args.command == "tracking":
        tracking()
    elif args.command == "gate-smoke":
        gate_smoke()
    elif args.command == "dft-prepare":
        dft_prepare()
    elif args.command == "dft-run":
        dft_run()


if __name__ == "__main__":
    main()
