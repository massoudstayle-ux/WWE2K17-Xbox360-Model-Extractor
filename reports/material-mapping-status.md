# Material Mapping Progress — CH120 / CH139

Source: analysis artifact from GitHub Actions run 44564091342 (downloaded as run79-analysis.zip).

## Verified model extraction

| Character | Main model meshes | Vertices | Faces | Bones | Discarded faces |
|---|---:|---:|---:|---:|---:|
| CH120 SHDC0 | 14 | 8,857 | 14,870 | 109 | 0 |
| CH139 SHDC0 | 26 | 10,395 | 15,069 | 109 | 0 |

## Verified accessory merge reports

- CH120 SHDC0: 2 accessory FBX inputs merged (1 mesh / 24 bones; 2 meshes / 11 bones). 0 rejected.
- CH139 SHDC0: 1 accessory FBX input merged (2 meshes / 11 bones). 0 rejected.
- Merge criteria in report include bone names, rest transforms, armature object transform, and vertex-group mapping.

## Texture audit

- 51 DDS candidates; 51 decoded images in the audit.
- CH120 model summary lists shader names: body, tooth, EYE; texture slot labels include color, normal, mask, hair_shift, hair_noise, wrinkles_n, mf12, sweat_bump, noise2, cubemap_eyes.
- CH139 summary lists shader names: body, EYE, tooth; texture slot labels include color, normal, mask, wrinkles_n, mf12, sweat_bump, noise2, cubemap_eyes, mf01–mf11.
- The DDS visual audit explicitly warns that it does not infer material-to-mesh assignments.

## Status / next step

Extraction and accessory merging are evidenced by reports. Material-to-mesh/UV assignments are **not yet verified**, so this report does not assign DDS files to meshes by guess. Next step is to inspect exported FBX material slots/UVs and shader/resource references, then create a tested mapping for skin, face, hair, clothing, normal and mask maps. Visual validation in Blender or Godot remains pending.
