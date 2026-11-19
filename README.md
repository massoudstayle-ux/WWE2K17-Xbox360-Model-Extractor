# WWE 2K17 Xbox 360 Model Extractor

Research tools for inspecting **user-provided WWE 2K17 Xbox 360 files** and investigating a path toward extracting wrestler models and converting supported assets to formats such as FBX or glTF/GLB for Godot.

> This project does not include game files, copyrighted assets, or extracted wrestler models.

## Current status

- [x] Repository initialized
- [x] PAC container structure research for ch120.pac and ch139.pac
- [x] XMem TD decompression and HSPC/SHDC/BPE resource extraction
- [x] JBOY geometry extraction to OBJ
- [x] 109-node hierarchy and skin-weight structure analysis
- [x] Add a first rigged FBX export stage for SHDC0/SHDC1 main-body JBOY resources
- [ ] Run and inspect the latest FBX export artifact; verify bone transforms, bind pose, and deformation in Godot
- [ ] Match accessory bone hierarchies to the body skeleton and merge compatible meshes
- [ ] Decode texture resources, identify image formats, and assign skin, hair, and clothing materials


## Resource findings from ch120.pac and ch139.pac

The successful run 73 artifact contains these separate decoded resources:

- `ch120`: body variants with 109 bones, a separate `2710` hair mesh (1,756 vertices, 24 bones), and a separate `4E22` eyelash/eyeshadow resource (352 vertices, 11 bones).
- `ch139`: body variants with 109 bones, a separate `4E22` eyelash/eyeshadow resource (417 vertices, 11 bones), and a `271A` resource labeled `towel` (209 vertices, 100 bones).
- The body resources contain multiple mesh sub-objects. Their exact clothing/material assignments still need shader and texture mapping; do not assume every sub-object is clothing.

The workflow now includes:
- Rigged FBX candidate export for non-body JBOY resources, stored separately from the body FBXs.
- Decoding of all SHDC BPE resources and recovery of DDS candidates only when the decompressed data passes standard DDS header checks.
- A conservative raw non-BPE SHDC resource dump for later format identification.

Separate accessory FBXs are not yet proven compatible with the body's 109-bone skeleton. Texture candidates are not yet visually verified or assigned to skin, hair, and clothing materials.

## Planned tools

### 1. PAC probe

A read-only Python utility that reports file size, initial bytes, candidate signatures, and entropy. It does **not** modify input files or claim to decompress them.

### 2. Format analysis

Record verified observations and test results in `docs/format-notes.md`. Unknown structures will be labeled as hypotheses until confirmed against multiple files.

### 3. Model conversion

Static OBJ geometry is exported. The repository validates mesh palettes, per-vertex influence records, and candidate node hierarchy. A first Blender-based rigged FBX export stage now targets the main-body JBOY resources in both SHDC0 and SHDC1 variants. This exporter is still a prototype: its transforms and deformation must be visually validated in Godot, and separate hair, eyelashes, clothing, and accessory resources have not yet been merged. Do not treat the FBX export step as a visually verified complete wrestler until that validation is finished.

## Usage

Python 3.10+ is recommended.

```bash
python tools/pac_probe.py path/to/ch150.pac
```

## Safety and legal notes

- Use files from a game copy you own and are legally permitted to inspect.
- Do not commit original game files, extracted assets, keys, or copyrighted content.
- Keep source files unchanged; tools should operate read-only by default.
- This is an independent research project and is not affiliated with WWE or 2K.

## License

The code in this repository is licensed under the MIT License. See [LICENSE](LICENSE).
