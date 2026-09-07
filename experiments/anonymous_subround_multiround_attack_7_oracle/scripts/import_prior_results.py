import csv
import glob
from pathlib import Path

TOPOLOGY_MAP = {
    # Phase 1: MC Topologies
    "mc_same_byte_2": [("MC", 0, 0), ("MC", 0, 1)],
    "mc_same_col_samebit_2": [("MC", 0, 0), ("MC", 1, 0)],
    "mc_same_col_diagbit_2": [("MC", 0, 0), ("MC", 1, 1)],
    "mc_distinct_row0_2": [("MC", 0, 0), ("MC", 4, 0)],
    "mc_distinct_diag_2": [("MC", 0, 0), ("MC", 5, 1)],
    "mc_same_byte_farbit_2": [("MC", 0, 0), ("MC", 0, 7)],
    "mc_same_col_farbyte_2": [("MC", 0, 0), ("MC", 3, 0)],
    
    # Phase 2: ARK Topologies
    "ark_same_byte_2": [("ARK", 0, 0), ("ARK", 0, 1)],
    "ark_same_col_samebit_2": [("ARK", 0, 0), ("ARK", 1, 0)],
    "ark_same_col_diagbit_2": [("ARK", 0, 0), ("ARK", 1, 1)],
    "ark_distinct_row0_2": [("ARK", 0, 0), ("ARK", 4, 0)],
    "ark_distinct_diag_2": [("ARK", 0, 0), ("ARK", 5, 1)],
    
    # Phase 3: Early stage SB/SR
    "sb_same_byte_2": [("SB", 0, 0), ("SB", 0, 1)],
    "sb_same_col_samebit_2": [("SB", 0, 0), ("SB", 1, 0)],
    "sb_distinct_row0_2": [("SB", 0, 0), ("SB", 4, 0)],
    "sb_distinct_diag_2": [("SB", 0, 0), ("SB", 5, 1)],
    "sr_same_byte_2": [("SR", 0, 0), ("SR", 0, 1)],
    "sr_same_col_samebit_2": [("SR", 0, 0), ("SR", 1, 0)],
    "sr_distinct_row0_2": [("SR", 0, 0), ("SR", 4, 0)],
    "sr_distinct_diag_2": [("SR", 0, 0), ("SR", 5, 1)],
    
    # Phase 4: Mixed late MC+ARK
    "mc0_ark1_same_byte_like": [("MC", 0, 0), ("ARK", 0, 1)],
    "mc0_ark0_same_bit": [("MC", 0, 0), ("ARK", 0, 0)],
    "mc0_ark8_same_column": [("MC", 0, 0), ("ARK", 1, 0)],
    "mc0_ark9_same_col_diag": [("MC", 0, 0), ("ARK", 1, 1)],
    "mc0_ark32_distinct_row": [("MC", 0, 0), ("ARK", 4, 0)],
    "mc0_ark41_distinct_diag": [("MC", 0, 0), ("ARK", 5, 1)],
    
    # Phase 5: Cross-stage early+late scatter
    "sb0_mc0": [("SB", 0, 0), ("MC", 0, 0)],
    "sb0_mc1": [("SB", 0, 0), ("MC", 0, 1)],
    "sb0_mc32": [("SB", 0, 0), ("MC", 4, 0)],
    "sb0_mc41": [("SB", 0, 0), ("MC", 5, 1)],
    "sr0_mc0": [("SR", 0, 0), ("MC", 0, 0)],
    "sr0_mc1": [("SR", 0, 0), ("MC", 0, 1)],
    "sr0_mc32": [("SR", 0, 0), ("MC", 4, 0)],
    "sr0_mc41": [("SR", 0, 0), ("MC", 5, 1)],
    "sb0_ark0": [("SB", 0, 0), ("ARK", 0, 0)],
    "sb0_ark1": [("SB", 0, 0), ("ARK", 0, 1)],
    "sr0_ark0": [("SR", 0, 0), ("ARK", 0, 0)],
    "sr0_ark1": [("SR", 0, 0), ("ARK", 0, 1)],
    
    # Phase 6: Early-only cross-stage SB+SR
    "sb0_sr0": [("SB", 0, 0), ("SR", 0, 0)],
    "sb0_sr1": [("SB", 0, 0), ("SR", 0, 1)],
    "sb0_sr8": [("SB", 0, 0), ("SR", 1, 0)],
    "sb0_sr32": [("SB", 0, 0), ("SR", 4, 0)],
    "sb0_sr41": [("SB", 0, 0), ("SR", 5, 1)],
}

