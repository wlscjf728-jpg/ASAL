"""Append a newly measured gate-level query to a bridge transcript."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--base',required=True,type=Path); ap.add_argument('--extra',required=True,type=Path); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--key'); a=ap.parse_args()
 base=json.loads(a.base.read_text()); extra=json.loads(a.extra.read_text()); out=json.loads(json.dumps(base))
 next_id=max(int(o['query_id']) for o in out['observations'])+1
 add=next(o for o in extra['observations'] if int(o['query_id']) != 0)
 add['query_id']=next_id; out['observations'].append(add)
 out['schema']='aes-sparse-gate-bridge-adaptive-v1'; out.setdefault('experiment',{}).setdefault('adaptive',{})['added_query_id']=next_id; out['experiment']['adaptive']['source_observation']=str(a.extra)
 if a.key: out['evaluator']={'true_key_hex':a.key}
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps({'base_queries':len(base['observations']),'final_queries':len(out['observations']),'added_plaintext':add['plaintext_hex'],'added_query_id':next_id},indent=2))
if __name__=='__main__':main()
