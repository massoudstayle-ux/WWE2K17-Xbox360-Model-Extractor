#!/usr/bin/env python3
"""Export static OBJ geometry from a decoded WWE 2K17 JBOY/YOBJ resource.

The binary field layout and triangle-strip interpretation were cross-checked
against WrestleMINUS (Pozzum, MIT License). This exporter does not build a rig.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path

class JBOYError(ValueError):
    pass

def u32(data: bytes, off: int) -> int:
    if off < 0 or off + 4 > len(data):
        raise JBOYError(f"u32 outside JBOY at 0x{off:X}")
    return struct.unpack_from(">I", data, off)[0]

def u16(data: bytes, off: int) -> int:
    if off < 0 or off + 2 > len(data):
        raise JBOYError(f"u16 outside JBOY at 0x{off:X}")
    return struct.unpack_from(">H", data, off)[0]

def f32(data: bytes, off: int) -> float:
    if off < 0 or off + 4 > len(data):
        raise JBOYError(f"float outside JBOY at 0x{off:X}")
    value = struct.unpack_from(">f", data, off)[0]
    if not math.isfinite(value):
        raise JBOYError(f"Non-finite float at 0x{off:X}")
    return value

def check_range(data: bytes, off: int, size: int, label: str) -> None:
    if off < 0 or size < 0 or off + size > len(data):
        raise JBOYError(f"{label} range 0x{off:X}+0x{size:X} outside file size 0x{len(data):X}")

def parse_triangle_strips(data: bytes, faces_offset: int) -> tuple[list[tuple[int,int,int]], int]:
    base = faces_offset + 8
    count = u32(data, base + 4)
    if count > 10_000_000:
        raise JBOYError(f"Unreasonable face-index count: {count}")
    check_range(data, base + 12, count * 2, "face indices")
    indices = [u16(data, base + 12 + i * 2) + 1 for i in range(count)]
    strips: list[list[int]] = []
    fi = 0
    buffer_face = False
    while fi < count - 3:
        strip: list[int] = []
        while fi < count - 4:
            vertex = indices[fi]
            if len(strip) == 0:
                if buffer_face:
                    strip.append(0)
                    buffer_face = False
                strip.append(vertex)
                fi += 1
            elif len(strip) in (1, 2):
                if vertex in strip:
                    break
                strip.append(vertex)
                fi += 1
            else:
                if strip[-1] == vertex:
                    strips.append(strip)
                    break
                if strip[-2] == vertex:
                    fi -= 1
                    buffer_face = True
                    strips.append(strip)
                    break
                strip.append(vertex)
                fi += 1
        if fi == count - 4:
            strip.append(indices[fi])
            strips.append(strip)
            fi += 1
    faces: list[tuple[int,int,int]] = []
    for strip in strips:
        clockwise = True
        if strip and strip[0] == 0:
            strip = strip[1:]
        elif len(strip) % 2 == 1:
            clockwise = False
        for i in range(len(strip) - 2):
            if strip[i] == 0:
                continue
            if not clockwise:
                tri = ((strip[i], strip[i+1], strip[i+2]) if i % 2 == 1
                       else (strip[i], strip[i+2], strip[i+1]))
            else:
                tri = ((strip[i], strip[i+2], strip[i+1]) if i % 2 == 1
                       else (strip[i], strip[i+1], strip[i+2]))
            faces.append(tri)
    return faces, count

def parse_model(data: bytes, emote: int = 0) -> dict:
    if data[:4] not in (b"JBOY", b"YOBJ"):
        raise JBOYError("Model must start with JBOY or YOBJ")
    sub_count = u32(data, 0x18)
    header_start = u32(data, 0x1C) + 8
    bone_count = u32(data, 0x20)
    texture_count = u32(data, 0x24)
    bone_offset = u32(data, 0x28) + 8
    texture_offset = u32(data, 0x2C) + 8
    shader_offset = u32(data, 0x30) + 8
    shader_count = u32(data, 0x34)
    if sub_count > 10000 or bone_count > 10000 or texture_count > 10000:
        raise JBOYError("Unreasonable model header counts")
    check_range(data, header_start, sub_count * 0xB8, "sub-object headers")
    check_range(data, bone_offset, bone_count * 0x50, "bone records")
    check_range(data, texture_offset, texture_count * 0x10, "texture names")
    check_range(data, shader_offset, shader_count * 0x20, "shader names")

    bones = []
    for i in range(bone_count):
        off = bone_offset + i * 0x50
        raw_name = data[off:off+0x10].split(b"\0", 1)[0]
        parent_raw = u32(data, off + 0x30)
        bones.append({
            "index": i,
            "name": raw_name.decode("ascii", "replace"),
            # Yuke's 0x50-byte bone record. These transform fields are exposed
            # for analysis; they are not yet converted into a verified rig.
            "parent_index_candidate": None if parent_raw == 0xFFFFFFFF else parent_raw,
            "parent_raw_0x30": parent_raw,
            "local_position_candidate": [f32(data, off + 0x10 + j*4) for j in range(4)],
            "local_rotation_euler_radians_candidate": [f32(data, off + 0x1C + j*4) for j in range(3)],
            "node_u40_candidate": u32(data, off + 0x28),
            "node_u44_candidate": u32(data, off + 0x2C),
            "bounding_sphere_candidate": [f32(data, off + 0x40 + j*4) for j in range(4)],
            # Keep the previous field name for existing report consumers.
            "unknown_0x30": parent_raw,
            "translation_candidate": [f32(data, off + 0x10 + j*4) for j in range(3)]
        })
    textures = [
        data[texture_offset+i*0x10:texture_offset+(i+1)*0x10].split(b"\0",1)[0].decode("ascii","replace")
        for i in range(texture_count)
    ]
    shaders = [
        data[shader_offset+i*0x20:shader_offset+i*0x20+0x10].split(b"\0",1)[0].decode("ascii","replace")
        for i in range(shader_count)
    ]

    meshes = []
    for i in range(sub_count):
        off = header_start + i * 0xB8
        vertex_count = u32(data, off)
        weight_count = u32(data, off + 0x5C)
        vertex_head_count = u32(data, off + 0x64)
        vertex_offset = u32(data, off + 0x68)
        weight_offset = u32(data, off + 0x6C)
        uv_offset = u32(data, off + 0x70)
        normal_offset = u32(data, off + 0x74)
        faces_offset = u32(data, off + 0x9C)
        uv_count = u32(data, off + 0xA0)
        if vertex_count > 2_000_000 or vertex_head_count > 128 or weight_count > 32:
            raise JBOYError(f"Unreasonable mesh counts in object {i}")
        if vertex_head_count == 0 or emote >= vertex_head_count:
            raise JBOYError(f"Requested emote {emote} unavailable for object {i}")
        pointer_pos = vertex_offset + 8 + emote * 4
        vertex_pos = u32(data, pointer_pos) + 8
        check_range(data, vertex_pos, vertex_count * 0x1C, f"object {i} vertices")
        check_range(data, uv_offset + 8, uv_count * 8, f"object {i} UVs")
        check_range(data, normal_offset + 8, vertex_count * 12, f"object {i} normals")
        if uv_count != vertex_count:
            raise JBOYError(f"Object {i}: UV count {uv_count} != vertex count {vertex_count}")

        vertices = []
        for j in range(vertex_count):
            p = vertex_pos + j * 0x1C
            x = f32(data, p)
            z = -f32(data, p + 4)
            y = f32(data, p + 8)
            vertices.append((x, y, z))
        uvs = [(f32(data, uv_offset+8+j*8), -f32(data, uv_offset+12+j*8)) for j in range(uv_count)]
        normals = []
        for j in range(vertex_count):
            p = normal_offset + 8 + j * 12
            normals.append((f32(data,p), f32(data,p+8), -f32(data,p+4)))
        faces, index_count = parse_triangle_strips(data, faces_offset)
        valid_faces = [face for face in faces if min(face) >= 1 and max(face) <= vertex_count]
        meshes.append({
            "index": i, "vertex_count": vertex_count, "weight_count": weight_count,
            "vertex_head_count": vertex_head_count, "vertices": vertices,
            "uvs": uvs, "normals": normals, "faces": valid_faces,
            "face_index_count": index_count, "discarded_faces": len(faces)-len(valid_faces)
        })
    return {
        "format": data[:4].decode("ascii"), "file_size": len(data),
        "mesh_count": sub_count, "bone_count": bone_count,
        "texture_count": texture_count, "shader_count": shader_count,
        "bones": bones, "textures": textures, "shaders": shaders, "meshes": meshes
    }

def export_obj(model: dict, output: Path) -> None:
    lines = [
        "# Static mesh export from a WWE 2K17 JBOY/YOBJ resource",
        "# OBJ does not preserve skeletons or skin weights; see companion JSON."
    ]
    vertex_base = uv_base = normal_base = 1
    for mesh in model["meshes"]:
        lines.append(f"\ng Object_{mesh['index']:02d}")
        for x,y,z in mesh["vertices"]:
            lines.append(f"v {x:.8f} {y:.8f} {z:.8f}")
        for u,v in mesh["uvs"]:
            lines.append(f"vt {u:.8f} {v:.8f}")
        for x,y,z in mesh["normals"]:
            lines.append(f"vn {x:.8f} {y:.8f} {z:.8f}")
        for a,b,c in mesh["faces"]:
            va,vb,vc = (vertex_base+a-1, vertex_base+b-1, vertex_base+c-1)
            ta,tb,tc = (uv_base+a-1, uv_base+b-1, uv_base+c-1)
            na,nb,nc = (normal_base+a-1, normal_base+b-1, normal_base+c-1)
            lines.append(f"f {va}/{ta}/{na} {vb}/{tb}/{nb} {vc}/{tc}/{nc}")
        vertex_base += len(mesh["vertices"])
        uv_base += len(mesh["uvs"])
        normal_base += len(mesh["normals"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser(description="Export static OBJ from a decoded JBOY model.")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--summary", type=Path)
    ap.add_argument("--emote", type=int, default=0)
    args = ap.parse_args()
    model = parse_model(args.input.read_bytes(), args.emote)
    export_obj(model, args.output)
    summary = {k:v for k,v in model.items() if k != "meshes"}
    summary["meshes"] = [{k:v for k,v in m.items() if k not in ("vertices","uvs","normals","faces")} for m in model["meshes"]]
    summary["total_vertices"] = sum(m["vertex_count"] for m in model["meshes"])
    summary["total_faces"] = sum(len(m["faces"]) for m in model["meshes"])
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {summary['mesh_count']} meshes, {summary['total_vertices']} vertices, {summary['total_faces']} faces -> {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
