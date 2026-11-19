# WWE 2K17 Xbox 360 Model Extractor

Research tools for inspecting **user-provided WWE 2K17 Xbox 360 files** and investigating a path toward extracting wrestler models and converting supported assets to formats such as FBX or glTF/GLB for Godot.

> This project does not include game files, copyrighted assets, or extracted wrestler models.

## Current status

- [x] Repository initialized
- [x] PAC container structure research for ch120.pac and ch139.pac
- [x] XMem TD decompression and HSPC/SHDC/BPE resource extraction
- [x] JBOY geometry extraction to OBJ
- [x] 109-node hierarchy and skin-weight structure analysis
- [ ] Verify node transforms and inverse-bind matrices in a renderer
- [ ] Rigged GLB/FBX export and visual validation in Godot

## Planned tools

### 1. PAC probe

A read-only Python utility that reports file size, initial bytes, candidate signatures, and entropy. It does **not** modify input files or claim to decompress them.

### 2. Format analysis

Record verified observations and test results in `docs/format-notes.md`. Unknown structures will be labeled as hypotheses until confirmed against multiple files.

### 3. Model conversion

Static OBJ geometry is exported. The repository also validates mesh palettes, per-vertex influence records, and candidate node hierarchy. Rigged GLB/FBX export is still in progress; current OBJ previews are not animated characters.

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
