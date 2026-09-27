"""Known exact-mapping AES K0 uniqueness evaluator."""
import argparse,csv,json,time
from pathlib import Path
import z3
from z3_aes import AESGraphBuilder,select_bit
KEY_COLUMNS=((0,1,2,3),(4,5,6,7),(8,9,10,11),(12,13,14,15))

def _status(result):return str(result).lower()
def _timed_check(solver,timeout_ms):
    solver.set(timeout=timeout_ms); start=time.perf_counter(); result=solver.check(); elapsed=time.perf_counter()-start; reason=solver.reason_unknown() if result==z3.unknown else ""; timed_out=result==z3.unknown and ("timeout" in reason.lower() or "canceled" in reason.lower() or elapsed*1000>=timeout_ms*.95); return result,elapsed,timed_out,reason
def _classification(result): return "fixed" if result==z3.unsat else "free" if result==z3.sat else "unknown"

def build_problem(doc,sbox_encoding="uf_axiom",max_constraint_round=None):
    exp=doc["experiment"]; depth=int(exp["depth"]); mode=exp["mode"]; taps={t["tap_id"]:t for t in exp["taps"]}; key=[z3.BitVec(f"k_{i}",8) for i in range(16)]; builder=AESGraphBuilder(depth,key,sbox_encoding)
    for obs in doc["observations"]:builder.build_for_plaintext(bytes.fromhex(obs["plaintext_hex"]),str(obs["query_id"]))
    constraints={r:[] for r in range(1,depth+1)}; base=str(exp.get("base_query_id",0)); limit=max_constraint_round or depth
    for obs in doc["observations"]:
        qid=str(obs["query_id"])
        for rnd in range(1,min(depth,limit)+1):
            for tid,tap in taps.items():
                value=obs["rounds"][str(rnd)][tid]; qbit=select_bit(builder.graphs[qid][rnd][tap["stage"]],int(tap["bit_index"])); bbit=select_bit(builder.graphs[base][rnd][tap["stage"]],int(tap["bit_index"]))
                if mode in ("absolute","combined"):constraints[rnd].append(qbit==z3.BitVecVal(int(value["absolute"]),1))
                if mode in ("differential","combined"):constraints[rnd].append((qbit^bbit)==z3.BitVecVal(int(value["differential"]),1))
    return key,builder,constraints

def diagnostics_after_second(solver,key,candidate,second_status,alternative,diagnostic_timeout_ms):
    if second_status == "unsat":
        return ({str(i):"fixed" for i in range(16)}, {str(i):"fixed" for i in range(4)})
    byte_summary={str(i):"unknown" for i in range(16)}; column_summary={str(i):"unknown" for i in range(4)}
    if alternative is not None:
        for i in range(16):
            if alternative[i]!=candidate[i]: byte_summary[str(i)]="free"
        for c,indices in enumerate(KEY_COLUMNS):
            if any(alternative[i]!=candidate[i] for i in indices): column_summary[str(c)]="free"
    deadline=time.perf_counter()+diagnostic_timeout_ms/1000.0
    # Columns first: a fixed column proves all four constituent bytes fixed.
    for column,indices in enumerate(KEY_COLUMNS):
        if column_summary[str(column)]!="unknown": continue
        remaining=max(0,int((deadline-time.perf_counter())*1000))
        if remaining<=0: break
        solver.push(); solver.add(z3.Or(*[key[i]!=candidate[i] for i in indices])); result,_,_,_=_timed_check(solver,remaining); solver.pop(); status=_classification(result); column_summary[str(column)]=status
        if status=="fixed":
            for i in indices: byte_summary[str(i)]="fixed"
    for i in range(16):
        if byte_summary[str(i)]!="unknown": continue
        remaining=max(0,int((deadline-time.perf_counter())*1000))
        if remaining<=0: break
        solver.push(); solver.add(key[i]!=candidate[i]); result,_,_,_=_timed_check(solver,remaining); solver.pop(); byte_summary[str(i)]=_classification(result)
    for column,indices in enumerate(KEY_COLUMNS):
        values=[byte_summary[str(i)] for i in indices]
        if all(v=="fixed" for v in values): column_summary[str(column)]="fixed"
        elif any(v=="free" for v in values): column_summary[str(column)]="free"
    return byte_summary,column_summary

