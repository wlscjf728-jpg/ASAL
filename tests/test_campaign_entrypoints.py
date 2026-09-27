import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import paper384


@pytest.mark.parametrize('stage',['fixed_q128','pair_rescue'])
@pytest.mark.parametrize('workers',[1,32,64])
def test_valid_worker_limits(stage,workers,tmp_path):
    config=paper384.runtime_config(stage,workers,tmp_path)
    paper384.stage_module(stage)._validate_config(config)


@pytest.mark.parametrize('stage',['fixed_q128','pair_rescue'])
@pytest.mark.parametrize('workers',[0,-1,65])
def test_invalid_worker_limits(stage,workers,tmp_path):
    with pytest.raises(ValueError,match='between 1 and 64'):
        paper384.runtime_config(stage,workers,tmp_path)


def test_preflight_loads_real_tasks_without_outputs(tmp_path):
    paper384.preflight(64,tmp_path)
    assert not list(tmp_path.iterdir())


def test_fixed_cli_accepts_64_and_default_384_config(tmp_path):
    script=paper384.EXP/'scripts/run_late1bit_fixed_paper384.py'
    result=subprocess.run([sys.executable,str(script),'--workers','64','--result-dir',str(tmp_path),'--dry-run'],
        cwd=paper384.EXP,text=True,capture_output=True,check=True)
    assert 'runs=384 pending=384 workers=64' in result.stdout


def test_ambiguous_first_candidate_need_not_equal_test_key(tmp_path):
    source=paper384.EXP/'results/paper384_late_1bit_fixed_q128_runs'
    for path in source.glob('*.json'):
        row=json.loads(path.read_text())
        if row['terminal_classification']=='finite_query_ambiguity':
            row['solver']['first_model_correct']=False
        (tmp_path/path.name).write_text(json.dumps(row))
    assert len(paper384.verify(tmp_path))==135


def test_unique_wrong_key_is_rejected(tmp_path):
    source=paper384.EXP/'results/paper384_late_1bit_fixed_q128_runs'
    shutil.copytree(source,tmp_path/'fixed')
    path=next(p for p in (tmp_path/'fixed').glob('*.json') if json.loads(p.read_text())['terminal_classification']=='fixed_query_unique')
    row=json.loads(path.read_text()); row['solver']['first_model_correct']=False
    path.write_text(json.dumps(row))
    with pytest.raises(AssertionError,match='Unique key'):
        paper384.verify(tmp_path/'fixed')


def test_bootstrap_recipe_matches_archived_key_diversity():
    archive=ROOT/'evidence/source/anonymous_subround_multiround_attack_key_diversity/results/raw_runs.jsonl'
    archived={json.loads(line)['evaluator_only']['key_sha256'] for line in archive.read_text().splitlines() if line.strip()}
    generated={hashlib.sha256(hashlib.sha256(f'asal-key-diversity-20260903-{i}'.encode()).digest()[:16]).hexdigest() for i in range(20)}
    assert generated==archived


def test_96_dry_run_schedules_fresh_outputs(tmp_path, monkeypatch, capfd):
    import reproduce
    monkeypatch.setattr(reproduce, 'ROOT', tmp_path)
    monkeypatch.setenv('ASAL_WORKERS', '4')
    reproduce.one_bit_96(dry_run=True)
    output = capfd.readouterr().out
    assert 'runs=96 pending=96 workers=4' in output
    assert 'selected=32 workers=4' in output


def test_96_record_verifier_uses_96_manifest():
    source = paper384.EXP
    ambiguous = paper384.verify(
        source/'results/late_1bit_fixed_q128_runs',
        source/'results/late_1bit_pair_rescue_runs',
        manifest=source/'configs/late_1bit_positions.csv', expected_runs=96)
    assert len(ambiguous) == 32
