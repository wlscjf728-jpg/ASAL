#!/usr/bin/env python3
"""Restrict an anonymous transcript to hypotheses surviving a prior solve."""
from __future__ import annotations
import argparse,json,copy
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--transcript',type=Path,required=True); ap.add_argument('--solver-result',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    doc=json.loads(a.transcript.read_text()); solved=json.loads(a.solver_result.read_text())
    surviving=solved.get('surviving_hypotheses',[])
    if not surviving: raise ValueError('no surviving hypotheses')
    ids={str(h['hypothesis_id']) for h in surviving}
    out=copy.deepcopy(doc)
    out['experiment']['hypotheses']=[h for h in out['experiment']['hypotheses'] if str(h['hypothesis_id']) in ids]
    out['experiment']['attribution']={'source_solver':str(a.solver_result),'previous_surviving_hypothesis_count':len(surviving)}
    out['schema']='aes-sparse-gate-hypothesis-bridge-v2'
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'input_hypotheses':len(doc['experiment']['hypotheses']),'surviving_hypotheses':len(out['experiment']['hypotheses']),'query_count':len(out['observations'])},indent=2))
if __name__=='__main__':main()
