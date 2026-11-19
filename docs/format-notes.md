# Format research notes

## Scope

These notes concern the Xbox 360 edition of WWE 2K17 and user-supplied files from the game's ch directory. The outer compression and nested HSPC/SHDC/BPE layout are now verified for ch120.pac and ch139.pac.

## Observations and file handling

For each test, record the file name and size, signatures, offsets, validation method, and tool result. Never overwrite source PAC files. Keep test input outside this repository. Do not upload game assets.

## Exploratory analyzer

The read-only tools/pac_analyze.py reports fixed-window entropy, common embedded signatures, printable ASCII strings, and plausible in-range 32-bit values in both byte orders from the first 256 bytes. These are candidate observations, not confirmed fields. Automated unit tests cover entropy edge cases, string offsets, signature detection, and bounds filtering.

## Confirmed outer compression signature (2026-11-19)

Both samples begin with bytes 0F F5 12 ED. This is the Xbox 360 XCOMPRESS_FILE_IDENTIFIER_LZXTDECODE signature associated with XMemDecompressSegmentTD, not ordinary GZIP or the separate LZXNATIVE signature 0F F5 12 EE.

The first QuickBMS attempt was blocked before decoding because the script archive URL returned HTTP 404. This was a tooling/download failure, not evidence that either PAC was invalid.

## XMem TD decompression (2026-11-19)

The workflow builds PopGameTool/XMemCompression from source on a Windows GitHub Actions runner because its C++ sources require windows.h. The implementation is compatibility-oriented reverse engineering, not an official Microsoft decoder.

The successful run completed with exit code 0 for both samples:
- ch120.decompressed.bin: 8,521,728 bytes
- ch139.decompressed.bin: 8,798,208 bytes

Both outputs begin with HSPC. The source PAC files remain unchanged.

## Confirmed nested container layout and first model extraction (2026-11-19)

The decompressed files are HSPC containers. Each HSPC contains two child SHDC containers. The fields validated against both files are:

- HSPC file count: little-endian u32 at 0x38.
- HSPC filename table: starts at 0x800; records are 0x14 bytes (8-byte hashed name followed by padding).
- HSPC data table: FileNameLength - (FileNameLength % 0x800) + 0x1000. Each record is 12 bytes (sector, size), with data offset sector * 0x800 and stored length size * 0x100.
- SHDC mode 1: information table offset at 0x1C and byte length at 0x20; records are 16 bytes (id, offset, length).

