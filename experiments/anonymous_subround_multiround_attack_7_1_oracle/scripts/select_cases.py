import csv
import random
from pathlib import Path

# Explicit reproduction anchors to ensure identical mapping to Attack 6 results
REPRODUCTION_ANCHORS = {
    # mc_same_byte_2 [0,1]
    "MC_0__MC_1": "prior_strong_reproduction",
    "MC_0__MC_7": "prior_strong_reproduction", # mc_same_byte_farbit_2
    "MC_0__MC_41": "prior_strong_reproduction", # mc_distinct_diag_2 (Wait, MC_41 is byte 5 bit 1)
    "MC_0__MC_32": "prior_strong_reproduction", # mc_distinct_row0_2 (byte 4 bit 0)
    "MC_0__MC_8": "weak_same_column", # mc_same_col_samebit_2 (byte 1 bit 0)
    "MC_0__MC_24": "weak_same_column", # mc_same_col_farbyte_2 (byte 3 bit 0)
    "MC_0__MC_9": "weak_same_column", # mc_same_col_diagbit_2 (byte 1 bit 1)
    
    # ARK same byte and distinct
    "ARK_0__ARK_1": "prior_strong_reproduction", # ark_same_byte_2
    "ARK_0__ARK_32": "prior_strong_reproduction", # ark_distinct_row0_2
    "ARK_0__ARK_41": "prior_strong_reproduction", # ark_distinct_diag_2
    "ARK_0__ARK_8": "weak_same_column", # ark_same_col_samebit_2
    "ARK_0__ARK_9": "weak_same_column", # ark_same_col_diagbit_2
    
    # Early only
    "SB_0__SB_1": "prior_weak_reproduction", # sb_same_byte_2
    "SB_0__SB_32": "prior_weak_reproduction", # sb_distinct_row0_2
    "SB_0__SB_41": "prior_weak_reproduction", # sb_distinct_diag_2
    "SR_0__SR_1": "prior_weak_reproduction", # sr_same_byte_2
    "SR_0__SR_32": "prior_weak_reproduction", # sr_distinct_row0_2
    "SR_0__SR_41": "prior_weak_reproduction", # sr_distinct_diag_2
    
    # Mixed late
    "MC_0__ARK_1": "prior_strong_reproduction", # mc0_ark1_same_byte_like
    "MC_0__ARK_0": "redundancy_test", # mc0_ark0_same_bit
    "MC_0__ARK_8": "prior_strong_reproduction", # mc0_ark8_same_column
    "MC_0__ARK_9": "weak_same_column", # mc0_ark9_same_col_diag
    "MC_0__ARK_32": "prior_strong_reproduction", # mc0_ark32_distinct_row
    "MC_0__ARK_41": "prior_strong_reproduction", # mc0_ark41_distinct_diag
    
    # Mixed early + late
    "SB_0__MC_0": "redundancy_test", # sb0_mc0
    "SB_0__MC_1": "redundancy_test", # sb0_mc1
    "SB_0__MC_32": "early_late_complementarity", # sb0_mc32
    "SB_0__MC_41": "early_late_complementarity", # sb0_mc41
    "SR_0__MC_0": "redundancy_test", # sr0_mc0
    "SR_0__MC_1": "redundancy_test", # sr0_mc1
    "SR_0__MC_32": "early_late_complementarity", # sr0_mc32
    "SR_0__MC_41": "early_late_complementarity", # sr0_mc41
    "SB_0__ARK_0": "redundancy_test", # sb0_ark0
    "SB_0__ARK_1": "redundancy_test", # sb0_ark1
    "SR_0__ARK_0": "redundancy_test", # sr0_ark0
    "SR_0__ARK_1": "redundancy_test", # sr0_ark1
    
    # Early cross stage
    "SB_0__SR_0": "prior_weak_reproduction", # sb0_sr0
    "SB_0__SR_1": "prior_weak_reproduction", # sb0_sr1
    "SB_0__SR_8": "prior_weak_reproduction", # sb0_sr8
    "SB_0__SR_32": "prior_weak_reproduction", # sb0_sr32
    "SB_0__SR_41": "prior_weak_reproduction", # sb0_sr41
}

