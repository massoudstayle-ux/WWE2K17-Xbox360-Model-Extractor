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
- local Euler rotation candidate: three big-endian floats at +0x20
- parent index candidate: big-endian u32 at +0x30 (0xFFFFFFFF is represented as no parent)
- global position candidate: three big-endian floats at +0x40
- additional float at +0x4C

The older `unknown_0x30` and `translation_candidate` keys are retained for report compatibility. These fields have not yet been validated as a complete Godot-compatible bind pose. In particular, matrix conventions, coordinate conversion, and skin-weight-to-bone mapping remain unresolved.

The current CI export remains OBJ + JSON + raw decoded JBOY. It does not produce FBX, and the current geometry exporter does not yet read per-vertex skin weights. Do not treat the OBJ preview as a rigged character.


## Skin-weight buffer boundary validation (2026-11-19)

A new read-only analyzer, `tools/analyze_jboy_skinning.py`, was added after inspecting the generated ch120/ch139 comparison artifact directly.

For every mesh in all four main JBOY model samples, the resolved byte span from the weight-buffer pointer to the UV-buffer pointer exactly equals:

`vertex_count * weight_block_count * 8`

Validation results:
- ch120 SHDC0: 14/14 mesh spans match.
- ch120 SHDC1: 15/15 mesh spans match.
- ch139 SHDC0: 26/26 mesh spans match.
- ch139 SHDC1: 20/20 mesh spans match.

This confirms the per-mesh weight-buffer size and 8-byte slot stride for these 75 meshes. It does **not** yet prove the field order, byte order, or meaning of each 8-byte slot. The analyzer therefore emits raw slot bytes and candidate numeric interpretations only; it deliberately does not label them as decoded bone indices or normalized weights.

The mesh descriptors also contain a palette count and a 20-entry palette area. The palette-to-weight-slot mapping still needs independent validation before generating skin joints and inverse-bind matrices.

Reference format notes describe JBOY mesh palettes and weight buffers as bone-index/weight data, but the current implementation treats that as a hypothesis to verify against these Xbox 360 samples rather than blindly assuming identical packing: https://github.com/KaikoClanworth1/wwe-svr2011-pc/blob/main/docs/SVRMOD_FORMAT.md
