#!/usr/bin/env python3
"""Read-only exploratory analyzer for unknown PAC-like containers.

All findings are candidates, not format claims. The input is never modified.
"""
from __future__ import annotations

import argparse
import math
import struct
import zlib
from collections import Counter
from pathlib import Path

SIGNATURES = {
    b"DDS ": "DDS texture",
    b"\x89PNG\r\n\x1a\n": "PNG image",
    b"\xff\xd8\xff": "JPEG image",
    b"OggS": "Ogg stream",
    b"RIFF": "RIFF container",
    b"PK\x03\x04": "ZIP local header",
    b"\x1f\x8b": "GZIP stream",
    b"\x7fELF": "ELF executable",
}

def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def printable_strings(data: bytes, minimum: int = 5) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    start = None
    for i, value in enumerate(data):
        if 32 <= value <= 126:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= minimum:
                found.append((start, data[start:i].decode("ascii", errors="replace")))
            start = None
    if start is not None and len(data) - start >= minimum:
        found.append((start, data[start:].decode("ascii", errors="replace")))
    return found

def signature_hits(data: bytes) -> list[tuple[int, str]]:
    hits = []
    for signature, label in SIGNATURES.items():
        offset = 0
        while True:
            offset = data.find(signature, offset)
            if offset < 0:
                break
            hits.append((offset, label))
            offset += 1
    return sorted(hits)

def valid_gzip_members(data: bytes, max_output: int = 32 * 1024 * 1024) -> list[tuple[int, int, int, bytes]]:
    """Return (offset, compressed_size, output_size, output_prefix) for validated members."""
    results = []
    marker = b"\x1f\x8b"
    offset = 0
    while True:
        offset = data.find(marker, offset)
        if offset < 0:
            break
        try:
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            output = decoder.decompress(data[offset:], max_output + 1)
            if decoder.eof and len(output) <= max_output:
                trailing = len(decoder.unused_data)
                consumed = len(data) - offset - trailing
                if consumed >= 18:
                    results.append((offset, consumed, len(output), output[:16]))
        except zlib.error:
            pass
        offset += 2
    return results

def aligned_values(data: bytes, endian: str, file_size: int) -> list[tuple[int, int]]:
    fmt = "<I" if endian == "little" else ">I"
    values = []
    limit = min(len(data), 256)
    for pos in range(0, limit - 3, 4):
        value = struct.unpack_from(fmt, data, pos)[0]
        # Candidate absolute offsets only; small values and out-of-file values omitted.
        if 64 <= value < file_size:
            values.append((pos, value))
    return values

def main() -> int:
    parser = argparse.ArgumentParser(description="Explore a binary container without changing it.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--window-size", type=int, default=65536)
    parser.add_argument("--max-strings", type=int, default=80)
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error(f"Not a file: {args.file}")
    if args.window_size < 1024 or args.max_strings < 0:
        parser.error("window-size must be >= 1024 and max-strings >= 0")

    size = args.file.stat().st_size
    with args.file.open("rb") as stream:
        header = stream.read(256)
        stream.seek(0)
        whole = stream.read()

    print("PAC exploratory analysis (read-only)")
    print(f"File: {args.file}")
    print(f"Size: {size} bytes ({size / 1048576:.3f} MiB)")
    print(f"Header (first {len(header)} bytes): {header.hex(' ').upper()}")
    print("\nWindow entropy:")
    for start in range(0, len(whole), args.window_size):
        chunk = whole[start:start + args.window_size]
        print(f"  0x{start:08X}-0x{start + len(chunk):08X}: {entropy(chunk):.4f}")

    print("\nKnown signature candidates:")
    hits = signature_hits(whole)
    if hits:
        for offset, label in hits[:200]:
            print(f"  0x{offset:08X}: {label}")
        if len(hits) > 200:
            print(f"  ... {len(hits) - 200} more")
    else:
        print("  none found")

    print("\nValidated GZIP members (actual decompression check, max output 32 MiB each):")
    gzip_members = valid_gzip_members(whole)
    if gzip_members:
        for offset, compressed_size, output_size, prefix in gzip_members:
            print(f"  0x{offset:08X}: compressed={compressed_size} bytes, output={output_size} bytes, output_prefix={prefix.hex(' ').upper()}")
    else:
        print("  none validated")

    print("\nPrintable ASCII strings (offset, text):")
    strings = printable_strings(whole)
    for offset, value in strings[:args.max_strings]:
        print(f"  0x{offset:08X}: {value[:160]}")
    if not strings:
        print("  none found")
    elif len(strings) > args.max_strings:
        print(f"  ... {len(strings) - args.max_strings} more")

    print("\n32-bit aligned values in first 256 bytes that fall inside file:")
    for endian in ("little", "big"):
        values = aligned_values(header, endian, size)
        print(f"  {endian}-endian: " + (", ".join(f"+0x{p:X}=0x{v:X}" for p, v in values) if values else "none"))

    print("\nInterpretation limits:")
    print("- Raw signature matches are only candidates; validated GZIP members above passed an actual decompression check.")
    print("- In-range integers are only offset candidates, not confirmed pointers.")
    print("- High entropy does not prove encryption or compression.")
    print("- No decompression, extraction, or source-file modification was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