import random
def get_general_taps(placement, seed):
    if placement == "mc_random_pair_seeded":
        rng = random.Random((seed + 1) * 9999 + 42)
        universe = [("MC", byte, bit) for byte in range(16) for bit in range(8)]
        specs = rng.sample(universe, 2)
    elif placement in TOPOLOGY_MAP:
        specs = TOPOLOGY_MAP[placement]
    else:
        return None
    return [{"stage": s, "bit_index": byte * 8 + bit} for s, byte, bit in specs]

def import_results():
    base_dir = Path(__file__).parent.parent
    attack_6_results_dir = base_dir.parent / "anonymous_subround_multiround_attack_6_oracle" / "results"
    
    # Find all CSV files in Attack 6 results
    csv_paths = glob.glob(str(attack_6_results_dir / "*.csv"))
    
    # Aggregate data by (placement, depth, query_count, mode)
    aggregated = {}
    
    for path in csv_paths:
        if "phase_influence_topology_2bit" in path or "phase1c_tap_count_reduction" in path:
            continue
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                placement = row["placement"]
                depth = int(row["depth"])
                query_count = int(row["query_count"])
                mode = row["mode"]
                classification = row["classification"]
                seed = int(row["seed"])
                
                key = (placement, depth, query_count, mode)
                if key not in aggregated:
                    aggregated[key] = []
                aggregated[key].append((seed, classification))
                
    imported_rows = []
    
    for (placement, depth, query_count, mode), runs in sorted(aggregated.items()):
        # Exclude runs that aren't 2 taps
        if placement == "one_early" or placement == "one_late":
            continue
            
        taps = get_general_taps(placement, 0) # Use seed=0 as reference, unless randomized
        if taps is None:
            # Skip if we cannot map
            continue
            
        stage_a = taps[0]["stage"]
        bit_a = taps[0]["bit_index"]
        stage_b = taps[1]["stage"]
        bit_b = taps[1]["bit_index"]
        
        seeds_total = len(runs)
        unique_count = sum(1 for seed, cls in runs if cls == "full_key_unique")
        ambiguity_count = sum(1 for seed, cls in runs if cls == "ambiguity")
        unknown_count = sum(1 for seed, cls in runs if cls in ("undecided", "unknown"))
        
        # Confirm status
        if unique_count == seeds_total:
            status = "all_unique"
        elif unique_count >= seeds_total * 0.8:
            status = "mostly_unique"
        elif ambiguity_count == seeds_total:
            status = "all_ambiguity"
        elif unique_count > 0:
            status = "mixed"
        else:
            status = "unresolved"
            
        case_name = f"{placement}-d{depth}-q{query_count}-{mode}"
        
        imported_rows.append({
            "source_experiment": "attack_6_oracle",
            "case_name": case_name,
            "stage_a": stage_a,
            "bit_a": bit_a,
            "stage_b": stage_b,
            "bit_b": bit_b,
            "depth": depth,
            "query_count": query_count,
            "mode": mode,
            "seeds_total": seeds_total,
            "unique_count": unique_count,
            "ambiguity_count": ambiguity_count,
            "unknown_count": unknown_count,
            "confirmed_status": status,
            "notes": f"imported placement {placement}"
        })
        
    headers = [
        "source_experiment", "case_name", "stage_a", "bit_a", "stage_b", "bit_b",
        "depth", "query_count", "mode", "seeds_total", "unique_count",
        "ambiguity_count", "unknown_count", "confirmed_status", "notes"
    ]
    
    with open(base_dir / "results" / "prior_2bit_results_imported.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(imported_rows)

if __name__ == "__main__":
    import_results()
    print("Prior 2bit results imported successfully.")
