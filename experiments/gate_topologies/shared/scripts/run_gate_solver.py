"""Run the existing Attack 8 Z3 solver on a gate-level bridge transcript."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'temporal_key_recovery'/'scripts'))
from solve_known_mapping import solve_document

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True,type=Path); ap.add_argument('--key',required=True); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--label',required=True); a=ap.parse_args()
 doc=json.loads(a.input.read_text()); doc['evaluator']={'true_key_hex':a.key}
 started=time.perf_counter(); row=solve_document(doc,first_timeout_ms=0,second_timeout_ms=0,diagnostic_timeout_ms=0,sbox_encoding='uf_axiom'); row['bridge_label']=a.label; row['input_transcript']=str(a.input); row['wall_time_seconds']=time.perf_counter()-started
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(row,indent=2)+'\n'); print(json.dumps(row,indent=2))
if __name__=='__main__': main()
