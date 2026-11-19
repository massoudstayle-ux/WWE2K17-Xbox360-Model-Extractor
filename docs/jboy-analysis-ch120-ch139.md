# JBOY analysis — ch120 / ch139

This note records observations from the generated `ch120-ch139-pac-comparison.zip` artifact. It does not claim that the meshes are skinned or that an FBX export is complete.

## Verified observations

- The extracted JBOY files begin with the ASCII magic `JBOY`.
- The main model summaries consistently report 109 bones for both ch120 and ch139.
- Candidate parent indices are in range for 107/109 bones in the main models. The two entries with raw parent `0xFFFFFFFF` are the `vector` and `null` records. This is a candidate hierarchy, not yet a validated bind pose.
- Mesh vertex totals in the JSON summaries exactly match the vertex records exported to the corresponding OBJ files.
- The summary's `weight_count` values are 1–4, but this field alone does not establish that per-vertex bone indices and normalized skin weights were decoded.

## Main model comparison

| PAC | SHDC entry | Meshes | Bones | Textures | Vertices | Faces |
|---|---|---:|---:|---:|---:|---:|
| ch120 | SHDC0 entry0 | 14 | 109 | 11 | 8,857 | 14,870 |
| ch120 | SHDC1 entry0 | 15 | 109 | 11 | 9,403 | 15,420 |
| ch139 | SHDC0 entry0 | 26 | 109 | 20 | 10,395 | 15,069 |
| ch139 | SHDC1 entry0 | 20 | 109 | 14 | 9,575 | 14,373 |

## Important binary-header observation

For `ch120_SHDC0_entry0_0_JBOY.bin`, the big-endian word at offset `0x04` is 763,024, while the extracted file length is 763,948 bytes. The header also contains plausible counts and offsets (14 meshes, 109 bones, 11 textures, and several offsets near the end of the file). This discrepancy must be resolved before using those offsets as a trusted complete file layout.

## Next required reverse-engineering steps

1. Map each mesh descriptor and prove its start/end ranges against the file.
2. Decode one mesh's vertex attributes and index buffer independently, then compare the decoded positions and faces against its OBJ.
3. Identify the per-vertex influence records: bone indices, weight values, influence count, and byte order.
4. Validate the 109-bone hierarchy and bind transforms using known landmarks (pelvis, spine, thighs, arms).
5. Only after these checks, export a test GLB/FBX and inspect it in Godot/Blender. Keep the original PAC/JBOY files unchanged.

## Status

Geometry and candidate skeleton metadata are extracted. Skin weights, validated bind pose, texture assignment, and FBX/GLB export remain **not yet verified / not implemented**.
