import csv
import itertools
import random
from pathlib import Path

def load_unique_pairs(base_dir):
    unique_pairs = set()
    
    # 1. Load from imported prior results
    prior_path = base_dir / "results" / "prior_2bit_results_imported.csv"
    if prior_path.exists():
        with open(prior_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If unique_count / seeds_total is high, it is unique
                u_cnt = int(row["unique_count"])
                s_tot = int(row["seeds_total"])
                if s_tot > 0 and (u_cnt / s_tot >= 0.8):
                    # Sort candidates
                    c1, c2 = row["stage_a"] + "_" + row["bit_a"], row["stage_b"] + "_" + row["bit_b"]
                    key = tuple(sorted([c1, c2]))
                    unique_pairs.add(key)
                    
    # 2. Load from two_bit_risk_map.csv if it exists (new runs)
    risk_map_path = base_dir / "results" / "two_bit_risk_map.csv"
    if risk_map_path.exists():
        with open(risk_map_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                u_cnt = int(row["unique_count"])
                s_tot = int(row["seeds_total"])
                if s_tot > 0 and (u_cnt / s_tot >= 0.8):
                    c1 = row["stage_a"] + "_" + row["bit_a"]
                    c2 = row["stage_b"] + "_" + row["bit_b"]
                    key = tuple(sorted([c1, c2]))
                    unique_pairs.add(key)
                    
    return unique_pairs

def get_candidates(base_dir):
    cands = []
    with open(base_dir / "results" / "candidate_map_extended512.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cands.append(row["candidate_id"])
    return cands

def main():
    base_dir = Path(__file__).parent.parent
    unique_pairs = load_unique_pairs(base_dir)
    cands = get_candidates(base_dir)
    
    print(f"Loaded {len(unique_pairs)} confirmed unique 2-bit pairs.")
    
    # Stratified candidate pools:
    # 1. Early only (SB, SR)
    early_cands = [c for c in cands if c.startswith("SB_") or c.startswith("SR_")]
    # 2. Weak late candidates (same column/redundant)
    # We can select some MC, ARK candidates that are in column 0
    col0_cands = []
    with open(base_dir / "results" / "candidate_map_extended512.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["column"] == "0" and row["stage"] in ("MC", "ARK"):
                col0_cands.append(row["candidate_id"])
                
    # Select 3-bit hard cases
    selected_3bit = []
    # 3.1. Early only combinations (budget: 60)
    early_combos_3 = list(itertools.combinations(early_cands, 3))
    random.Random(42).shuffle(early_combos_3)
    
    for combo in early_combos_3:
        if len(selected_3bit) >= 60:
            break
        # Check all 3 sub-pairs
        pairs = list(itertools.combinations(combo, 2))
        has_unique_subset = False
        for p in pairs:
            key = tuple(sorted(p))
            if key in unique_pairs:
                has_unique_subset = True
                break
        if not has_unique_subset:
            selected_3bit.append({
                "case_id": f"3bit_early__{combo[0]}__{combo[1]}__{combo[2]}",
                "cand_a": combo[0],
                "cand_b": combo[1],
                "cand_c": combo[2],
                "cand_d": "",
                "topology_class": "early_only",
                "selection_reason": "early_only_hard_case"
            })
            
    # 3.2. Same-column/redundant late combinations (budget: 40)
    col0_combos_3 = list(itertools.combinations(col0_cands, 3))
    random.Random(43).shuffle(col0_combos_3)
    for combo in col0_combos_3:
        if len(selected_3bit) >= 100:
            break
        pairs = list(itertools.combinations(combo, 2))
        has_unique_subset = False
        for p in pairs:
            key = tuple(sorted(p))
            if key in unique_pairs:
                has_unique_subset = True
                break
        if not has_unique_subset:
            selected_3bit.append({
                "case_id": f"3bit_weak_late__{combo[0]}__{combo[1]}__{combo[2]}",
                "cand_a": combo[0],
                "cand_b": combo[1],
                "cand_c": combo[2],
                "cand_d": "",
                "topology_class": "weak_same_column",
                "selection_reason": "weak_same_column_hard_case"
            })
            
    # Select 4-bit hard cases
    selected_4bit = []
    # 4.1. Early only combinations (budget: 30)
    early_combos_4 = list(itertools.combinations(early_cands, 4))
    random.Random(44).shuffle(early_combos_4)
    for combo in early_combos_4:
        if len(selected_4bit) >= 30:
            break
        pairs = list(itertools.combinations(combo, 2))
        has_unique_subset = False
        for p in pairs:
            key = tuple(sorted(p))
            if key in unique_pairs:
                has_unique_subset = True
                break
        if not has_unique_subset:
            selected_4bit.append({
                "case_id": f"4bit_early__{combo[0]}__{combo[1]}__{combo[2]}__{combo[3]}",
                "cand_a": combo[0],
                "cand_b": combo[1],
                "cand_c": combo[2],
                "cand_d": combo[3],
                "topology_class": "early_only",
                "selection_reason": "early_only_hard_case"
            })
            
    # 4.2. Same-column/redundant late combinations (budget: 15)
    col0_combos_4 = list(itertools.combinations(col0_cands, 4))
    random.Random(45).shuffle(col0_combos_4)
    for combo in col0_combos_4:
        if len(selected_4bit) >= 45:
            break
        pairs = list(itertools.combinations(combo, 2))
        has_unique_subset = False
        for p in pairs:
            key = tuple(sorted(p))
            if key in unique_pairs:
                has_unique_subset = True
                break
        if not has_unique_subset:
            selected_4bit.append({
                "case_id": f"4bit_weak_late__{combo[0]}__{combo[1]}__{combo[2]}__{combo[3]}",
                "cand_a": combo[0],
                "cand_b": combo[1],
                "cand_c": combo[2],
                "cand_d": combo[3],
                "topology_class": "weak_same_column",
                "selection_reason": "weak_same_column_hard_case"
            })
            
    # Save files
    configs_dir = base_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    
    headers = ["case_id", "cand_a", "cand_b", "cand_c", "cand_d", "topology_class", "selection_reason"]
    
    with open(configs_dir / "selected_3bit_hard_cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(selected_3bit)
        
    with open(configs_dir / "selected_4bit_hard_cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(selected_4bit)
        
    print(f"Generated {len(selected_3bit)} hard 3-bit cases and {len(selected_4bit)} hard 4-bit cases.")

if __name__ == "__main__":
    main()
