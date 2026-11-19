# WWE 2K17 Xbox 360 Model Extractor

Research tools for inspecting **user-provided WWE 2K17 Xbox 360 files** and converting supported wrestler resources into rigged FBX assets for Godot.

> This project does not include game files, copyrighted assets, or extracted wrestler models in the Git repository. Generated analysis artifacts are temporary GitHub Actions outputs.

## Current status (2026-11-19)

- [x] PAC container analysis and XMem TD decompression for `ch120.pac` and `ch139.pac`
- [x] HSPC / SHDC / BPE resource extraction and JBOY mesh decoding
- [x] Main-body rigged FBX export for SHDC0 and SHDC1 variants
- [x] Decode separate hair / face / accessory JBOY resources into FBX candidates
- [x] Merge compatible accessories into the matching 109-bone body skeleton
- [x] Recover and visually preview DDS texture candidates
- [ ] Match JBOY material/shader texture slots to the correct mesh sub-objects
- [ ] Assign diffuse, normal, mask, hair, skin, and clothing materials in FBX
- [ ] Validate bind pose, orientation, skin deformation, and appearance in Godot

## Verified results: workflow run 79

The successful [GitHub Actions run 79](https://github.com/massoudstayle-ux/WWE2K17-Xbox360-Model-Extractor/actions/runs/44564091342) produced four combined FBX files:

- `ch120_SHDC0_entry0_0-complete.fbx`
- `ch120_SHDC1_entry0_0-complete.fbx`
- `ch139_SHDC0_entry0_0-complete.fbx`
- `ch139_SHDC1_entry0_0-complete.fbx`

The accessory merge reports confirm seven successful accessory merges across the four outputs, with zero rejected accessories:
- ch120: the 24-bone `2710` hair resource and 11-bone `4E22` face/eyelash resource merged into both SHDC variants.
- ch139 SHDC0: the 11-bone `4E22` face/eyelash resource merged.
- ch139 SHDC1: the 100-bone `271A` towel/accessory candidate and 11-bone `4E22` face/eyelash resource merged. The `271A` mesh still needs visual review before calling it clothing.

The workflow also decoded 30 BPE resources from ch120 and 29 from ch139, recovering 20 and 31 DDS candidates respectively (51 total). The visual contact sheet includes skin/face UV atlases and clothing/gear UV regions, including shirts, trousers, shoes, wrist gear, and body skin. These are recovered texture candidates; material-to-mesh assignments have not yet been completed.

## Important limitations

- Successful automated merging proves matching bone names, rest transforms, armature transforms, and vertex-group mappings. It does **not** prove visual correctness in Godot.
- The DDS contact sheet is a preview only. The main texture atlas clearly contains skin and clothing regions, but the model's material slots and shader assignments still need to be decoded before the FBX can display them correctly.
- Do not assume every body sub-mesh is clothing. Keep the SHDC0/SHDC1 variants separate until they are compared in a renderer.
- The original PAC files are read-only inputs and must not be overwritten or committed.

## Usage

Python 3.10+ is recommended.

```bash
python tools/pac_probe.py path/to/ch150.pac
```

## Safety and legal notes

- Use files from a game copy you own and are legally permitted to inspect.
- Do not commit original game files, extracted assets, or copyrighted content.
- Keep source files unchanged; tools should operate read-only by default.
- This is an independent research project and is not affiliated with WWE or 2K.

## License

The repository tools are licensed under the MIT License. See [LICENSE](LICENSE).
