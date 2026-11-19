#!/usr/bin/env python3
"""Read-only basic PAC file probe. No decompression or file modification."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
from collections import Counter

def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a file's size, leading bytes, and byte entropy.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--sample-size", type=int, default=1024 * 1024,
                        help="Maximum bytes read for entropy (default: 1 MiB)")
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error(f"Not a file: {args.file}")
    if args.sample_size < 1:
        parser.error("--sample-size must be positive")
    size = args.file.stat().st_size
    with args.file.open("rb") as f:
        header = f.read(64)
        sample = header + f.read(max(0, args.sample_size - len(header)))
    print(f"File: {args.file}")
    print(f"Size: {size} bytes ({size / 1024 / 1024:.3f} MiB)")
    print(f"First 64 bytes: {header.hex(' ').upper()}")
    print(f"ASCII preview: {''.join(chr(b) if 32 <= b < 127 else '.' for b in header)}")
    print(f"Entropy sample: {entropy(sample):.4f} bits/byte (max 8.0)")
    print("Note: high entropy alone does not prove compression or encryption.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
