#!/usr/bin/env python3
"""Run the anonymous MC-function attribution and gate-level adaptive loop."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PYTHON=Path(__import__('sys').executable)
PHASE=ROOT/'gate_reference/results/phase_b'
LOGS=ROOT/'gate_reference/logs'

def run(cmd, log_name=None):
    LOGS.mkdir(parents=True,exist_ok=True)
    output=None
    if log_name:
        output=(LOGS/log_name).open('w')
    try:
        return subprocess.run(cmd, cwd=ROOT, stdout=output or None, stderr=subprocess.STDOUT if output else None, check=True)
    finally:
        if output: output.close()

def wait_for(path: Path):
    while not path.is_file() or path.stat().st_size == 0:
        time.sleep(5)

def load(path): return json.loads(path.read_text())

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--workers',type=int,default=32); ap.add_argument('--hidden-key',type=Path,default=ROOT/'gate_reference/inputs/hidden_key.evaluator.json'); args=ap.parse_args()
    q128=PHASE/'q128_mc_hypotheses_attack.json'
    q128_solver=PHASE/'q128_mc_hypothesis_solver_attack.json'
    wait_for(q128_solver)
    s128=load(q128_solver)
    if s128['joint_key_uniqueness']['first_result'] != 'sat': raise RuntimeError('Q128 first joint solve was not SAT')
    run([str(PYTHON), 'gate_reference/scripts/filter_mc_hypotheses.py','--transcript',str(q128),'--solver-result',str(q128_solver),'--output',str(PHASE/'q129_mc_hypotheses_attack_pruned.json')], 'q129_mc_hypothesis_filter.log')
    q129=PHASE/'q129_mc_hypotheses_attack_pruned.json'
    q129_solver=PHASE/'q129_mc_hypothesis_solver_attack.json'
    if q129_solver.is_file() and q129_solver.stat().st_size:
        s129=load(q129_solver)
    else:
        run([str(PYTHON),'gate_reference/scripts/run_mc_hypothesis_solver.py','--input',str(q129),'--output',str(q129_solver),'--workers',str(args.workers)], 'q129_mc_hypothesis_solver_attack.log')
        s129=load(q129_solver)
    if s129['joint_key_uniqueness']['second_result'] == 'unsat':
        final=q129_solver
    elif s129['joint_key_uniqueness']['second_result'] == 'sat':
        sep=PHASE/'adaptive_separator_mc_hypothesis_synthesis.json'
        run([str(PYTHON),'gate_reference/scripts/generate_mc_hypothesis_separator.py','--input',str(q129),'--solver-result',str(q129_solver),'--output',str(sep)], 'adaptive_separator_mc_hypothesis_synthesis.log')
        sep_doc=load(sep)
        if sep_doc.get('status') != 'sat': raise RuntimeError('hypothesis pair separator unresolved')
        point=sep_doc['plaintext_hex']
        query_manifest=PHASE/'adaptive_separator_mc_hypothesis_queries.txt'
        reference=load(q129)['observations'][0]['plaintext_hex']
        run([str(PYTHON),'gate_reference/scripts/make_single_query_manifest.py','--plaintext',point,'--reference',reference,'--output',str(query_manifest)])
        raw=PHASE/'adaptive_separator_mc_hypothesis_gate_scan_eval5.txt'
        key=load(args.hidden_key)['true_key_hex']
        run([str(PHASE/'simv_gate_capture'),f'+QUERY_FILE={query_manifest.relative_to(ROOT)}',f'+OUT_FILE={raw.relative_to(ROOT)}',f'+KEY_HEX={key}'], 'adaptive_separator_mc_hypothesis_gate_capture.log')
        extra=PHASE/'adaptive_separator_mc_hypothesis_gate_observation.json'
        run([str(PYTHON),'gate_reference/scripts/build_mc_hypothesis_observation.py','--capture',str(raw),'--queries',str(query_manifest),'--slot','255','--hypotheses-from',str(q129),'--output',str(extra)], 'adaptive_separator_mc_hypothesis_observation.log')
        q130=PHASE/'q130_mc_hypotheses_attack_closed_loop.json'
        run([str(PYTHON),'gate_reference/scripts/append_mc_hypothesis_observation.py','--base',str(q129),'--extra',str(extra),'--output',str(q130)])
        # Filter only after the Q129 survivor set was established; this is the
        # hypothesis set used for the final key-exclusion solve.
        q130_pruned=PHASE/'q130_mc_hypotheses_attack_pruned.json'
        run([str(PYTHON),'gate_reference/scripts/filter_mc_hypotheses.py','--transcript',str(q130),'--solver-result',str(q129_solver),'--output',str(q130_pruned)])
        final=PHASE/'q130_mc_hypothesis_solver_attack.json'
        run([str(PYTHON),'gate_reference/scripts/run_mc_hypothesis_solver.py','--input',str(q130_pruned),'--output',str(final),'--workers',str(args.workers)], 'q130_mc_hypothesis_solver_attack.log')
    summary={
      'schema':'mc9-anonymous-function-attribution-closed-loop-v1',
      'q128_solver':str(q128_solver),
      'q129_solver':str(q129_solver),
      'final_solver':str(final),
      'q128_surviving_hypothesis_count':s128['surviving_hypothesis_count'],
      'q129_surviving_hypothesis_count':s129['surviving_hypothesis_count'],
      'final_joint_key_uniqueness':load(final)['joint_key_uniqueness'],
      'attack_used_ground_truth_mc9':False,
      'attack_used_hidden_key':False,
    }
    out=PHASE/'mc9_anonymous_function_attribution_closed_loop.json'; out.write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
