"""Sound round-1 byte-domain extraction for known mapping experiments.

Only values proven UNSAT are removed. SAT and UNKNOWN values are retained.
"""
import argparse,json
from pathlib import Path
import z3
from solve_known_mapping import build_problem,_timed_check

def validate_true_key_retained(domains,true_key): return all(true_key[i] in domains[str(i)] for i in range(16))
def make_domain_constraint_factory(domains):
    normalized={int(i):tuple(int(v) for v in values) for i,values in domains.items()}
    def factory(key):
        constraints=[]
        for i in range(16):
            values=normalized[i]
            constraints.append(z3.Or(*[key[i]==z3.BitVecVal(v,8) for v in values]) if values else z3.BoolVal(False))
        return constraints
    return factory
def extract_byte_domains(doc,timeout_ms=1000,sbox_encoding="uf_axiom"):
    key,builder,by_round=build_problem(doc,sbox_encoding,max_constraint_round=1); solver=z3.Solver(); solver.add(*builder.sbox_constraints); solver.add(*by_round.get(1,[])); domains={}; stats={"sat":0,"unsat":0,"unknown":0}
    for i in range(16):
        retained=[]
        for value in range(256):
            solver.push(); solver.add(key[i]==value); result,_,_,_=_timed_check(solver,timeout_ms); solver.pop(); status=str(result); stats[status]+=1
            if result!=z3.unsat:retained.append(value)
        domains[str(i)]=retained
    true_key=bytes.fromhex(doc["evaluator"]["true_key_hex"]); return {"schema":"aes-round1-byte-domains-v1","sbox_encoding":sbox_encoding,"timeout_ms":timeout_ms,"domains":domains,"stats":stats,"true_key_retained":validate_true_key_retained(domains,true_key),"soundness_rule":"remove only UNSAT; retain SAT and UNKNOWN"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output",required=True); ap.add_argument("--timeout-ms",type=int,default=1000); ap.add_argument("--sbox-encoding",choices=("uf_axiom","array_select","ite_bv"),default="uf_axiom"); a=ap.parse_args(); doc=json.loads(Path(a.input).read_text()); result=extract_byte_domains(doc,a.timeout_ms,a.sbox_encoding); Path(a.output).write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps({"stats":result["stats"],"true_key_retained":result["true_key_retained"]},indent=2))
if __name__=="__main__":main()
