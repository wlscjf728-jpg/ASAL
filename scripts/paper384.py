"""Reproduce or validate the 384-run one-bit campaign."""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import importlib
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / 'experiments/temporal_key_recovery'


def stage_module(stage):
    folder=str(EXP/'scripts')
    if folder not in sys.path:
        sys.path.insert(0,folder)
    names={'fixed_q128':'run_late1bit_fixed_paper384','pair_rescue':'run_late1bit_pair_rescue_paper384'}
    return importlib.import_module(names[stage])


def runtime_config(stage,workers,output):
    config=yaml.safe_load((EXP/f'configs/late_1bit_{stage}_paper384.yaml').read_text())
    config['campaign']['workers']=workers
    config['paths'].update(result_dir=str(output/stage),summary=str(output/f'{stage}_summary.jsonl'),errors=str(output/f'{stage}_errors.jsonl'))
    if stage=='pair_rescue':
        config['paths'].update(baseline_result_dir=str(output/'fixed_q128'),checkpoint_dir=str(output/'checkpoints'))
    stage_module(stage)._validate_config(config)
    return config


def preflight(workers,output):
    fixed=runtime_config('fixed_q128',workers,output)
    adaptive=runtime_config('pair_rescue',workers,output)
    tasks=stage_module('fixed_q128').load_tasks(fixed)
    with tempfile.TemporaryDirectory(prefix='asal-preflight-') as temporary:
        count=len(stage_module('pair_rescue').load_tasks(adaptive,
            baseline_dir=EXP/'results/paper384_late_1bit_fixed_q128_runs',
            result_dir=Path(temporary)/'adaptive',checkpoint_dir=Path(temporary)/'checkpoints'))
    print(f'Validated both stage configs: workers={workers}; fixed pending={len(tasks)}; archived adaptive inputs={count}')
    return fixed,adaptive


def verify(fixed, adaptive=None, *, manifest=None, expected_runs=384):
    with (manifest or EXP / 'configs/late_1bit_positions_paper384.csv').open() as f:
        expected = {(r['case_id'], seed) for r in csv.DictReader(f) for seed in range(3)}
    def load(folder):
        rows = [json.loads(p.read_text()) for p in folder.glob('*.json')]
        indexed = {(r['case_id'], r['seed']): r for r in rows}
        assert len(indexed) == len(rows), 'Duplicate identities'
        assert all(r['state'] == 'terminal' for r in rows), 'Nonterminal result'
        return indexed
    rows = load(fixed)
    assert len(expected) == expected_runs and set(rows) == expected, 'Incomplete fixed campaign'
    ambiguous = set()
    for identity, r in rows.items():
        s = r['solver']
        assert r['query_count'] == 128 and r['oracle_encryptions'] == 129
        assert s['first_result'] == 'sat'
        if r['terminal_classification'] == 'finite_query_ambiguity':
            assert s['second_result'] == 'sat'
            ambiguous.add(identity)
        else:
            assert r['terminal_classification'] == 'fixed_query_unique' and s['second_result'] == 'unsat'
            assert s['first_model_correct'], 'Unique key disagrees with evaluator'
    print(f'fixed={expected_runs} unique={expected_runs-len(ambiguous)} ambiguous={len(ambiguous)}')
    if adaptive is not None:
        recovered = load(adaptive)
        assert set(recovered) == ambiguous, 'Incomplete adaptive campaign'
        for r in recovered.values():
            s = r['solver']
            assert r['attack_success'] and r['terminal_classification'] == 'adaptive_key_recovered'
            assert (s['first_result'], s['second_result']) == ('sat', 'unsat') and s['first_model_correct']
            assert r['total_query_count'] == 128 + r['adaptive_query_count']
        print(f'recovered={expected_runs} adaptive_queries=' + str(dict(sorted(Counter(r['total_query_count'] for r in recovered.values()).items()))))
    return ambiguous


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--output-root', type=Path, default=ROOT / 'run-output/paper384')
    args = p.parse_args()
    if args.verify:
        verify(EXP / 'results/paper384_late_1bit_fixed_q128_runs', EXP / 'results/paper384_late_1bit_pair_rescue_runs')
        return
    workers = int(os.environ.get('ASAL_WORKERS', '4'))
    if not 1 <= workers <= 64:
        raise ValueError('ASAL_WORKERS must be between 1 and 64')
    output = args.output_root.resolve()
    if output == EXP/'results' or EXP/'results' in output.parents:
        raise ValueError('Use run-output/ or another fresh directory, not bundled results/')
    configs=preflight(workers,output)
    if args.dry_run:
        print(f'384 fixed runs -> ambiguity-only adaptive; workers={workers}; output={output}')
        print('No solver execution. Both configs and task inputs were loaded; terminal records are resumed on execution.')
        return
    output.mkdir(parents=True, exist_ok=True)
    for (stage, script), config in zip([('fixed_q128', 'run_late1bit_fixed_paper384.py'), ('pair_rescue', 'run_late1bit_pair_rescue_paper384.py')],configs):
        if stage=='pair_rescue' and not verify(output/'fixed_q128'):
            (output/'pair_rescue').mkdir(exist_ok=True)
            verify(output/'fixed_q128',output/'pair_rescue')
            return
        path = output / f'{stage}.yaml'
        path.write_text(yaml.safe_dump(config))
        subprocess.run([sys.executable, str(EXP / 'scripts' / script), '--config', str(path), '--workers', str(workers)], cwd=EXP, check=True)
        verify(output / 'fixed_q128', output / 'pair_rescue' if stage == 'pair_rescue' else None)


if __name__ == '__main__':
    main()
