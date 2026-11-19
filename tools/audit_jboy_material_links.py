#!/usr/bin/env python3
"""Read-only audit of JBOY mesh material/shader candidates and DDS headers.

This tool deliberately does not assign materials. The descriptor fields are
reported as raw candidates until their semantics are confirmed against the
game's shader format. Original PAC/JBOY/DDS files are never modified.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"u32 outside input at 0x{offset:X}")
    return struct.unpack_from(">I", data, offset)[0]


def cstring(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("ascii", "replace")


def dds_info(path: Path) -> dict:
    data = path.read_bytes()
    result = {"file": path.name, "bytes": len(data), "valid_dds_header": False}
    if len(data) >= 128 and data[:4] == b"DDS ":
        size, height, width = struct.unpack_from("<III", data, 4)
        pf_size = struct.unpack_from("<I", data, 76)[0]
        result.update({"valid_dds_header": size == 124 and pf_size == 32,
                       "width": width, "height": height,
                       "header_size": size, "pixel_format_size": pf_size})
    return result


def audit_model(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise ValueError(f"{path}: expected JBOY/YOBJ signature")
    mesh_count = u32(data, 0x18)
    mesh_table = u32(data, 0x1C) + 8
    texture_count = u32(data, 0x24)
    texture_table = u32(data, 0x2C) + 8
    shader_count = u32(data, 0x34)
    shader_table = u32(data, 0x30) + 8
    if mesh_count > 10000 or texture_count > 10000 or shader_count > 10000:
        raise ValueError("Unreasonable table count")
    if mesh_table + mesh_count * 0xB8 > len(data):
        raise ValueError("Mesh descriptor table outside file")
    if texture_table + texture_count * 0x10 > len(data):
        raise ValueError("Texture table outside file")
    if shader_table + shader_count * 0x20 > len(data):
        raise ValueError("Shader table outside file")

    textures = [cstring(data[texture_table+i*0x10:texture_table+(i+1)*0x10])
                for i in range(texture_count)]
    shaders = [cstring(data[shader_table+i*0x20:shader_table+i*0x20+0x20])
               for i in range(shader_count)]
    meshes = []
    for i in range(mesh_count):
        off = mesh_table + i * 0xB8
        vertex_count = u32(data, off)
        uv_ptr = u32(data, off + 0x70) + 8
        uv_count = u32(data, off + 0xA0)
        if uv_count > 2_000_000 or uv_ptr + uv_count * 8 > len(data):
            raise ValueError(f"Mesh {i}: invalid UV buffer")
        uv = [struct.unpack_from(">ff", data, uv_ptr+j*8) for j in range(uv_count)]
        uv_bounds = None
        if uv:
            us, vs = zip(*uv)
            uv_bounds = {"u_min": min(us), "u_max": max(us),
                         "v_min": min(vs), "v_max": max(vs)}
        raw_shader_label = cstring(data[off+0x7C:off+0x8C])
        meshes.append({
            "mesh_index": i,
            "vertex_count": vertex_count,
            "uv_count": uv_count,
            "uv_bounds": uv_bounds,
            "shader_label_candidate": raw_shader_label,
            "descriptor_u32_candidates": {
                "0x78": u32(data, off+0x78),
                "0x8C": u32(data, off+0x8C),
                "0x90": u32(data, off+0x90),
                "0x94": u32(data, off+0x94),
            },
            "material_assignment": "UNVERIFIED"
        })
    return {
        "source": path.name,
        "format": data[:4].decode("ascii"),
        "mesh_count": mesh_count,
        "texture_slots": textures,
        "shader_table": shaders,
        "meshes": meshes,
        "safety_note": "No material assignment was made; descriptor fields remain candidates pending shader-format confirmation."
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model", type=Path)
    ap.add_argument("--dds-dir", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = audit_model(args.model)
    if args.dds_dir:
        report["dds_candidates"] = [
            dds_info(p) for p in sorted(args.dds_dir.glob("*.dds"))
        ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"JBOY_MATERIAL_AUDIT_OK meshes={report['mesh_count']} "
          f"texture_slots={len(report['texture_slots'])} "
          f"shaders={len(report['shader_table'])} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
