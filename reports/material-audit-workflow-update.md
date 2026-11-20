# Material Audit Workflow Update

## Change
The `Audit JBOY material slots and UV links (read-only)` workflow step now passes:

```bash
--dds-dir analysis-output/texture-audit
```

to `tools/audit_jboy_material_links.py`.

## What this improves
For each decoded JBOY model, the generated JSON will include the DDS candidate filenames, byte sizes, validity of the DDS header, and width/height when the file is present in the audit folder. This places mesh UV bounds, shader-label candidates, raw descriptor fields, texture-slot names, and candidate DDS metadata in one report.

## Limits (important)
- This does **not** prove which DDS belongs to which mesh/material.
- The current workflow's texture-audit folder copies recovered BPE DDS candidates; other recovered texture-resource paths may not be included.
- The exporter `tools/blender_export_jboy_fbx.py` currently creates geometry, UVs, armature, and skin weights, but does not create Blender materials or link texture images.
- Raw descriptor values remain candidates until shader/material semantics are validated.
- Original PAC/JBOY/DDS files remain untouched.

## Next validation
After a successful Actions run, compare the JBOY audit JSON with DDS dimensions and visual contact sheet. Use UV bounds and shader labels to narrow candidate mappings, then validate in Blender with a small number of material assignments before applying across the character.
