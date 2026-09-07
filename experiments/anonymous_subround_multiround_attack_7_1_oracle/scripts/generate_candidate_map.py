import csv
from pathlib import Path

def generate_maps():
    stages_core = ["SB", "SR", "MC"]
    stages_ext = ["SB", "SR", "MC", "ARK"]
    
    def get_candidate_rows(stages):
        rows = []
        for stage in stages:
            for bit_idx in range(128):
                byte_idx = bit_idx // 8
                bit_in_byte = bit_idx % 8
                row = byte_idx % 4
                col = byte_idx // 4
                cls = "early" if stage in ("SB", "SR") else "late"
                notes = f"{stage} output byte {byte_idx} row {row} col {col} bit {bit_in_byte}"
                
                rows.append({
                    "candidate_id": f"{stage}_{bit_idx}",
                    "stage": stage,
                    "bit_index": bit_idx,
                    "byte_index": byte_idx,
                    "row": row,
                    "column": col,
                    "bit_in_byte": bit_in_byte,
                    "class": cls,
                    "notes": notes
                })
        return rows

    core_rows = get_candidate_rows(stages_core)
    ext_rows = get_candidate_rows(stages_ext)
    
    # Save CSVs
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    headers = ["candidate_id", "stage", "bit_index", "byte_index", "row", "column", "bit_in_byte", "class", "notes"]
    
    with open(results_dir / "candidate_map_core384.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(core_rows)
        
    with open(results_dir / "candidate_map_extended512.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(ext_rows)

if __name__ == "__main__":
    generate_maps()
    print("Candidate maps generated successfully.")
