#!/usr/bin/env python3
"""Decode and validate candidate JBOY skin-weight slots.

Across the ch120/ch139 samples, each 8-byte slot appears to contain a
little-endian uint32 bone index followed by a big-endian float32 weight.
Index 0xFF is a sentinel. This interpretation is validated against ranges and
per-vertex weight sums, but remains a format hypothesis until independently
confirmed by a known-good rig/render.
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
        raise FormatError(f"{label} range 0x{off:X}+0x{size:X} outside file 0x{len(data):X}")

def inspect(data: bytes, samples: int = 3, sum_tolerance: float = 0.02) -> dict:
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise FormatError("Expected JBOY or YOBJ magic")
    mesh_count = be_u32(data, 0x18)
    mesh_table = be_u32(data, 0x1C) + 8
    bone_count = be_u32(data, 0x20)
    if mesh_count > 10000 or bone_count > 10000:
        raise FormatError("Unreasonable model counts")
    check_range(data, mesh_table, mesh_count * 0xB8, "mesh descriptors")

    meshes = []
    exact = 0
    all_vertices = 0
    all_valid = 0
    all_sentinel = 0
    all_bad_indices = 0
    all_bad_weights = 0
    all_bad_sums = 0
    for index in range(mesh_count):
        desc = mesh_table + index * 0xB8
        vertex_count = be_u32(data, desc)
        weight_blocks = be_u32(data, desc + 0x5C)
        weight_ptr = be_u32(data, desc + 0x6C) + 8
        uv_ptr = be_u32(data, desc + 0x70) + 8
        if vertex_count > 2_000_000 or weight_blocks > 32:
            raise FormatError(f"Unreasonable counts in mesh {index}")
        check_range(data, weight_ptr, max(0, uv_ptr-weight_ptr), f"mesh {index} weight span")
        actual_bytes = uv_ptr-weight_ptr
        expected_bytes = vertex_count*weight_blocks*8
        span_ok = actual_bytes == expected_bytes
        exact += int(span_ok)
        if not span_ok:
            meshes.append({"mesh":index,"vertex_count":vertex_count,"weight_block_count":weight_blocks,
                "weight_buffer_offset":weight_ptr,"uv_buffer_offset":uv_ptr,
                "actual_weight_span_bytes":actual_bytes,"expected_vertex_times_blocks_times_8":expected_bytes,
                "span_matches_expected":False,"decode_skipped":"buffer span mismatch"})
            continue

        vertex_sums=[]
        influences_hist={}
        valid_indices=sentinels=bad_indices=bad_weights=bad_sums=0
        samples_out=[]
        for vertex in range(vertex_count):
            slots=[]
            total=0.0
            active=0
            for slot in range(weight_blocks):
                off=weight_ptr+(vertex*weight_blocks+slot)*8
                bone_index=struct.unpack_from("<I",data,off)[0]
                weight=struct.unpack_from(">f",data,off+4)[0]
                is_sentinel=(bone_index==0xFF)
                if is_sentinel:
                    sentinels+=1
                elif bone_index < bone_count and math.isfinite(weight) and 0.0 <= weight <= 1.0:
                    valid_indices+=1
                    active+=1
                    total+=weight
                else:
                    if bone_index >= bone_count: bad_indices+=1
                    if not math.isfinite(weight) or weight < 0.0 or weight > 1.0: bad_weights+=1
                if vertex < samples:
                    slots.append({"slot":slot,"bone_index_candidate":bone_index,
                        "weight_candidate":weight if math.isfinite(weight) else None,
                        "sentinel":is_sentinel,"raw_hex":data[off:off+8].hex()})
            if active:
                vertex_sums.append(total)
                influences_hist[active]=influences_hist.get(active,0)+1
                if abs(total-1.0)>sum_tolerance: bad_sums+=1
            if vertex < samples: samples_out.append({"vertex":vertex,"slots":slots,"active_influence_count":active,"weight_sum_candidate":total})
        all_vertices+=vertex_count
        all_valid+=valid_indices
        all_sentinel+=sentinels
        all_bad_indices+=bad_indices
        all_bad_weights+=bad_weights
        all_bad_sums+=bad_sums
        meshes.append({"mesh":index,"vertex_count":vertex_count,"weight_block_count":weight_blocks,
            "weight_buffer_offset":weight_ptr,"uv_buffer_offset":uv_ptr,
            "actual_weight_span_bytes":actual_bytes,"expected_vertex_times_blocks_times_8":expected_bytes,
            "span_matches_expected":span_ok,"decoded_candidate_slots":vertex_count*weight_blocks,
            "valid_influence_slots":valid_indices,"sentinel_slots":sentinels,
            "invalid_bone_index_slots":bad_indices,"invalid_weight_slots":bad_weights,
            "vertices_with_weight_sum_outside_tolerance":bad_sums,
            "influence_count_histogram":influences_hist,
            "weight_sum_min":min(vertex_sums) if vertex_sums else None,
            "weight_sum_max":max(vertex_sums) if vertex_sums else None,
            "sample_vertices":samples_out})
    return {"format":data[:4].decode("ascii"),"file_size":len(data),"mesh_count":mesh_count,
        "bone_count":bone_count,"meshes_with_exact_weight_span":exact,
        "all_weight_spans_match":exact==mesh_count,"decoded_candidate_slots":all_vertices,
        "valid_influence_slots":all_valid,"sentinel_slots":all_sentinel,
        "invalid_bone_index_slots":all_bad_indices,"invalid_weight_slots":all_bad_weights,
        "vertices_with_weight_sum_outside_tolerance":all_bad_sums,
        "candidate_encoding":{"bone_index":"little-endian uint32","weight":"big-endian float32","sentinel_index":255,
            "validation":"candidate indices in range and active weights sum to 1 within tolerance"},
        "interpretation_warning":"The slot interpretation is strongly supported by range and weight-sum checks, but bone mapping and bind transforms are not yet validated against a rendered rig.",
        "meshes":meshes}

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path)
    ap.add_argument("--samples",type=int,default=3)
    ap.add_argument("--sum-tolerance",type=float,default=0.02)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if args.samples<0 or args.samples>100: ap.error("--samples must be 0..100")
    report=inspect(args.input.read_bytes(),args.samples,args.sum_tolerance)
    rendered=json.dumps(report,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("format","mesh_count","bone_count","all_weight_spans_match","valid_influence_slots","sentinel_slots","invalid_bone_index_slots","invalid_weight_slots","vertices_with_weight_sum_outside_tolerance","interpretation_warning")},indent=2))
    return 0 if report["all_weight_spans_match"] and report["invalid_bone_index_slots"]==0 and report["invalid_weight_slots"]==0 and report["vertices_with_weight_sum_outside_tolerance"]==0 else 2
if __name__=="__main__": raise SystemExit(main())
