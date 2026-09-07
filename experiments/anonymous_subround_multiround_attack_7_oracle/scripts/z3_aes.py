"""Shared Z3 AES-128 graph with selectable S-box encodings."""
import z3
from aes_ref import SBOX, RCON


UF_SBOX=z3.Function("AES_SBOX_UF",z3.BitVecSort(8),z3.BitVecSort(8))
UF_AXIOMS=[UF_SBOX(z3.BitVecVal(i,8))==z3.BitVecVal(v,8) for i,v in enumerate(SBOX)]

class SBoxBackend:
    def __init__(self,encoding):
        if encoding not in {"uf_axiom","array_select","ite_bv"}: raise ValueError(f"unsupported S-box encoding: {encoding}")
        self.encoding=encoding; self.constraints=[]
        if encoding=="uf_axiom":
            self.uf=UF_SBOX
            self.constraints=UF_AXIOMS
        elif encoding=="array_select":
            arr=z3.K(z3.BitVecSort(8),z3.BitVecVal(0,8))
            for i,v in enumerate(SBOX): arr=z3.Store(arr,z3.BitVecVal(i,8),z3.BitVecVal(v,8))
            self.array=arr
    def lookup(self,x):
        if self.encoding=="uf_axiom": return self.uf(x)
        if self.encoding=="array_select": return z3.Select(self.array,x)
        value=z3.BitVecVal(SBOX[-1],8)
        for i in range(254,-1,-1): value=z3.If(x==z3.BitVecVal(i,8),z3.BitVecVal(SBOX[i],8),value)
        return value

def sbox_axioms(): return UF_AXIOMS

def xtime(x): return (x<<1)^z3.If(z3.Extract(7,7,x)==1,z3.BitVecVal(0x1b,8),z3.BitVecVal(0,8))
def sr(s):
    out=[None]*16
    for r in range(4):
        for c in range(4): out[4*c+r]=s[4*((c+r)%4)+r]
    return out
def mc(s):
    out=[None]*16
    for c in range(4):
        o=4*c; t=s[o]^s[o+1]^s[o+2]^s[o+3]
        out[o]=s[o]^t^xtime(s[o]^s[o+1]); out[o+1]=s[o+1]^t^xtime(s[o+1]^s[o+2])
        out[o+2]=s[o+2]^t^xtime(s[o+2]^s[o+3]); out[o+3]=s[o+3]^t^xtime(s[o+3]^s[o])
    return out
def ark(s,k): return [a^b for a,b in zip(s,k)]
def select_bit(state,bit_index): return z3.Extract(bit_index%8,bit_index%8,state[bit_index//8])

def expand_key(key,lookup):
    keys=[key]
    for n in range(1,11):
        p=keys[-1]; t=[lookup(p[13])^z3.BitVecVal(RCON[n-1],8),lookup(p[14]),lookup(p[15]),lookup(p[12])]; q=[None]*16
        for i in range(4): q[i]=p[i]^t[i]
        for i in range(4,16): q[i]=p[i]^q[i-4]
        keys.append(q)
    return keys

class AESGraphBuilder:
    def __init__(self,depth,key=None,sbox_encoding="uf_axiom"):
        if not 1 <= depth <= 4: raise ValueError("depth must be 1..4")
        self.depth=depth; self.key=key or [z3.BitVec(f"k_{i}",8) for i in range(16)]
        self.sbox_encoding=sbox_encoding; self.sbox=SBoxBackend(sbox_encoding); self.sbox_constraints=self.sbox.constraints
        self.round_keys=expand_key(self.key,self.sbox.lookup); self.graphs={}; self.graph_build_count=0
    def build_for_plaintext(self,plaintext,query_id):
        if query_id in self.graphs:return self.graphs[query_id]
        state=ark([z3.BitVecVal(b,8) for b in plaintext],self.round_keys[0]); rounds={}
        for rnd in range(1,self.depth+1):
            a=[self.sbox.lookup(x) for x in state]; b=sr(a); c=mc(b); d=ark(c,self.round_keys[rnd]); rounds[rnd]={"SB":a,"SR":b,"MC":c,"ARK":d}; state=d
        self.graphs[query_id]=rounds; self.graph_build_count+=1; return rounds
