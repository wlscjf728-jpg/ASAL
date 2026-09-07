"""Script to run a single case with strictly unlimited timeouts to answer the user's question."""
import sys
from pathlib import Path
import yaml

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))

from experiment_common import ROOT, load_candidate_map, read_csv, taps_for_case
from adaptive_query_attack import adaptive_run

def run_single():
    # 1. Load configuration and override timeouts to 0 (unlimited)
    config = {
        "campaign": {"seeds": 3},
        "attack": {
            "depth": 2,
            "mode": "differential",
            "initial_query_count": 32,
            "fixed_query_ladder": [32, 64, 96, 128, 192, 255]
        },
        "solver": {
            "first_timeout_ms": 0,          # UNLIMITED
            "second_timeout_ms": 0,         # UNLIMITED
            "diagnostic_timeout_ms": 0,     # UNLIMITED
            "sbox_encoding": "uf_axiom"
        },
        "adaptive_query": {
            "synthesis_mode": "fixed_pair",
            "max_adaptive_queries": 96,
            "separability_timeout_ms": 0,    # UNLIMITED
            "query_domain": "unrestricted",
            "max_active_bytes": 16
        }
    }
    
    # 2. Get cases and find the target case
    cases = read_csv(ROOT / "configs" / "selected_3bit_proven_ambiguous.csv")
    target_case_id = "p7_1_3b_3bit_gap_mixed__ARK_34__SB_106__SB_115"
    
    target_case = None
    for case in cases:
        if case["attack8_case_id"] == target_case_id:
            target_case = case
            break
            
    if not target_case:
        print(f"Case {target_case_id} not found in CSV.")
        return
        
    candidate_map = load_candidate_map()
    taps = taps_for_case(target_case, candidate_map)
    seed = 0
    
    print(f"Starting single sequential validation run for {target_case_id} seed {seed} with UNLIMITED timeouts...")
    payload = adaptive_run(target_case, seed, config, taps)
    
    print("\n--- RUN COMPLETED ---")
    print(f"Run ID: {payload['run_id']}")
    print(f"Terminal Classification: {payload['terminal_classification']}")
    print(f"Total Query Count: {payload['query_count']}")
    print(f"Oracle Encryptions: {payload['oracle_encryptions']}")
    print(f"Steps taken: {len(payload['steps'])}")
    for idx, step in enumerate(payload['steps']):
        print(f"Step {idx}: classification={step['classification']}, first={step['first_result']}, second={step['second_result']}, terminal={step.get('terminal', 'none')}")

if __name__ == "__main__":
    run_single()