Each SHDC contains BPE-compressed resources. The BPE header is BPE-space, version 0x100, packed size at +0x08, and unpacked size at +0x0C. The published Yuke BPE routine (Luigi Auriemma's yuke_bpe reverse-engineering implementation) was validated against all extracted entries; decoded sizes match their declared sizes.

The BPE entry ID 0000 decodes to JBOY, a Yuke character-model format. Additional JBOY entries were found at IDs 2710, 271A, and 4E22 in some SHDC children; ID 006E decodes to YANM; several small entries decode to DUMY.

The JBOY main header uses big-endian values. Confirmed root fields include:
- sub-object count at 0x18
- sub-object header table offset at 0x1C (add 8)
- bone count at 0x20
- texture count at 0x24
- bone data offset at 0x28
- texture reference offset at 0x2C
- shader data offset at 0x30
- shader count at 0x34

A geometry-only OBJ exporter was tested against all main JBOY entries in these samples. For the two ch139 main JBOY variants it exported:
- 10,395 vertices / 15,069 triangles
- 9,575 vertices / 14,373 triangles

Both exports had zero out-of-range triangles. A visual preview confirms a recognizable wrestler-shaped mesh in a T-pose.

Important limitations: OBJ contains geometry and UV coordinates only. Skeleton hierarchy, skin weights, DDS texture resources, material assignments, and FBX export are not yet complete. The model is therefore not yet ready for animation in Godot. The original PAC files were not modified.

## Reference implementations and format research

- pozzum/WrestleMINUS identifies HSPC, SHDC, BPE, and JBOY, and contains JBOY model parsing.
- WrestleMINUS ModelView.vb documents JBOY sub-object vertex, UV, and triangle-strip parsing.
- Luigi Auriemma's Yuke BPE routine is reproduced in the Legends of Modding discussion on BPE compression alternatives.


## Bone-record metadata pass (2026-11-19)

The JBOY exporter now exposes the known 0x50-byte bone-record fields as analysis candidates:
- local position candidate: four big-endian floats at bone record + 0x10
- local translation: three big-endian floats at +0x10 (fourth float retained as a raw candidate)
- local Euler rotation: three big-endian floats at +0x1C
- node metadata words: big-endian u32 at +0x28 and +0x2C
- parent index: big-endian u32 at +0x30 (0xFFFFFFFF is represented as no parent)
- bounding sphere candidate: four big-endian floats at +0x40

The +0x40 block is a bounding-sphere candidate, not a global position. The rotation begins at +0x1C, not +0x20. This field layout agrees with the published Yuke 0x50-byte node-record description. The transform order, coordinate conversion, and inverse-bind construction still need visual validation on these WWE 2K17 Xbox 360 samples before production FBX export.

The current CI export remains OBJ + JSON + raw decoded JBOY. It does not produce FBX yet. The skinning analyzer now resolves palette-local indices and validates weight sums, but the geometry exporter still needs to combine vertex data, node hierarchy, bind transforms, and skin weights into a rigged interchange file. Do not treat the OBJ preview as a rigged character.


## Skin-weight buffer boundary validation (2026-11-19)

A new read-only analyzer, `tools/analyze_jboy_skinning.py`, was added after inspecting the generated ch120/ch139 comparison artifact directly.

For every mesh in all four main JBOY model samples, the resolved byte span from the weight-buffer pointer to the UV-buffer pointer exactly equals:

`vertex_count * weight_block_count * 8`

Validation results:
- ch120 SHDC0: 14/14 mesh spans match.
- ch120 SHDC1: 15/15 mesh spans match.
- ch139 SHDC0: 26/26 mesh spans match.
- ch139 SHDC1: 20/20 mesh spans match.

This confirms the per-mesh weight-buffer size and 8-byte slot stride for these 75 meshes. The layout is now decoded using the published JBOY structure: the descriptor stores a palette count at +0x08, followed by up to 20 big-endian node-index-plus-one values at +0x0C. Each 8-byte influence record stores the palette-local index in its first byte, three zero padding bytes, and a big-endian float32 weight; 0xFF marks an unused influence. The palette stores node-index-plus-one values, so the palette value is reduced by one to obtain the node index. Slots are vertex-major (all weight blocks for vertex 0, then vertex 1, etc.); this ordering is supported by the per-vertex weights summing to 1.0 across the supplied samples.

Validation against all four 109-node main models:
- 75/75 mesh weight spans match the expected size.
- 38,230 vertices checked.
- 91,390 active influence records decoded.
- 40,299 unused influence slots identified.
- Zero nonzero padding bytes in influence records.
- Zero palette-index errors, zero invalid weights, and zero vertices with active weights outside 1.0 ± 0.02.
- Each model uses 101 of its 109 skeleton nodes in the mesh palettes.

The hierarchy candidate checks also found no out-of-range parent references or cycles in the four main models. The node transform parser was corrected in this pass: Euler rotation is read from +0x1C and +0x40 is treated as a bounding-sphere candidate, not a global position. These checks validate the binary mapping and normalized weights, not the final visual deformation. Node rotation order, coordinate conversion, bind pose and inverse-bind matrices still need a renderer/Godot validation pass before a production FBX export. Reference: https://github.com/KaikoClanworth1/wwe-svr2011-pc/blob/main/docs/SVRMOD_FORMAT.md


## FBX and accessory audit (2026-11-19)

The downloaded artifact for workflow run 44558087745 was inspected directly. It contains four non-empty main-body FBX files (ch120/ch139, SHDC0/SHDC1) and the decoded JBOY/JSON analysis outputs. It does not contain an `fbx-accessories/`, `fbx-combined/`, `texture-resources/`, `bpe-textures/`, or `texture-audit/` directory, and it contains no DDS image files. Therefore this artifact proves only the four body FBX exports; it does not prove hair, clothing, eyelashes, or skin textures were merged.

The extracted model summaries identify a promising accessory match for ch120: resource `2710` has 24 bones, including `Bip`, `Bip Spine`, `Bip Spine1`, `Bip Neck`, `Neck_x`, `Bip Head`, and the hair/face bones. These names are present in the 109-node ch120 body skeleton. This is a candidate for the existing strict accessory merge validator; it must still pass the rest-transform and vertex-group checks before being included in a combined FBX. ch139 resource `271A` has 100 bones and is labeled as a towel candidate; do not classify it as clothing until the mesh is visually inspected.

Next validation must run the current workflow revision and inspect its actual artifact. Confirm that separate accessory FBXs were exported, record which passed/rejected the strict shared-skeleton merge, and visually inspect the resulting combined FBX in Blender or Godot. Texture recovery remains incomplete until actual image files decode and their UV/material assignments are confirmed. The original PAC inputs remain read-only.
