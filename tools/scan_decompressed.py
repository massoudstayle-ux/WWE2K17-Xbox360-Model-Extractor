#!/usr/bin/env python3
"""Read-only signature scanner for XMem-decompressed WWE 2K17 data.

This reports candidate offsets only. It does not parse containers, decode BPE,
extract models, or modify its input.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MAGIC = {
    b"HSPC": "HSPC container",
    b"SHDC": "SHDC container",
    b"BPE ": "BPE compressed resource",
    b"JBOY": "JBOY model",
    b"YOBJ": "YOBJ model",
    b"DDS ": "DDS texture",
    b"YANM": "YANM animation",
    b"DUMY": "DUMY resource",
}

def scan(data: bytes) -> list[tuple[int, str]]:
    hits = []
    for signature, label in MAGIC.items():
        start = 0
        while True:
            offset = data.find(signature, start)
            if offset < 0:
                break
            hits.append((offset, label))
            start = offset + 1
    return sorted(hits)

def main() -> int:
    parser = argparse.ArgumentParser(description="Find candidate WWE 2K17 resource signatures.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path, help="Optional text report path.")
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error(f"Not a file: {args.file}")
    data = args.file.read_bytes()
    hits = scan(data)
    lines = [
        "WWE 2K17 decompressed-resource signature scan (read-only)",
        f"File: {args.file}",
        f"Size: {len(data)} bytes",
        "NOTE: signature hits are candidates, not proof of valid resources.",
        f"Total hits: {len(hits)}",
    ]
    lines.extend(f"0x{offset:08X}  {label}" for offset, label in hits)
    if not hits:
        lines.append("No known signatures found.")
    report = "\n".join(lines) + "\n"
    print(report, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
