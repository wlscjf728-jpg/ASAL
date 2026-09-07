import csv
import itertools
from pathlib import Path

# ShiftRows mapping: SR_out[4*c + r] = SB_out[4*((c+r)%4) + r]
# We can find the source byte for any SR byte:
# Let SR byte index be byte_sr = 4*c + r. Then c = byte_sr // 4, r = byte_sr % 4.
# The corresponding SB byte is byte_sb = 4*((c+r)%4) + r.
def get_sb_byte_for_sr(byte_sr):
    c = byte_sr // 4
    r = byte_sr % 4
    return 4 * ((c + r) % 4) + r

def is_redundant(cand_a, cand_b):
    stg_a, idx_a = cand_a["stage"], cand_a["bit_index"]
    stg_b, idx_b = cand_b["stage"], cand_b["bit_index"]
    byte_a, bit_a = cand_a["byte_index"], cand_a["bit_in_byte"]
    byte_b, bit_b = cand_b["byte_index"], cand_b["bit_in_byte"]
    
    # 1. MC and ARK at the same bit index are identical in differential mode
    if {stg_a, stg_b} == {"MC", "ARK"} and idx_a == idx_b:
        return True
        
    # 2. SB and SR that map to each other at the same bit position
    if {stg_a, stg_b} == {"SB", "SR"}:
        cand_sb = cand_a if stg_a == "SB" else cand_b
        cand_sr = cand_b if stg_a == "SB" else cand_a
        if cand_sb["bit_in_byte"] == cand_sr["bit_in_byte"]:
            expected_sb_byte = get_sb_byte_for_sr(cand_sr["byte_index"])
            if cand_sb["byte_index"] == expected_sb_byte:
                return True
                
    return False

def classify_pair(cand_a, cand_b):
    stg_a, idx_a = cand_a["stage"], cand_a["bit_index"]
    stg_b, idx_b = cand_b["stage"], cand_b["bit_index"]
    byte_a, bit_a = cand_a["byte_index"], cand_a["bit_in_byte"]
    byte_b, bit_b = cand_b["byte_index"], cand_b["bit_in_byte"]
    row_a, col_a = cand_a["row"], cand_a["column"]
    row_b, col_b = cand_b["row"], cand_b["column"]
    
    # Sort stages to make stage_pair canonical (e.g. SB-MC, never MC-SB)
    stage_order = {"SB": 0, "SR": 1, "MC": 2, "ARK": 3}
    if stage_order[stg_a] <= stage_order[stg_b]:
        c1, c2 = cand_a, cand_b
    else:
        c1, c2 = cand_b, cand_a
        
    stage_pair = f"{c1['stage']}-{c2['stage']}"
    
    same_stage = int(stg_a == stg_b)
    same_byte = int(byte_a == byte_b)
    same_row = int(row_a == row_b)
    same_col = int(col_a == col_b)
    same_bit_in_byte = int(bit_a == bit_b)
    
    # same_byte_farbit: same byte, bits are 0 and 7
    same_byte_farbit = int(same_byte and abs(bit_a - bit_b) == 7)
    
    # same_col_samebit: same column, same bit_in_byte, different bytes
    same_col_samebit = int(same_col and same_bit_in_byte and not same_byte)
    
    # same_col_diagbit: same column, row shift matches bit shift, different bytes
    # e.g., MC[0,0] and MC[1,1] in column 0 -> row_a=0, row_b=1, bit_a=0, bit_b=1
    same_col_diagbit = int(same_col and not same_byte and abs(row_a - row_b) == abs(bit_a - bit_b))
    
    # distinct_row: different columns, same row
    distinct_row = int(same_row and not same_col)
    
    # distinct_diag: diagonal relationship across different columns
    distinct_diag = int(not same_row and not same_col and abs(row_a - row_b) == abs(col_a - col_b) and abs(bit_a - bit_b) == abs(row_a - row_b))
    
    # scatter: fallback if it is a general scatter (different rows, different columns, no direct local relation)
    scatter = int(not same_row and not same_col and not distinct_diag)
    
    # redundancy check
    potentially_redundant = int(is_redundant(cand_a, cand_b))
    
    # Expected Risk Class
    is_a_early = cand_a["class"] == "early"
    is_b_early = cand_b["class"] == "early"
    
    if is_a_early and is_b_early:
        expected_risk = "early_only"
    elif not is_a_early and not is_b_early:
        if potentially_redundant:
            expected_risk = "redundant_late"
        elif same_col and (same_col_samebit or same_col_diagbit):
            expected_risk = "weak_same_column"
        else:
            expected_risk = "late_only"
    else:
        if potentially_redundant:
            expected_risk = "redundant_late"
        else:
            expected_risk = "early_late_mixed"
            
    return {
        "pair_id": f"{c1['candidate_id']}__{c2['candidate_id']}",
        "cand_a": c1['candidate_id'],
        "cand_b": c2['candidate_id'],
        "stage_pair": stage_pair,
        "same_stage": same_stage,
        "same_byte": same_byte,
        "same_row": same_row,
        "same_column": same_col,
        "same_bit_in_byte": same_bit_in_byte,
        "same_byte_farbit": same_byte_farbit,
        "same_col_samebit": same_col_samebit,
        "same_col_diagbit": same_col_diagbit,
        "distinct_row": distinct_row,
        "distinct_diag": distinct_diag,
        "scatter": scatter,
        "potentially_redundant": potentially_redundant,
        "expected_risk_class": expected_risk
    }

def read_candidate_map(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def main():
    base_dir = Path(__file__).parent.parent
    core_candidates = read_candidate_map(base_dir / "results" / "candidate_map_core384.csv")
    ext_candidates = read_candidate_map(base_dir / "results" / "candidate_map_extended512.csv")
    
    # Process core384
    core_pairs = []
    # Convert types
    for c in core_candidates:
        c["bit_index"] = int(c["bit_index"])
        c["byte_index"] = int(c["byte_index"])
        c["row"] = int(c["row"])
        c["column"] = int(c["column"])
        c["bit_in_byte"] = int(c["bit_in_byte"])
        
    for c1, c2 in itertools.combinations(core_candidates, 2):
        core_pairs.append(classify_pair(c1, c2))
        
    # Process extended512
    ext_pairs = []
    for c in ext_candidates:
        c["bit_index"] = int(c["bit_index"])
        c["byte_index"] = int(c["byte_index"])
        c["row"] = int(c["row"])
        c["column"] = int(c["column"])
        c["bit_in_byte"] = int(c["bit_in_byte"])
        
    for c1, c2 in itertools.combinations(ext_candidates, 2):
        ext_pairs.append(classify_pair(c1, c2))
        
    headers = [
        "pair_id", "cand_a", "cand_b", "stage_pair", "same_stage", "same_byte",
        "same_row", "same_column", "same_bit_in_byte", "same_byte_farbit",
        "same_col_samebit", "same_col_diagbit", "distinct_row", "distinct_diag",
        "scatter", "potentially_redundant", "expected_risk_class"
    ]
    
    with open(base_dir / "results" / "pair_structural_map_core384.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(core_pairs)
        
    with open(base_dir / "results" / "pair_structural_map_extended512.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(ext_pairs)

if __name__ == "__main__":
    main()
    print("Pair structural maps generated successfully.")
