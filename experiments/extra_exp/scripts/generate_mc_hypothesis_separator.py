#!/usr/bin/env python3
"""Generate an adaptive plaintext for two anonymous (key, MC-function) models."""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
import z3

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'anonymous_subround_multiround_attack_8_oracle'/'scripts'))
from z3_aes import AESGraphBuilder, select_bit


def domain_constraints(point, reference):
    changed=[point[i] != z3.BitVecVal(reference[i],8) for i in range(16)]
    return [z3.Sum([z3.If(item,1,0) for item in changed]) >= 1]


def leakage(builder, query_id, base_id, hypothesis, depth):
    result=[]
    bit_index=int(hypothesis['bit_index'])
    stage=str(hypothesis['stage'])
    for rnd in range(1,depth+1):
        q=select_bit(builder.graphs[query_id][rnd][stage],bit_index)
        b=select_bit(builder.graphs[base_id][rnd][stage],bit_index)
        result.append(q ^ b)
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--solver-result',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--sbox-encoding',default='uf_axiom',choices=('uf_axiom','array_select','ite_bv'))
    args=ap.parse_args()
    doc=json.loads(args.input.read_text())
    solved=json.loads(args.solver_result.read_text())['joint_key_uniqueness']
    if solved.get('second_result') != 'sat':
        raise ValueError('adaptive separator requires a SAT alternative model')
    k1=bytes.fromhex(solved['first_model_hex'])
    k2=bytes.fromhex(solved['alternative_model'])
    hypotheses={str(h['hypothesis_id']):h for h in doc['experiment']['hypotheses']}
    h1=hypotheses[solved['first_hypothesis_id']]
    h2=hypotheses[solved['alternative_hypothesis_id']]
    depth=int(doc['experiment']['depth'])
    reference=bytes.fromhex(doc['observations'][0]['plaintext_hex'])
    b1=AESGraphBuilder(depth,[z3.BitVecVal(v,8) for v in k1],args.sbox_encoding)
    b2=AESGraphBuilder(depth,[z3.BitVecVal(v,8) for v in k2],args.sbox_encoding)
    point=[z3.BitVec(f'mc_sep_p_{i}',8) for i in range(16)]
    base1='base1'; base2='base2'; query1='query1'; query2='query2'
    b1.build_for_plaintext(reference,base1); b2.build_for_plaintext(reference,base2)
    b1.build_for_plaintext(point,query1); b2.build_for_plaintext(point,query2)
    l1=leakage(b1,query1,base1,h1,depth); l2=leakage(b2,query2,base2,h2,depth)
    solver=z3.Solver()
    solver.add(*b1.sbox_constraints,*b2.sbox_constraints)
    solver.add(z3.Or(*[a != b for a,b in zip(l1,l2)]))
    solver.add(*domain_constraints(point,reference))
    for observation in doc['observations']:
        previous=bytes.fromhex(observation['plaintext_hex'])
        solver.add(z3.Or(*[point[i] != z3.BitVecVal(previous[i],8) for i in range(16)]))
    started=time.perf_counter(); result=solver.check(); elapsed=time.perf_counter()-started
    out={
      'schema':'mc9-anonymous-hypothesis-separator-v1',
      'status':str(result).lower(),
      'elapsed':elapsed,
      'reason_unknown':solver.reason_unknown() if result==z3.unknown else '',
      'synthesis_mode':'hypothesis_pair',
      'candidate1_hex':k1.hex(),
      'candidate2_hex':k2.hex(),
      'hypothesis1_id':solved['first_hypothesis_id'],
      'hypothesis2_id':solved['alternative_hypothesis_id'],
      'predicted_leakage_width':len(l1),
      'attack_used_ground_truth_mc9':False,
      'attack_used_hidden_key':False,
    }
    if result==z3.sat:
        model=solver.model()
        point_value=bytes(model.eval(v,model_completion=True).as_long() for v in point)
        out['plaintext_hex']=point_value.hex()
        out['predicted_leakage_model1']=[model.eval(v,model_completion=True).as_long() for v in l1]
        out['predicted_leakage_model2']=[model.eval(v,model_completion=True).as_long() for v in l2]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
