#!/usr/bin/env python3
"""Export the main JBOY body mesh set as a rigged FBX using Blender's FBX exporter.

Run inside Blender:
  blender --background --python tools/blender_export_jboy_fbx.py -- input_JBOY.bin output.fbx

This first exporter intentionally targets the main body JBOY only. Hair/lashes
are separate JBOY resources and need a follow-up shared-skeleton merge pass.
"""
from __future__ import annotations
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_jboy_obj import parse_model, u32, f32  # noqa: E402

MESH_RECORD_SIZE = 0xB8
BASIS = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)))
BASIS4 = BASIS.to_4x4()


def source_local_matrix(translation, rotation):
    """Convert source Yuke Euler XYZ values using Rz * Ry * Rx and Y-up basis."""
    rx, ry, rz = rotation
    mx = Matrix.Rotation(rx, 3, "X")
    my = Matrix.Rotation(ry, 3, "Y")
    mz = Matrix.Rotation(rz, 3, "Z")
    source_rot = mz @ my @ mx
    converted_rot = BASIS @ source_rot @ BASIS.transposed()
    converted_pos = BASIS @ Vector(translation[:3])
    result = converted_rot.to_4x4()
    result.translation = converted_pos
    return result


def build_global_matrices(bones):
    count = len(bones)
    result = [None] * count
    visiting = set()

    def resolve(i):
        if result[i] is not None:
            return result[i]
        if i in visiting:
            raise ValueError(f"Bone hierarchy cycle at index {i}")
        visiting.add(i)
        bone = bones[i]
        local = source_local_matrix(
            bone["local_position_candidate"],
            bone["local_rotation_euler_radians_candidate"],
        )
        parent = bone["parent_index_candidate"]
        if parent is None:
            global_matrix = local
        else:
            if not isinstance(parent, int) or parent < 0 or parent >= count or parent == i:
                raise ValueError(f"Invalid parent {parent!r} for bone {i}")
            global_matrix = resolve(parent) @ local
        visiting.remove(i)
        result[i] = global_matrix
        return global_matrix

    for i in range(count):
        resolve(i)
    return result


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def make_armature(bones, matrices):
    data = bpy.data.armatures.new("WWE2K17_Skeleton")
    obj = bpy.data.objects.new("WWE2K17_Skeleton", data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = []
    used_names = set()
    for i, record in enumerate(bones):
        raw_name = record.get("name") or f"Bone_{i:03d}"
        name = raw_name
        if name in used_names:
            name = f"{raw_name}_{i:03d}"
        used_names.add(name)
        eb = data.edit_bones.new(name)
        eb.matrix = matrices[i]
        eb.length = 0.1
        edit_bones.append(eb)
    for i, record in enumerate(bones):
        parent = record.get("parent_index_candidate")
        if parent is not None:
            edit_bones[i].parent = edit_bones[parent]
            edit_bones[i].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return obj, [b.name for b in data.bones]


def mesh_weights(data, descriptor, vertex_count, block_count, palette, bone_count):
    weight_ptr = u32(data, descriptor + 0x6C) + 8
    uv_ptr = u32(data, descriptor + 0x70) + 8
    expected = vertex_count * block_count * 8
    if uv_ptr - weight_ptr != expected:
        raise ValueError(
            f"Mesh at 0x{descriptor:X}: weight span {uv_ptr-weight_ptr} != {expected}"
        )
    result = [[] for _ in range(vertex_count)]
    for vertex in range(vertex_count):
        for block in range(block_count):
            off = weight_ptr + (vertex * block_count + block) * 8
            local_index = data[off]
            if data[off + 1:off + 4] != bytes(3):
                raise ValueError(f"Non-zero influence padding at 0x{off:X}")
            weight = f32(data, off + 4)
            if local_index == 255:
                continue
            if local_index >= len(palette):
                raise ValueError(f"Palette index {local_index} outside palette size {len(palette)}")
            node_index = palette[local_index] - 1
            if node_index < 0 or node_index >= bone_count:
                raise ValueError(f"Palette node {node_index} outside skeleton")
            if not math.isfinite(weight) or weight < 0.0 or weight > 1.0:
                raise ValueError(f"Invalid skin weight {weight}")
            if weight > 0.0:
                result[vertex].append((node_index, weight))
    return result


def export(input_path: Path, output_path: Path):
    raw = input_path.read_bytes()
    model = parse_model(raw)
    if not model["bones"]:
        raise ValueError("No skeleton nodes found")
    matrices = build_global_matrices(model["bones"])
    clear_scene()
    armature, bone_names = make_armature(model["bones"], matrices)

    mesh_table = u32(raw, 0x1C) + 8
    exported_meshes = 0
    total_vertices = 0
    for mesh_info in model["meshes"]:
        i = mesh_info["index"]
        descriptor = mesh_table + i * MESH_RECORD_SIZE
        vertex_count = mesh_info["vertex_count"]
        block_count = u32(raw, descriptor + 0x5C)
        palette_count = u32(raw, descriptor + 0x08)
        if palette_count > 20:
            raise ValueError(f"Mesh {i}: invalid palette count {palette_count}")
        palette = [u32(raw, descriptor + 0x0C + j * 4) for j in range(palette_count)]
        influences = mesh_weights(raw, descriptor, vertex_count, block_count, palette, len(bone_names))

        vertices = [Vector(v) for v in mesh_info["vertices"]]
        faces = [tuple(index - 1 for index in face) for face in mesh_info["faces"]]
        mesh_data = bpy.data.meshes.new(f"BodyMesh_{i:02d}")
        mesh_data.from_pydata(vertices, [], faces)
        mesh_data.update()
        obj = bpy.data.objects.new(f"BodyMesh_{i:02d}", mesh_data)
        bpy.context.collection.objects.link(obj)

        uv_layer = mesh_data.uv_layers.new(name="UVMap")
        for poly in mesh_data.polygons:
            for loop_index in poly.loop_indices:
                vertex_index = mesh_data.loops[loop_index].vertex_index
                u, v = mesh_info["uvs"][vertex_index]
                uv_layer.data[loop_index].uv = (u, v)

        try:
            mesh_data.normals_split_custom_set_from_vertices([Vector(n) for n in mesh_info["normals"]])
        except Exception:
            pass

        groups = {}
        for node_index in sorted({node for row in influences for node, weight in row}):
            groups[node_index] = obj.vertex_groups.new(name=bone_names[node_index])
        for vertex_index, row in enumerate(influences):
            total = sum(weight for _, weight in row)
            if total <= 0.0:
                continue
            for node_index, weight in row:
                groups[node_index].add([vertex_index], weight / total, "REPLACE")

        modifier = obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = armature
        obj.parent = armature
        obj.matrix_parent_inverse = armature.matrix_world.inverted()
        exported_meshes += 1
        total_vertices += vertex_count

    armature.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj != armature:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=False,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward="-Z",
        axis_up="Y",
        path_mode="AUTO",
    )
    print(
        f"FBX_EXPORT_OK meshes={exported_meshes} vertices={total_vertices} "
        f"bones={len(bone_names)} output={output_path}"
    )


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 2:
        raise SystemExit("Usage: blender --background --python blender_export_jboy_fbx.py -- input_JBOY.bin output.fbx")
    export(Path(args[0]), Path(args[1]))


if __name__ == "__main__":
    main()
