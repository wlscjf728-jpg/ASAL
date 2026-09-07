#!/usr/bin/env python3
"""Append one anonymous hypothesis transcript query to an existing transcript."""
from __future__ import annotations
import argparse, copy, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',type=Path,required=True)
    ap.add_argument('--extra',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    base=json.loads(args.base.read_text())
    extra=json.loads(args.extra.read_text())
    if base['experiment']['hypotheses'] != extra['experiment']['hypotheses']:
        raise ValueError('base and extra hypothesis sets differ')
    add=[o for o in extra['observations'] if int(o['query_id']) != 0]
    if len(add)!=1:
        raise ValueError('extra transcript must contain exactly one non-reference observation')
    out=copy.deepcopy(base)
    next_id=max(int(o['query_id']) for o in out['observations'])+1
    item=copy.deepcopy(add[0]); item['query_id']=next_id
    out['observations'].append(item)
    out['schema']='aes-sparse-gate-hypothesis-adaptive-bridge-v1'
    out['experiment'].setdefault('adaptive',{})['added_query_id']=next_id
    out['experiment']['adaptive']['source_observation']=str(args.extra)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'base_queries':len(base['observations']),'final_queries':len(out['observations']),'added_plaintext':item['plaintext_hex'],'added_query_id':next_id},indent=2))
if __name__=='__main__': main()
