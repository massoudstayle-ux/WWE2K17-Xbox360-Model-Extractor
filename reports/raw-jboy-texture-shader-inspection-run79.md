# Raw JBOY Texture/Shader Table Inspection — Run 79

## Scope
Read-only inspection of JBOY binaries included in `run79-analysis.zip`. No source PAC files were changed.

## Verified header tables
- CH120 SHDC0: 14 meshes, 109 bones, 11 texture-name entries, 3 shader-name entries.
- CH139 SHDC0: 26 meshes, 109 bones, 20 texture-name entries, 3 shader-name entries.

## Texture names
CH120 SHDC0: `color`, `normal`, `mask`, `""`, `hair_shift`, `hair_noise`, `wrinkles_n`, `mf12`, `sweat_bump`, `noise2`, `cubemap_eyes`.

CH139 SHDC0: `color`, `normal`, `mask`, `wrinkles_n`, `mf12`, `""`, `sweat_bump`, `noise2`, `cubemap_eyes`, `mf01` through `mf11`.

## Shader names
Both files expose shader names including `body`, `tooth`, and `EYE` (table order differs).

## Limits
These are model-level texture/shader name tables, not verified per-mesh material assignments. The FBX exporter currently creates meshes and UVs, skin weights, and armature; it does not build material nodes or assign extracted DDS images. The run79 artifact ZIP inspected here did not contain a `material-audit/` output directory, so the audit results cannot be confirmed from that artifact.

## Next required step
Run the current workflow against the PAC source and inspect each `*_material-audit.json` report. Then use mesh UV bounds, descriptor fields, shader candidates, and DDS visual previews to test material links. Keep assignments marked as candidates until visual validation confirms them.
