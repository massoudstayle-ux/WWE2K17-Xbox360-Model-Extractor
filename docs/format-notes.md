# Format research notes

## Scope

These notes concern the Xbox 360 edition of WWE 2K17 and user-supplied files (for example, wrestler files from a game's `ch` directory). The exact structure of the PAC file and its internal resources is not yet verified.

## Observations to record

For each test file, record:
- file name and size
- first 64–256 bytes (hex)
- candidate signature / magic
- offsets and values only when repeatable
- whether the test was performed on a copy
- tool name, version, command, and result

## Hypotheses (not confirmed)

PAC may be a container, a compressed container, or a wrapper around another resource format. Header bytes alone are not sufficient to identify the format. Do not label data as encrypted/compressed without supporting tests.

## Next investigation

1. Compare headers of several PAC files from the same folder.
2. Compare sizes and any repeated byte patterns.
3. Search for plausible directory tables and offsets, validating that every candidate offset lies within the file.
4. Identify compression only by testing known algorithms against structurally plausible regions and checking output signatures/consistency.
5. Once a nested format is identified, document it and build a parser with bounds checks and test fixtures that contain no copyrighted game data.

## File handling

Never overwrite source PAC files. Keep test input outside this repository. Do not upload game assets.


## Exploratory analyzer additions

The read-only `tools/pac_analyze.py` now reports fixed-window entropy, common embedded signatures, printable ASCII strings, and plausible in-range 32-bit values in both byte orders from the first 256 bytes. Each is a candidate observation, not a confirmed format field.

Automated unit tests cover entropy edge cases, string offsets, signature detection, and bounds filtering. No extraction or decompression is implemented yet.


## Confirmed outer compression signature (2026-11-19)

Both uploaded samples begin with bytes `0F F5 12 ED`. This is identified in QuickBMS community documentation as Xbox 360 `XCOMPRESS_FILE_IDENTIFIER_LZXTDECODE`, associated with `XMemDecompressSegmentTD` rather than ordinary GZIP or the separate LZXNATIVE signature `0F F5 12 EE`.

References:
- QuickBMS XCompress file script is listed by the author's script index as supporting `0x0FF512ED`, `XMemDecompress`, and `0x0FF512EE`.
- The QuickBMS author explains that the ED variant requires the segment decode path and can be handled by QuickBMS / xbdecompress.

The workflow now downloads the official QuickBMS Linux package and official script collection at run time, attempts decompression into `analysis-output/decompressed/`, and records the exit code and output signatures. Original PAC files remain read-only. A successful process exit alone will not be treated as proof of a valid model; the output's magic and internal structure must be checked next.
