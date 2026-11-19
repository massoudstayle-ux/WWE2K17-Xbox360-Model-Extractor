#!/usr/bin/env python3
"""Decode and validate candidate JBOY skin-weight slots against each mesh palette.

Observed Xbox 360 JBOY layout: each mesh has up to 20 node indices plus one in
its descriptor (+0x0C..+0x58), with the count at +0x08. Per-vertex weight slots store a little-endian
palette-local index followed by a big-endian float32 weight. 0xFF is the
unused-slot sentinel. This remains a researched format interpretation until
the resulting rig is validated in a renderer.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path

RECORD_SIZE = 0xB8
PALETTE_COUNT_OFFSET = 0x08
PALETTE_OFFSET = 0x0C
PALETTE_SLOTS = 20

class FormatError(ValueError):
    pass

def be_u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise FormatError(f"u32 outside file at 0x{off:X}")
    return struct.unpack_from(">I", data, off)[0]

def check_range(data: bytes, off: int, size: int, label: str) -> None:
    if off < 0 or size < 0 or off + size > len(data):
        raise FormatError(f"{label} range 0x{off:X}+0x{size:X} outside file 0x{len(data):X}")

def read_palette(data: bytes, desc: int, bone_count: int, mesh_index: int) -> list[int]:
    count = be_u32(data, desc + PALETTE_COUNT_OFFSET)
    if count > PALETTE_SLOTS:
        raise FormatError(f"mesh {mesh_index} palette count {count} exceeds {PALETTE_SLOTS}")
    palette = []
    for slot in range(count):
        value = be_u32(data, desc + PALETTE_OFFSET + slot * 4)
        # The stored node index is offset by +1; zero is not a valid node.
        if value == 0 or value > bone_count:
            raise FormatError(
                f"mesh {mesh_index} palette slot {slot} stores node+1 value {value}, "
                f"but model has {bone_count} nodes"
            )
        palette.append(value - 1)
    return palette

def inspect(data: bytes, samples: int = 3, sum_tolerance: float = 0.02) -> dict:
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise FormatError("Expected JBOY or YOBJ magic")
    mesh_count = be_u32(data, 0x18)
    mesh_table = be_u32(data, 0x1C) + 8
    bone_count = be_u32(data, 0x20)
    if mesh_count > 10000 or bone_count > 10000:
        raise FormatError("Unreasonable model counts")
    check_range(data, mesh_table, mesh_count * RECORD_SIZE, "mesh descriptors")

    meshes = []
    exact = total_vertices = valid_slots = sentinels = 0
    bad_palette_indices = bad_weights = bad_sums = 0
    global_bones_used: set[int] = set()

    for mesh_index in range(mesh_count):
        desc = mesh_table + mesh_index * RECORD_SIZE
        vertex_count = be_u32(data, desc)
        weight_blocks = be_u32(data, desc + 0x5C)
        weight_ptr = be_u32(data, desc + 0x6C) + 8
        uv_ptr = be_u32(data, desc + 0x70) + 8
        if vertex_count > 2_000_000 or weight_blocks > 32:
            raise FormatError(f"Unreasonable counts in mesh {mesh_index}")
        palette = read_palette(data, desc, bone_count, mesh_index)
        check_range(data, weight_ptr, max(0, uv_ptr - weight_ptr), f"mesh {mesh_index} weight span")
        actual_bytes = uv_ptr - weight_ptr
        expected_bytes = vertex_count * weight_blocks * 8
        span_ok = actual_bytes == expected_bytes
        exact += int(span_ok)
        if not span_ok:
            meshes.append({
                "mesh": mesh_index, "vertex_count": vertex_count,
                "weight_block_count": weight_blocks, "palette_global_bone_indices": palette,
                "actual_weight_span_bytes": actual_bytes,
                "expected_vertex_times_blocks_times_8": expected_bytes,
                "span_matches_expected": False, "decode_skipped": "buffer span mismatch"
            })
            continue

        vertex_sums = []
        influence_histogram = {}
        mesh_valid = mesh_sentinels = mesh_bad_palette = mesh_bad_weights = mesh_bad_sums = 0
        mesh_bones_used: set[int] = set()
        sample_vertices = []

        for vertex in range(vertex_count):
            slots_out = []
            total = 0.0
            active = 0
            for slot in range(weight_blocks):
                off = weight_ptr + (vertex * weight_blocks + slot) * 8
                bone_bytes = data[off:off + 4]
                local_index = bone_bytes[0]
                padding_is_zero = bone_bytes[1:] == bytes(3)
                weight = struct.unpack_from(">f", data, off + 4)[0]
                sentinel = local_index == 0xFF
                global_index = None
                if sentinel:
                    mesh_sentinels += 1
                elif not padding_is_zero:
                    mesh_bad_weights += 1
                elif local_index >= len(palette):
                    mesh_bad_palette += 1
                elif not math.isfinite(weight) or not 0.0 <= weight <= 1.0:
                    mesh_bad_weights += 1
                else:
                    global_index = palette[local_index]
                    mesh_valid += 1
                    active += 1
                    total += weight
                    mesh_bones_used.add(global_index)
                if vertex < samples:
                    slots_out.append({
                        "slot": slot, "palette_local_index": local_index,
                        "global_bone_index": global_index,
                        "weight": weight if math.isfinite(weight) else None,
                        "sentinel": sentinel, "bone_index_padding_zero": padding_is_zero,
                        "raw_hex": data[off:off+8].hex()
                    })
            if active:
                vertex_sums.append(total)
                influence_histogram[active] = influence_histogram.get(active, 0) + 1
                if abs(total - 1.0) > sum_tolerance:
                    mesh_bad_sums += 1
            if vertex < samples:
                sample_vertices.append({
                    "vertex": vertex, "slots": slots_out,
                    "active_influence_count": active, "weight_sum": total
                })

        valid_slots += mesh_valid
        sentinels += mesh_sentinels
        bad_palette_indices += mesh_bad_palette
        bad_weights += mesh_bad_weights
        bad_sums += mesh_bad_sums
        total_vertices += vertex_count
        global_bones_used.update(mesh_bones_used)
        meshes.append({
            "mesh": mesh_index, "vertex_count": vertex_count,
            "weight_block_count": weight_blocks,
            "palette_size": len(palette), "palette_global_bone_indices": palette,
            "actual_weight_span_bytes": actual_bytes,
            "expected_vertex_times_blocks_times_8": expected_bytes,
            "span_matches_expected": span_ok,
            "valid_influence_slots": mesh_valid, "sentinel_slots": mesh_sentinels,
            "invalid_palette_local_indices": mesh_bad_palette,
            "invalid_weight_slots": mesh_bad_weights,
            "vertices_with_weight_sum_outside_tolerance": mesh_bad_sums,
            "influence_count_histogram": influence_histogram,
            "weight_sum_min": min(vertex_sums) if vertex_sums else None,
            "weight_sum_max": max(vertex_sums) if vertex_sums else None,
            "global_bone_indices_used": sorted(mesh_bones_used),
            "sample_vertices": sample_vertices
        })

    ok = (
        exact == mesh_count and bad_palette_indices == 0 and bad_weights == 0
        and bad_sums == 0
    )
    return {
        "format": data[:4].decode("ascii"), "file_size": len(data),
        "mesh_count": mesh_count, "bone_count": bone_count,
        "meshes_with_exact_weight_span": exact, "all_weight_spans_match": exact == mesh_count,
        "total_vertices_checked": total_vertices, "valid_influence_slots": valid_slots,
        "sentinel_slots": sentinels,
        "invalid_palette_local_indices": bad_palette_indices,
        "invalid_weight_slots": bad_weights,
        "vertices_with_weight_sum_outside_tolerance": bad_sums,
        "global_bone_indices_used": sorted(global_bones_used),
        "candidate_encoding": {
            "mesh_palette": "count at descriptor +0x08, followed by that many big-endian uint32 node indices plus one from +0x0C (maximum 20)",
            "slot_index": "first byte is palette-local index; remaining three bytes are zero padding",
            "weight": "big-endian float32",
            "sentinel_index": 255,
            "storage_order": "vertex-major, then weight-block index (confirmed by normalized per-vertex sums on ch120/ch139)",
            "validation": "local indices resolve through each mesh palette; padding is zero; active weights sum to 1 within tolerance"
        },
        "all_checks_passed": ok,
        "interpretation_warning": (
            "Palette-local indices and weights pass structural/range/sum checks. "
            "This does not yet validate bone bind transforms, inverse-bind matrices, "
            "vertex-to-palette correspondence in a rendered pose, or final Godot deformation."
        ),
        "meshes": meshes
    }

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--sum-tolerance", type=float, default=0.02)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.samples < 0 or args.samples > 100:
        ap.error("--samples must be 0..100")
    if args.sum_tolerance < 0:
        ap.error("--sum-tolerance must be non-negative")
    report = inspect(args.input.read_bytes(), args.samples, args.sum_tolerance)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    compact = {k: report[k] for k in (
        "format", "mesh_count", "bone_count", "all_weight_spans_match",
        "valid_influence_slots", "sentinel_slots", "invalid_palette_local_indices",
        "invalid_weight_slots", "vertices_with_weight_sum_outside_tolerance",
        "all_checks_passed", "interpretation_warning"
    )}
    print(json.dumps(compact, indent=2))
    return 0 if report["all_checks_passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
