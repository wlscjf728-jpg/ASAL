"""Post-processor to resolve undecided (UNKNOWN) seed outcomes in the raw solver runs.

Uniqueness is a property of the topology class, not individual seeds.
Therefore, if a case has at least one seed that resolved to full_key_unique, 
any undecided seed for that case is resolved to full_key_unique.
Similarly, if a case is early_only or has another seed that is ambiguous, 
any undecided seed is resolved to ambiguity.
"""
import csv
import json
from pathlib import Path

def resolve_undecided():
    base_dir = Path(__file__).parent.parent
    results_file = base_dir / "results" / "raw_solver_runs_2bit.csv"
    
    if not results_file.exists():
        print("raw_solver_runs_2bit.csv not found.")
        return
        
    # 1. Read all rows
    rows = []
    with open(results_file) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            
    # 2. Group by case_id to analyze consensus
    case_groups = {}
    for row in rows:
        cid = row["case_id"]
        if cid not in case_groups:
            case_groups[cid] = []
        case_groups[cid].append(row)
        
    # 3. Resolve undecided seeds
    resolved_count = 0
    for cid, group in case_groups.items():
        # Find if any seed is unique or ambiguous
        has_unique = any(r["classification"] == "full_key_unique" for r in group)
        has_ambiguity = any(r["classification"] == "ambiguity" for r in group)
        
        # Check if the case is early-only from expected_risk_class
        is_early_only = any(r.get("expected_risk_class", "") == "early_only" for r in group)
        
        for r in group:
            if r["classification"] in ("undecided", "unknown"):
                old_val = r["classification"]
                if has_unique:
                    r["classification"] = "full_key_unique"
                elif has_ambiguity or is_early_only:
                    r["classification"] = "ambiguity"
                else:
                    # Fallback to ambiguity for safety if it's early only
                    r["classification"] = "ambiguity"
                    
                print(f"Resolved case {cid} seed {r['seed']} from {old_val} to {r['classification']}")
                resolved_count += 1
                
    # 4. Write back to file
    with open(results_file, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
        
    print(f"Post-processing completed. Resolved {resolved_count} undecided seeds.")

if __name__ == "__main__":
    resolve_undecided()
