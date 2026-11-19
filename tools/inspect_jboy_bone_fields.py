#!/usr/bin/env python3
"""Dump raw offset-based candidates from JBOY bone records, without asserting semantics."""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path

RECORD_SIZE = 0x50
CANDIDATE_OFFSETS = (0x10, 0x20, 0x40)  # 0x30 is separately read as parent; 0x44 overlaps 0x40.

class FormatError(ValueError):
    pass

def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise FormatError(f"u32 outside file at 0x{offset:X}")
    return struct.unpack_from(">I", data, offset)[0]

def inspect(data: bytes) -> dict:
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise FormatError("Expected JBOY or YOBJ magic")
    count = u32(data, 0x20)
    bone_offset = u32(data, 0x28) + 8
    if count > 10000 or bone_offset < 8 or bone_offset + count * RECORD_SIZE > len(data):
        raise FormatError("Bone table range/count is invalid")
    bones = []
    for i in range(count):
        off = bone_offset + i * RECORD_SIZE
        name = data[off:off+0x10].split(b"\0", 1)[0].decode("ascii", "replace")
        parent_raw = u32(data, off + 0x30)
        fields = {}
        for field_off in CANDIDATE_OFFSETS:
            raw = data[off+field_off:off+field_off+16]
            vals = list(struct.unpack(">4f", raw))
            fields[f"offset_0x{field_off:02X}"] = {
                "raw_hex": raw.hex(),
                "float32_be_candidates": [v if math.isfinite(v) else None for v in vals],
                "all_finite": all(math.isfinite(v) for v in vals)
            }
        bones.append({
            "index": i, "name": name, "parent_u32_at_0x30": parent_raw,
            "record_offset": off, "record_hex": data[off:off+RECORD_SIZE].hex(),
            "candidate_fields": fields
        })
    return {
        "format": data[:4].decode("ascii"), "bone_count": count,
        "bone_table_offset": bone_offset, "record_size": RECORD_SIZE, "bones": bones,
        "warning": "Raw offsets only. 0x30 is parent-index candidate; 0x40 block overlaps 0x4C. No transform or bind-pose semantics asserted."
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = inspect(args.input.read_bytes())
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({"format": report["format"], "bone_count": report["bone_count"],
                      "bone_table_offset": report["bone_table_offset"],
                      "warning": report["warning"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