def solve_document(doc,first_timeout_ms=60000,second_timeout_ms=60000,diagnostic_timeout_ms=5000,sbox_encoding="uf_axiom",domain_constraints=None,domain_metadata=None):
    key,builder,by_round=build_problem(doc,sbox_encoding); solver=z3.Solver(); solver.add(*builder.sbox_constraints)
    if domain_constraints:solver.add(*domain_constraints(key))
    for rnd in sorted(by_round):solver.add(*by_round[rnd])
    true_key=bytes.fromhex(doc["evaluator"]["true_key_hex"]); solver.push(); solver.add(*[key[i]==true_key[i] for i in range(16)]); tr,_,tr_to,tr_reason=_timed_check(solver,diagnostic_timeout_ms); solver.pop()
    first,t1,to1,first_reason=_timed_check(solver,first_timeout_ms)
    unknown_bytes={str(i):"unknown" for i in range(16)}; unknown_columns={str(i):"unknown" for i in range(4)}
    row={"first_result":_status(first),"second_result":"not_run","first_time":t1,"second_time":0.0,"first_model":"","first_model_hex":"","alternative_model":"","first_model_correct":False,"true_key_satisfiable":_status(tr),"true_key_timeout":tr_to,"second_timeout":False,"timeout":to1,"z3_reason_unknown":first_reason,"byte_diagnostic_summary":json.dumps(unknown_bytes,sort_keys=True),"column_diagnostic_summary":json.dumps(unknown_columns,sort_keys=True),"fixed_bytes":"[]","free_bytes":"[]","unknown_bytes":json.dumps(list(range(16))),"first_timeout":to1,"classification":"undecided","confirmed_unique_candidate":False,"sbox_encoding":sbox_encoding,"domain_true_key_retained":(domain_metadata or {}).get("true_key_retained","")}
    if first!=z3.sat:
        row["classification"]="undecided" if first==z3.unknown else "inconsistent"; return row
    model=solver.model(); candidate=bytes(model.eval(key[i],model_completion=True).as_long() for i in range(16)); row["first_model"]=candidate.hex(); row["first_model_hex"]=candidate.hex(); row["first_model_correct"]=candidate==true_key
    solver.push(); solver.add(z3.Or(*[key[i]!=candidate[i] for i in range(16)])); second,t2,to2,second_reason=_timed_check(solver,second_timeout_ms); alternative=None
    if second==z3.sat:
        second_model=solver.model(); alternative=bytes(second_model.eval(key[i],model_completion=True).as_long() for i in range(16)); row["alternative_model"]=alternative.hex()
    solver.pop(); row.update(second_result=_status(second),second_time=t2,second_timeout=to2,timeout=to1 or to2,z3_reason_unknown=second_reason if second==z3.unknown else first_reason); row["classification"]="full_key_unique" if second==z3.unsat else "ambiguity" if second==z3.sat else "undecided"; row["confirmed_unique_candidate"]=first==z3.sat and second==z3.unsat
    byte_summary,column_summary=diagnostics_after_second(solver,key,candidate,_status(second),alternative,diagnostic_timeout_ms); row["byte_diagnostic_summary"]=json.dumps(byte_summary,sort_keys=True); row["column_diagnostic_summary"]=json.dumps(column_summary,sort_keys=True); row["fixed_bytes"]=json.dumps([int(i) for i,v in byte_summary.items() if v=="fixed"]); row["free_bytes"]=json.dumps([int(i) for i,v in byte_summary.items() if v=="free"]); row["unknown_bytes"]=json.dumps([int(i) for i,v in byte_summary.items() if v=="unknown"]); return row

def write_csv(row,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); exists=path.exists()
    with path.open("a",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(row));
        if not exists:w.writeheader()
        w.writerow(row)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--mapping"); ap.add_argument("--output",required=True); ap.add_argument("--first-timeout-ms",type=int,default=60000); ap.add_argument("--second-timeout-ms",type=int,default=60000); ap.add_argument("--diagnostic-timeout-ms",type=int,default=5000); ap.add_argument("--sbox-encoding",choices=("uf_axiom","array_select","ite_bv"),default="uf_axiom"); a=ap.parse_args(); doc=json.loads(Path(a.input).read_text())
    if a.mapping and json.loads(Path(a.mapping).read_text())!=doc["experiment"]["taps"]:raise ValueError("known mapping differs from oracle tap list")
    row=solve_document(doc,a.first_timeout_ms,a.second_timeout_ms,a.diagnostic_timeout_ms,a.sbox_encoding); write_csv(row,a.output); print(json.dumps(row,indent=2))
if __name__=="__main__":main()
