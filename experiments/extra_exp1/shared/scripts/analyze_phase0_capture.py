"""Analyze evaluator-annotated gate-level Phase 0 captures.

The attack-side output intentionally omits the evaluator target column. This
script is an evaluator analysis artifact: it compares differential scan slots
with the public AES semantic MC9 transcript and with the evaluator-only
MC_REG[9] Q transcript.
"""
from __future__ import annotations
import argparse, json, sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "extra_exp" / "scripts"))
import semantic_reference as sr
sr.sbox = lru_cache(maxsize=256)(sr.sbox)

COLUMNS = {
    "C0": {0, 5, 10, 15},
    "C1": {4, 9, 14, 3},
    "C2": {8, 13, 2, 7},
    "C3": {12, 1, 6, 11},
}

def parse_capture(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        q, schedule, target, vector = line.split()
        rows.append((int(q), int(schedule), int(target), int(vector, 16)))
    return rows

def parse_queries(path: Path):
    return {int(q): bytes.fromhex(p) for q, p in (line.split() for line in path.read_text().splitlines())}

def signature(values, qids):
    out = 0
    for q in qids:
        out |= (values[q] & 1) << q
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--queries", required=True, type=Path)
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    key = bytes.fromhex(args.key)
    rows = parse_capture(args.capture)
    queries = parse_queries(args.queries)
    qids = sorted(queries)
    # Compute each AES trace once, then reuse round states for both semantic rounds.
    traces = {q: sr.aes128_round_states(queries[q], key)[0] for q in qids}
    result = {"capture": str(args.capture), "query_count": len(qids), "schedules": {}}
    for schedule in (1, 2, 3):
        byq = {q: (target, vector) for q, s, target, vector in rows if s == schedule}
        if set(byq) != set(qids):
            raise SystemExit(f"schedule {schedule}: incomplete rows")
        target_sig = sum((byq[q][0] ^ byq[qids[0]][0]) << q for q in qids)
        slot_sigs = []
        for slot in range(256):
            slot_sigs.append(sum((((byq[q][1] >> slot) & 1) ^ ((byq[qids[0]][1] >> slot) & 1)) << q for q in qids))
        semantic_matches = {}
        for round_number in (1, 2):
            semsig = sum(((traces[q][round_number - 1][9 // 8] >> (9 % 8)) & 1 ^ ((traces[qids[0]][round_number - 1][9 // 8] >> (9 % 8)) & 1)) << q for q in qids)
            semantic_matches[str(round_number)] = [slot for slot, sig in enumerate(slot_sigs) if sig == semsig]
        target_matches = [slot for slot, sig in enumerate(slot_sigs) if sig == target_sig]
        result["schedules"][str(schedule)] = {
            "target_ones": sum(byq[q][0] for q in qids),
            "target_diff_ones": target_sig.bit_count(),
            "semantic_mc9_diff_ones": {
                str(r): sum((((traces[q][r - 1][1] >> 1) & 1) ^ ((traces[qids[0]][r - 1][1] >> 1) & 1)) for q in qids)
                for r in (1, 2)
            },
            "semantic_mc9_matches": semantic_matches,
            "evaluator_target_matches": target_matches,
        }
    # Reproducibility is evaluated by this script on repeated capture files.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
