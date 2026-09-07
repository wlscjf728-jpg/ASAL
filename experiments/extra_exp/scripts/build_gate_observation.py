"""Convert anonymous gate scan-out into the existing MC tap observation schema."""
from __future__ import annotations
import argparse, json, sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'extra_exp/scripts'))
import semantic_reference as sr
sr.sbox=lru_cache(256)(sr.sbox)

def parse_capture(path):
 rows={}
 for line in path.read_text().splitlines():
  f=line.split(); q,s,vector=(f[0],f[1],f[-1]); rows[(int(q),int(s))]=int(vector,16)
 return rows

def parse_queries(path):
 return {int(q):bytes.fromhex(p) for q,p in (x.split() for x in path.read_text().splitlines())}

def build(capture,queries,slot,key_hex=None):
 rows=parse_capture(capture); pts=parse_queries(queries); qids=sorted(pts)
 obs=[]
 for q in qids:
  rounds={}
  for r,s in ((1,1),(2,3)):
   bit=(rows[(q,s)]>>slot)&1; base=(rows[(0,s)]>>slot)&1
   rounds[str(r)]={"t0":{"differential":bit^base}}
  obs.append({"query_id":q,"plaintext_hex":pts[q].hex(),"rounds":rounds})
 doc={"schema":"aes-sparse-gate-bridge-v1","experiment":{"depth":2,"mode":"differential","base_query_id":0,"taps":[{"tap_id":"t0","candidate_id":"MC_9","stage":"MC","bit_index":9}],"source":{"scan_slot":slot,"schedule_to_round":{"1":1,"3":2},"anonymous_input":True}},"observations":obs}
 if key_hex: doc["evaluator"]={"true_key_hex":key_hex}
 return doc

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--capture',required=True,type=Path); ap.add_argument('--queries',required=True,type=Path); ap.add_argument('--slot',required=True,type=int); ap.add_argument('--output',required=True,type=Path); ap.add_argument('--key'); ap.add_argument('--reference-check',action='store_true'); a=ap.parse_args()
 doc=build(a.capture,a.queries,a.slot,a.key); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(doc,indent=2)+'\n')
 if a.reference_check:
  if not a.key: raise SystemExit('--key required for reference check')
  k=bytes.fromhex(a.key); rows=parse_capture(a.capture); pts=parse_queries(a.queries); mismatches=[]
  for q,p in pts.items():
   for r,s in ((1,1),(2,3)):
    observed=((rows[(q,s)]>>a.slot)&1)^((rows[(0,s)]>>a.slot)&1)
    expected=sr.mc_bit(p,k,r,9)^sr.mc_bit(pts[0],k,r,9)
    if observed != expected: mismatches.append({'query_id':q,'round':r,'observed':observed,'expected':expected})
  check={'query_count':len(pts),'slot':a.slot,'round1_schedule':1,'round2_schedule':3,'bitwise_match':not mismatches,'mismatch_count':len(mismatches),'mismatches':mismatches[:20]}
  cp=a.output.with_name(a.output.stem+'_reference_check.json'); cp.write_text(json.dumps(check,indent=2)+'\n'); print(json.dumps(check,indent=2))
 print(json.dumps({'output':str(a.output),'observations':len(doc['observations']),'slot':a.slot},indent=2))
if __name__=='__main__': main()
