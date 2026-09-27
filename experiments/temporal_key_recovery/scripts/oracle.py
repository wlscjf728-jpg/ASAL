"""Evaluator oracle for sparse, repeated subround taps."""
import argparse, json
from pathlib import Path
from aes_ref import encrypt_with_trace
MODES = {"absolute", "differential", "combined"}

def _block(value, name):
    out = value if isinstance(value, bytes) else bytes.fromhex(value)
    if len(out) != 16: raise ValueError(f"{name} must be 16 bytes")
    return out

def generate_observation(key, taps, plaintexts, depth, mode):
    key = _block(key, "key")
    pts = [_block(p, "plaintext") for p in plaintexts]
    if mode not in MODES or not 1 <= depth <= 4 or not pts: raise ValueError("invalid mode/depth/plaintexts")
    ids = [t["tap_id"] for t in taps]
    if len(ids) != len(set(ids)): raise ValueError("tap_id must be unique")
    raw=[]
    for plaintext in pts:
        trace=encrypt_with_trace(plaintext,key)["rounds"]
        raw.append({str(r): {t["tap_id"]: (trace[r][t["stage"]][int(t["bit_index"])//8] >> (int(t["bit_index"])%8)) & 1 for t in taps}
                    for r in range(1,depth+1)})
    observations=[]
    for qi,p in enumerate(pts):
        rounds={}
        for r in range(1,depth+1):
            rounds[str(r)]={}
            for t in taps:
                tid=t["tap_id"]; a=raw[qi][str(r)][tid]; d=a^raw[0][str(r)][tid]; v={}
                if mode in ("absolute","combined"): v["absolute"]=a
                if mode in ("differential","combined"): v["differential"]=d
                rounds[str(r)][tid]=v
        observations.append({"query_id":qi,"plaintext_hex":p.hex(),"rounds":rounds})
    return {"schema":"aes-sparse-oracle-v1",
            "experiment":{"depth":depth,"mode":mode,"base_query_id":0,"taps":taps},
            "observations":observations,"evaluator":{"true_key_hex":key.hex()}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--key",required=True); ap.add_argument("--taps",required=True); ap.add_argument("--plaintexts",required=True); ap.add_argument("--depth",type=int,required=True); ap.add_argument("--mode",choices=sorted(MODES),required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    doc=generate_observation(a.key,json.loads(Path(a.taps).read_text()),json.loads(Path(a.plaintexts).read_text()),a.depth,a.mode)
    Path(a.output).write_text(json.dumps(doc,indent=2)+"\n")
if __name__ == "__main__": main()
