# WWE 2K17 Xbox 360 Model Extractor

Research tools for inspecting **user-provided WWE 2K17 Xbox 360 files** and investigating a path toward extracting wrestler models and converting supported assets to formats such as FBX or glTF/GLB for Godot.

> This project does not include game files, copyrighted assets, or extracted wrestler models.

## Current status

- [x] Repository initialized
- [ ] PAC container structure research
- [ ] PAC header and metadata parser
- [ ] Compression/container identification
- [ ] Internal archive/resource extraction
- [ ] YOBJ/model format research
- [ ] Geometry, skeleton, and texture extraction
- [ ] Export pipeline (only after formats are understood)

## Planned tools

### 1. PAC probe

A read-only Python utility that reports file size, initial bytes, candidate signatures, and entropy. It does **not** modify input files or claim to decompress them.

### 2. Format analysis

Record verified observations and test results in `docs/format-notes.md`. Unknown structures will be labeled as hypotheses until confirmed against multiple files.

### 3. Model conversion

The eventual goal is to investigate model/texture/skeleton extraction and conversion to FBX or GLB. This is not yet implemented.

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
