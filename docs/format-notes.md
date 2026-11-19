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
