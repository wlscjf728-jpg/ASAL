#!/usr/bin/env python3
"""Exercise actual fixed/adaptive worker code with bounded solver calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from paper384 import EXP, ROOT, preflight, runtime_config, stage_module


def child(stage):
    with tempfile.TemporaryDirectory(prefix='asal-worker-probe-') as directory:
        output=Path(directory)
        config=runtime_config(stage,64,output)
        module=stage_module(stage)
        if stage=='fixed_q128':
            tasks=module.load_tasks(config)
        else:
            tasks=module.load_tasks(config,baseline_dir=EXP/'results/paper384_late_1bit_fixed_q128_runs')
        task=tasks[0]
        # Production configs are validated unchanged first. Only this disposable
        # probe gets time limits; its output is never a campaign checkpoint.
        for name in ['first_timeout_ms','second_timeout_ms','diagnostic_timeout_ms','separability_timeout_ms']:
            if name in config['solver']:
                config['solver'][name]=1000
        result=module.execute_task(task)
        if result.get('state')=='error':
            raise RuntimeError(result.get('error'))
        solver=result.get('solver',result.get('detail',{}))
        first=solver.get('first_result',solver.get('status'))
        if first not in {'sat','unknown'}:
            raise RuntimeError('No actual solver result was produced')
        print(json.dumps(dict(stage=stage,case_id=task.case['case_id'],seed=task.seed,
            query_count=task.query_count,first_result=first,
            second_result=solver.get('second_result'),state=result.get('state'),
            wall_seconds=result.get('wall_time'),solver_timeout_ms=1000,
            full_campaign_reproduced=False)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child',choices=['fixed_q128','pair_rescue'],help=argparse.SUPPRESS)
    parser.add_argument('--output',type=Path,default=ROOT/'run-output/startup-check.json')
    args=parser.parse_args()
    if args.child:
        child(args.child)
        return
    with tempfile.TemporaryDirectory(prefix='asal-startup-') as temporary:
        preflight(64,Path(temporary))
    results=[]
    for stage in ['fixed_q128','pair_rescue']:
        process=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',stage],
            cwd=ROOT,text=True,capture_output=True,timeout=180)
        if process.returncode:
            raise RuntimeError(f'{stage} startup failed:\n{process.stderr}')
        row=json.loads(process.stdout.splitlines()[-1])
        results.append(row)
        print(f"{stage}: real Q128 worker reached solver, {row['first_result']} -> {row['second_result']}")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'kind':'bounded-startup-check','runs':results},indent=2)+'\n')
    print('Startup passed. UNKNOWN is unresolved; this does not reproduce the full 384-run campaign.')


if __name__=='__main__':
    main()
