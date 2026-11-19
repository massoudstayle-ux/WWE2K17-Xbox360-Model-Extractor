import bpy
import os
import sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise SystemExit("Usage: blender --background --python render_fbx_previews.py -- input.fbx output.png")

fbx, output = args
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.abspath(fbx))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("Imported FBX contains no mesh objects")

for obj in meshes:
    if not obj.data.materials:
        mat = bpy.data.materials.new("Preview_Neutral")
        mat.diffuse_color = (0.52, 0.52, 0.56, 1.0)
        obj.data.materials.append(mat)

points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
center = (low + high) * 0.5
extent = max(high - low)
if extent <= 0:
    raise RuntimeError("FBX mesh has zero-sized bounds")

camera_data = bpy.data.cameras.new("AuditCamera")
camera = bpy.data.objects.new("AuditCamera", camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = center + Vector((extent * 2.5, -extent * 3.5, extent * 1.25))
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = extent * 1.45
bpy.context.scene.camera = camera

for offset, energy in [
    (Vector((extent * 2, -extent * 2, extent * 3)), 1800),
    (Vector((-extent * 2, -extent, extent * 1.5)), 1100),
]:
    light_data = bpy.data.lights.new("AuditArea", "AREA")
    light_obj = bpy.data.objects.new("AuditArea", light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = center + offset
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = extent * 2
    light_obj.rotation_euler = (center - light_obj.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 768
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.abspath(output)
if scene.world is None:
    scene.world = bpy.data.worlds.new("PreviewWorld")
scene.world.color = (0.08, 0.08, 0.08)
os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("PREVIEW_OK", output, "mesh_objects=", len(meshes))
