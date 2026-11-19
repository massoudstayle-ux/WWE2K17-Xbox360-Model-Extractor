# JBOY skin-weight decoding progress

## Verified against workflow artifact (2026-11-19)

The latest artifact contains decoded JBOY resources for both uploaded PAC files. The weight buffer length matches **vertex_count × slot_count × 8 bytes** for every extracted mesh tested.

Candidate slot layout:
- 4-byte little-endian bone index
- 4-byte big-endian float32 weight
- bone index 255 is a sentinel/unused slot

Across the main models, all non-sentinel indices are in range and every vertex's active weights sum to 1 (within floating-point tolerance). This strongly supports the candidate decoding, but does not yet prove that bone indices align with the candidate skeleton or that bind transforms are correct.

## Results

| File | Main model vertices | Meshes | Candidate bone count | Invalid indices | Weight-sum failures |
|---|---:|---:|---:|---:|---:|
| ch120 SHDC0 entry0 | 8,857 | 14 | 109 | 0 | 0 |
| ch120 SHDC1 entry0 | 9,403 | 15 | 109 | 0 | 0 |
| ch139 SHDC0 entry0 | 10,395 | 26 | 109 | 0 | 0 |
| ch139 SHDC1 entry0 | 9,575 | 20 | 109 | 0 | 0 |

The same checks also pass for extracted auxiliary JBOY entries in the artifact.

## Next

1. Decode/validate the bone hierarchy and transform records.
2. Determine the correct bind/inverse-bind matrices and coordinate basis.
3. Export a skinned GLB test first (more convenient to inspect), then FBX if the pipeline can preserve skinning.
4. Inspect the model in Godot before claiming successful conversion.
