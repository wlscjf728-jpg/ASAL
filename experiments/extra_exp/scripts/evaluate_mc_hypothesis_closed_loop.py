#!/usr/bin/env python3
"""Evaluator-only correctness check for the anonymous MC hypothesis campaign."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--hidden-key',type=Path,required=True)
    ap.add_argument('--mapping',type=Path,required=True)
    ap.add_argument('--q128',type=Path,required=True)
    ap.add_argument('--q129',type=Path,required=True)
    ap.add_argument('--q130',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    hidden=json.loads(args.hidden_key.read_text())['true_key_hex']
    mapping=json.loads(args.mapping.read_text())
    rows=[]
    for label,path,expected in [('q128',args.q128,('sat','sat')),('q129',args.q129,('sat','sat')),('q130',args.q130,('sat','unsat'))]:
        result=json.loads(path.read_text())
        joint=result['joint_key_uniqueness']
        actual=next((r for r in result['branch_consistency'] if r['hypothesis_id']=='h09'),None)
        rows.append({
          'label':label,
          'input_transcript':result['input_transcript'],
          'initial_hypothesis_count':result['initial_hypothesis_count'],
          'surviving_hypothesis_count':result['surviving_hypothesis_count'],
          'actual_hypothesis_h09_survives':actual is not None and actual['status']=='sat',
          'first_result':joint['first_result'],
          'second_result':joint['second_result'],
          'classification':joint.get('classification'),
          'first_model_matches_hidden_key':joint.get('first_model_hex')==hidden,
          'unknown_or_timeout':bool(joint.get('unknown') or joint.get('timeout')),
        })
    final=rows[-1]
    payload={
      'schema':'mc9-anonymous-hypothesis-evaluator-check-v1',
      'hidden_key_hex':hidden,
      'ground_truth_semantic_label':'MC_9',
      'ground_truth_hypothesis_id':'h09',
      'ground_truth_mapping':{
         'scan_slot':mapping['target']['scan_slot'],
         'serialized_scan_out_index':mapping['target']['serialized_scan_out_index'],
         'mapped_register':mapping['target'].get('register','aes_core/MC_REG_reg[9]'),
      },
      'phase_results':rows,
      'pass':(
        all(row['actual_hypothesis_h09_survives'] for row in rows)
        and rows[0]['first_result']=='sat' and rows[0]['second_result']=='sat'
        and rows[1]['first_result']=='sat' and rows[1]['second_result']=='sat'
        and final['first_result']=='sat' and final['second_result']=='unsat'
        and final['first_model_matches_hidden_key']
        and all(not row['unknown_or_timeout'] for row in rows)
        and mapping['target']['serialized_scan_out_index']==255
      ),
      'attack_used_hidden_key':False,
      'attack_used_ground_truth_mc9':False,
      'evaluator_only':True,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({k:payload[k] for k in ('schema','pass','ground_truth_hypothesis_id','phase_results')},indent=2))
if __name__=='__main__':main()
