#!/usr/bin/env python3
"""Read-only parser for WWE 2K17 HSPC -> SHDC directory tables.

It lists child resource ranges and their leading signatures. It deliberately
does not decompress BPE or claim that a JBOY marker inside BPE is a model.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

class FormatError(ValueError):
    pass

def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise FormatError(f"u32 outside file at 0x{offset:X}")
    return struct.unpack_from("<I", data, offset)[0]

def u64(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 8 > len(data):
        raise FormatError(f"u64 outside file at 0x{offset:X}")
    return struct.unpack_from("<Q", data, offset)[0]

def checked_range(data: bytes, offset: int, length: int, label: str) -> None:
    if offset < 0 or length < 0 or offset + length > len(data):
        raise FormatError(f"{label} range 0x{offset:X}+0x{length:X} exceeds file size 0x{len(data):X}")

def parse_hspc(data: bytes) -> list[dict]:
    if data[:4] != b"HSPC":
        raise FormatError("Input does not begin with HSPC")
    count = u32(data, 0x38)
    name_length = u32(data, 0x18)
    if count > 100000:
        raise FormatError(f"Unreasonable HSPC entry count: {count}")
    # HSPC file names begin at 0x800; the offset/length table follows the
    # padded name area, as implemented by WrestleMINUS' HSPC reader.
    table_offset = name_length - (name_length % 0x800) + 0x1000
    checked_range(data, 0x800, count * 0x14, "HSPC names")
    checked_range(data, table_offset, count * 0x0C, "HSPC entry table")
    entries = []
    for i in range(count):
        name = data[0x800 + i * 0x14:0x800 + i * 0x14 + 8].hex().upper()
        sector = u32(data, table_offset + i * 0x0C)
        size_units = u32(data, table_offset + i * 0x0C + 4)
        offset, length = sector * 0x800, size_units * 0x100
        checked_range(data, offset, length, f"HSPC entry {i}")
        entries.append({
            "container": "HSPC", "index": i, "name": name,
            "offset": offset, "length": length,
            "magic": data[offset:offset+4].decode("ascii", "replace")
        })
    return entries

def parse_shdc(data: bytes, base: int, length: int) -> list[dict]:
    checked_range(data, base, length, "SHDC container")
    if data[base:base+4] != b"SHDC":
        raise FormatError(f"Expected SHDC at 0x{base:X}")
    mode = u32(data, base + 0x0C)
    info_length = u32(data, base + 0x20)
    if info_length % 0x10:
        raise FormatError(f"SHDC info length is not divisible by 0x10 at 0x{base:X}")
    if mode == 1:
        info_offset = u32(data, base + 0x1C)
    elif mode == 0x10:
        temp = u32(data, base + 0x18)
        temp = (temp + 0x0F) & ~0x0F
        info_offset = temp + 0x50
    elif mode == 0x800:
        info_offset = u32(data, base + 0x1C) * 0x800
    else:
        raise FormatError(f"Unsupported SHDC header mode 0x{mode:X} at 0x{base:X}")
    checked_range(data, base + info_offset, info_length, "SHDC entry table")
    count = info_length // 0x10
    if count > 100000:
        raise FormatError(f"Unreasonable SHDC entry count: {count}")
    entries = []
    for i in range(count):
        row = base + info_offset + i * 0x10
        name_value = u32(data, row)
        relative_offset = u32(data, row + 4)
        child_length = u64(data, row + 8)
        offset = base + relative_offset
        checked_range(data, offset, child_length, f"SHDC entry {i}")
        entries.append({
            "container": "SHDC", "index": i, "name": f"{name_value:X}",
            "offset": offset, "length": child_length,
            "magic": data[offset:offset+4].decode("ascii", "replace")
        })
    return entries

def analyze(data: bytes) -> dict:
    top = parse_hspc(data)
    nested = []
    for item in top:
        if item["magic"] == "SHDC":
            nested.extend(parse_shdc(data, item["offset"], item["length"]))
    return {
        "file_size": len(data),
        "hspc_entries": top,
        "shdc_entries": nested,
        "notes": [
            "Offsets and lengths are parsed from container tables.",
            "BPE entries remain compressed; signatures found inside BPE bytes are not validated models.",
            "No source bytes are modified and no FBX/GLB is exported."
        ]
    }

def main() -> int:
    ap = argparse.ArgumentParser(description="List WWE 2K17 HSPC/SHDC resource entries.")
    ap.add_argument("file", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = analyze(args.file.read_bytes())
    report = json.dumps(result, indent=2)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
