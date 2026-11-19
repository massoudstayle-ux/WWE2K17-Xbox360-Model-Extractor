#!/usr/bin/env python3
"""Inspect JBOY skin-weight buffers without guessing their binary semantics.

The JBOY mesh descriptor stores a weight-block count and a weight-buffer
pointer. Across the ch120/ch139 samples, the byte span from the resolved
weight pointer to the resolved UV pointer equals:
    vertex_count * weight_block_count * 8
This tool validates that layout and prints raw 8-byte slots for research.
It does NOT claim that the slot fields have been fully decoded and does not
write or modify the source model.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path


class FormatError(ValueError):
    pass


def be_u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise FormatError(f"u32 outside file at 0x{off:X}")
    return struct.unpack_from(">I", data, off)[0]


def check_range(data: bytes, off: int, size: int, label: str) -> None:
    if off < 0 or size < 0 or off + size > len(data):
        raise FormatError(
            f"{label} range 0x{off:X}+0x{size:X} outside file 0x{len(data):X}"
        )


def inspect(data: bytes, samples: int = 3) -> dict:
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise FormatError("Expected JBOY or YOBJ magic")

    mesh_count = be_u32(data, 0x18)
    mesh_table = be_u32(data, 0x1C) + 8
    if mesh_count > 10000:
        raise FormatError(f"Unreasonable mesh count: {mesh_count}")
    check_range(data, mesh_table, mesh_count * 0xB8, "mesh descriptors")

    meshes = []
    exact = 0
    for index in range(mesh_count):
        desc = mesh_table + index * 0xB8
        vertex_count = be_u32(data, desc)
        weight_blocks = be_u32(data, desc + 0x5C)
        weight_ptr = be_u32(data, desc + 0x6C) + 8
        uv_ptr = be_u32(data, desc + 0x70) + 8

        if vertex_count > 2_000_000 or weight_blocks > 32:
            raise FormatError(f"Unreasonable counts in mesh {index}")
        check_range(data, weight_ptr, max(0, uv_ptr - weight_ptr), f"mesh {index} weight span")

        actual_bytes = uv_ptr - weight_ptr
        expected_bytes = vertex_count * weight_blocks * 8
        is_exact = actual_bytes == expected_bytes
        exact += int(is_exact)

        samples_out = []
        slot_count = min(weight_blocks, 8)
        for vertex in range(min(samples, vertex_count)):
            slots = []
            for slot in range(slot_count):
                off = weight_ptr + (vertex * weight_blocks + slot) * 8
                raw = data[off:off + 8]
                # These interpretations are deliberately labeled candidates.
                first_be = struct.unpack(">f", raw[:4])[0]
                second_be = struct.unpack(">f", raw[4:])[0]
                first_le_u32 = struct.unpack("<I", raw[:4])[0]
                second_le_u32 = struct.unpack("<I", raw[4:])[0]
                slots.append({
                    "hex": raw.hex(),
                    "u32_le_first_candidate": first_le_u32,
                    "u32_le_second_candidate": second_le_u32,
                    "f32_be_first_candidate": first_be if math.isfinite(first_be) else None,
                    "f32_be_second_candidate": second_be if math.isfinite(second_be) else None,
                })
            samples_out.append({"vertex": vertex, "slots": slots})

        meshes.append({
            "mesh": index,
            "vertex_count": vertex_count,
            "weight_block_count": weight_blocks,
            "weight_buffer_offset": weight_ptr,
            "uv_buffer_offset": uv_ptr,
            "actual_weight_span_bytes": actual_bytes,
            "expected_vertex_times_blocks_times_8": expected_bytes,
            "span_matches_expected": is_exact,
            "sample_vertices": samples_out,
        })

    return {
        "format": data[:4].decode("ascii"),
        "file_size": len(data),
        "mesh_count": mesh_count,
        "meshes_with_exact_weight_span": exact,
        "all_weight_spans_match": exact == mesh_count,
        "interpretation_warning": (
            "8-byte slot boundaries are validated by buffer lengths only. "
            "The meaning, byte order, and field order of each slot are not "
            "declared as decoded bone indices or normalized weights."
        ),
        "meshes": meshes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--samples", type=int, default=3,
                    help="Number of initial vertices to show per mesh (default: 3)")
    ap.add_argument("--output", type=Path,
                    help="Optional JSON report path")
    args = ap.parse_args()
    if args.samples < 0 or args.samples > 100:
        ap.error("--samples must be between 0 and 100")
    report = inspect(args.input.read_bytes(), args.samples)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "mesh_count": report["mesh_count"],
        "meshes_with_exact_weight_span": report["meshes_with_exact_weight_span"],
        "all_weight_spans_match": report["all_weight_spans_match"],
        "interpretation_warning": report["interpretation_warning"],
    }, indent=2))
    if not report["all_weight_spans_match"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
