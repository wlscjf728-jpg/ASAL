#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--plaintext',required=True); ap.add_argument('--reference'); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    value=bytes.fromhex(a.plaintext)
    reference=bytes.fromhex(a.reference) if a.reference else None
    if reference is not None and len(reference)!=16: raise ValueError('reference plaintext must be 16 bytes')
    if len(value)!=16: raise ValueError('plaintext must be 16 bytes')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if reference is None:
        a.output.write_text(f'0 {value.hex()}\n')
    else:
        a.output.write_text(f'0 {reference.hex()}\n1 {value.hex()}\n')
    print(a.output)
if __name__=='__main__':main()
