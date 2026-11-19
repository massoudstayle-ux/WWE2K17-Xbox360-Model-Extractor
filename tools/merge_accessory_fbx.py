#!/usr/bin/env python3
"""Safely merge compatible accessory FBXs onto a body's existing skeleton.

Usage inside Blender:
  blender --background --python tools/merge_accessory_fbx.py -- body.fbx output.fbx accessory1.fbx [accessory2.fbx ...]

The script refuses an accessory unless its armature is a transform-compatible
subset of the body armature and every mesh vertex group maps to a body bone.
Original input FBXs are read-only; only a new combined FBX and JSON report are
written.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy


def close_matrix(a, b, tolerance=1e-4):
    return all(abs(a[r][c] - b[r][c]) <= tolerance
               for r in range(4) for c in range(4))


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_fbx(path: Path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    return list(set(bpy.data.objects) - before)


def export_selected(path: Path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected exactly one final armature, found {len(armatures)}")
    bpy.context.view_layer.objects.active = armatures[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=False,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward="-Z",
        axis_up="Y",
        path_mode="AUTO",
    )


def merge_one(accessory_path: Path, body_armature, body_bones):
    imported = import_fbx(accessory_path)
    arms = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if len(arms) != 1 or not meshes:
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {"file": accessory_path.name, "status": "rejected",
                "reason": f"expected one armature and at least one mesh; got {len(arms)} armatures and {len(meshes)} meshes"}

    accessory_armature = arms[0]
    accessory_bones = accessory_armature.data.bones
    missing_bones = sorted(set(accessory_bones.keys()) - set(body_bones.keys()))
    if missing_bones:
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {"file": accessory_path.name, "status": "rejected",
                "reason": "accessory skeleton contains bones absent from body",
                "missing_bones": missing_bones[:40], "missing_bone_count": len(missing_bones)}

    if not close_matrix(accessory_armature.matrix_world, body_armature.matrix_world):
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {"file": accessory_path.name, "status": "rejected",
                "reason": "accessory armature object transform differs from body"}

    mismatched = []
    for name in accessory_bones.keys():
        if not close_matrix(accessory_bones[name].matrix_local, body_bones[name].matrix_local):
            mismatched.append(name)
    if mismatched:
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)
        return {"file": accessory_path.name, "status": "rejected",
                "reason": "shared bone rest transforms differ from body",
                "mismatched_bones": mismatched[:40], "mismatched_bone_count": len(mismatched)}

    for mesh in meshes:
        group_names = {group.name for group in mesh.vertex_groups}
        unmapped_groups = sorted(group_names - set(body_bones.keys()))
        armature_modifiers = [mod for mod in mesh.modifiers if mod.type == "ARMATURE"]
        if unmapped_groups or len(armature_modifiers) != 1 or armature_modifiers[0].object != accessory_armature:
            for obj in imported:
                bpy.data.objects.remove(obj, do_unlink=True)
            return {"file": accessory_path.name, "status": "rejected",
                    "reason": "mesh weights/modifier do not map cleanly to body skeleton",
                    "unmapped_vertex_groups": unmapped_groups[:40],
                    "armature_modifier_count": len(armature_modifiers)}

    for mesh in meshes:
        world = mesh.matrix_world.copy()
        modifier = next(mod for mod in mesh.modifiers if mod.type == "ARMATURE")
        modifier.object = body_armature
        mesh.parent = body_armature
        mesh.matrix_parent_inverse = body_armature.matrix_world.inverted()
        mesh.matrix_world = world

    bpy.data.objects.remove(accessory_armature, do_unlink=True)
    return {"file": accessory_path.name, "status": "merged",
            "mesh_count": len(meshes), "bone_count": len(accessory_bones)}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("Usage: blender --background --python merge_accessory_fbx.py -- body.fbx output.fbx [accessory.fbx ...]")

    body_path, output_path = Path(args[0]), Path(args[1])
    accessory_paths = [Path(value) for value in args[2:]]
    clear_scene()
    body_objects = import_fbx(body_path)
    body_armatures = [obj for obj in body_objects if obj.type == "ARMATURE"]
    if len(body_armatures) != 1:
        raise RuntimeError(f"Body FBX must contain exactly one armature; found {len(body_armatures)}")
    body_armature = body_armatures[0]
    body_bones = body_armature.data.bones

    results = []
    for accessory in accessory_paths:
        if not accessory.is_file():
            results.append({"file": accessory.name, "status": "rejected", "reason": "file not found"})
            continue
        results.append(merge_one(accessory, body_armature, body_bones))

    final_objects = list(bpy.context.scene.objects)
    export_selected(output_path, final_objects)
    report = {
        "body": body_path.name,
        "output": output_path.name,
        "body_bone_count": len(body_bones),
        "accessory_results": results,
        "merged_accessories": sum(item["status"] == "merged" for item in results),
        "rejected_accessories": sum(item["status"] == "rejected" for item in results),
        "note": "Only accessories with matching bone names, rest transforms, armature object transform, and vertex-group mappings are merged. Rejected files remain separate inputs.",
    }
    report_path = output_path.with_suffix(".merge-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