def main():
    base_dir = Path(__file__).parent.parent
    configs_dir = base_dir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all pairs
    pairs = []
    with open(base_dir / "results" / "pair_structural_map_extended512.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append(row)
            
    # Group pairs by stage_pair
    by_stage_pair = {}
    for p in pairs:
        sp = p["stage_pair"]
        if sp not in by_stage_pair:
            by_stage_pair[sp] = []
        by_stage_pair[sp].append(p)
        
    # Budget allocation:
    # SB-SB: 20
    # SB-SR: 20
    # SR-SR: 20
    # SB-MC: 30
    # SR-MC: 30
    # MC-MC: 40
    # SB-ARK: 10
    # SR-ARK: 10
    # MC-ARK: 20
    # ARK-ARK: 20
    budgets = {
        "SB-SB": 20, "SB-SR": 20, "SR-SR": 20,
        "SB-MC": 30, "SR-MC": 30, "MC-MC": 40,
        "SB-ARK": 10, "SR-ARK": 10, "MC-ARK": 20, "ARK-ARK": 20
    }
    
    selected_pairs = []
    selected_ids = set()
    
    # First, always add the reproduction anchors
    for p in pairs:
        pid = p["pair_id"]
        if pid in REPRODUCTION_ANCHORS:
            p["selection_reason"] = REPRODUCTION_ANCHORS[pid]
            selected_pairs.append(p)
            selected_ids.add(pid)
            
    # Set seed for reproducibility
    rng = random.Random(42)
    
    # Sample from each stage pair to satisfy budget
    for sp, budget in budgets.items():
        candidates = by_stage_pair.get(sp, [])
        # Exclude already selected anchors
        candidates = [c for c in candidates if c["pair_id"] not in selected_ids]
        
        # Calculate how many more we need
        current_count = sum(1 for p in selected_pairs if p["stage_pair"] == sp)
        needed = max(0, budget - current_count)
        
        if needed > 0 and candidates:
            # Stratify sampling: group by expected_risk_class to maintain diversity
            by_risk = {}
            for c in candidates:
                rk = c["expected_risk_class"]
                if rk not in by_risk:
                    by_risk[rk] = []
                by_risk[rk].append(c)
                
            # Sample evenly from each risk class if possible
            sampled = []
            risk_classes = list(by_risk.keys())
            while len(sampled) < needed:
                shuffled_classes = list(risk_classes)
                rng.shuffle(shuffled_classes)
                added_any = False
                for rk in shuffled_classes:
                    if len(sampled) >= needed:
                        break
                    if by_risk[rk]:
                        item = rng.choice(by_risk[rk])
                        by_risk[rk].remove(item)
                        sampled.append(item)
                        added_any = True
                if not added_any:
                    break
                    
            for item in sampled:
                # Assign default selection reason based on stage pair
                if "ARK" in sp:
                    item["selection_reason"] = "actual_core384_gap" if "ARK" in item["cand_b"] else "random_stratified_sample"
                else:
                    item["selection_reason"] = "random_stratified_sample"
                selected_pairs.append(item)
                selected_ids.add(item["pair_id"])
                
    # Save the selected 2bit cases
    headers = [
        "pair_id", "cand_a", "cand_b", "stage_pair", "same_stage", "same_byte",
        "same_row", "same_column", "same_bit_in_byte", "same_byte_farbit",
        "same_col_samebit", "same_col_diagbit", "distinct_row", "distinct_diag",
        "scatter", "potentially_redundant", "expected_risk_class", "selection_reason"
    ]
    
    with open(configs_dir / "selected_2bit_cases_round1.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(selected_pairs)

if __name__ == "__main__":
    main()
    print("Selected 2bit cases configured successfully.")
