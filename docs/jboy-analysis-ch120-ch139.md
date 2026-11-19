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

## Bone-record field inspection update

A raw-offset inspector was added at `tools/inspect_jboy_bone_fields.py`. It emits the complete 0x50-byte record, candidate big-endian float groups at offsets 0x10, 0x20, and 0x40, and the raw uint32 at 0x30. These are **not** labeled as translation/rotation/matrix values.

Important parser caution: earlier summary labels for fields at 0x40 and 0x44 overlap by 12 bytes. They must not be treated as two independent transform vectors. The raw inspector now avoids that false separation.

The workflow runs this report for each decoded JBOY. The next validation must compare values across named bones/models and, ideally, a known-good reference rig before assigning transform semantics.


## Heuristic bone-name map

`tools/map_jboy_bones.py` creates a name-based grouping for candidate root, pelvis, spine, neck, head, left/right arms, and left/right legs from each extracted model summary. This is only a naming heuristic. It does not establish bone transforms, parent semantics, skin binding, or an exportable FBX skeleton. The workflow writes JSON reports to `analysis-output/bone-map/`.
\nThe heuristic map report also includes candidate local-position, local-Euler-rotation, global-position, and translation arrays copied from the model summary, plus field-coverage counts. These are raw candidates, not verified transform semantics; notably the earlier raw-field inspection warned that candidate blocks overlap.\n