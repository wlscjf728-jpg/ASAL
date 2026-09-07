#!/usr/bin/env python3
"""Convert frozen JSON query manifests to VCS-friendly plaintext lists."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    data = json.loads(args.input.read_text())
    rows = data['queries']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w') as f:
        for row in rows:
            f.write(f"{row['query_id']} {row['plaintext_hex']}\n")
    print(json.dumps({'query_count': len(rows), 'output': str(args.output)}))

if __name__ == '__main__':
    main()
