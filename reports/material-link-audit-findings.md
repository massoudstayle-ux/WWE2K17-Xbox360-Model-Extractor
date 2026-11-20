# Material Link Audit — Current Findings

## Read-only audit tool inspected

`tools/audit_jboy_material_links.py` is present in the repository and is designed to:
- Read JBOY/YOBJ mesh descriptor tables and texture/shader tables.
- Collect per-mesh UV counts and UV bounds.
- Report shader-label and descriptor integer fields as **candidates**, not confirmed meanings.
- Validate DDS header dimensions/structure.
- Mark every mesh `material_assignment: UNVERIFIED`.
- Make no changes to source PAC/JBOY/DDS assets.

This is the correct conservative approach. No material assignments should be made until descriptor-field semantics are confirmed against the shader/resource format and visually checked.

## Current artifact evidence

From the analysis artifact:
- 51 DDS files were enumerated and decoded successfully by the image audit (51/51).
- CH120 and CH139 have texture resources grouped by source resource entries A, C, D, E, F, and 10 (as reflected in the extracted filenames).
- The texture audit records dimensions but does not identify the correct mesh/material target.
- FBX merge reports confirm accessories merged without rejection, but they do not verify texture mapping.

## Next validation procedure

1. Run the read-only material-link audit on the original JBOY model files in the workflow.
2. Compare mesh UV bounds and descriptor candidates with the model's texture/shader tables.
3. Preserve the raw candidate values in JSON.
4. Only add a proposed mapping when supported by resource references and UV evidence.
5. Render previews with the proposed materials, then label the mapping visually verified only after inspection.

## Status

Extraction, DDS decoding, and accessory merge are verified by existing artifacts. Material-to-mesh assignments and final visual validation remain pending. No claim of fully textured FBX output is made.
