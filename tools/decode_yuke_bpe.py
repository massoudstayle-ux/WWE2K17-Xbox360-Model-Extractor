#!/usr/bin/env python3
"""Decoder for the Yukes BPE block format used inside WWE 2K17 resources."""
from __future__ import annotations
import argparse
import struct
from pathlib import Path

class BPEError(ValueError):
    pass

def decode_yuke_bpe(blob: bytes, max_output: int = 128 * 1024 * 1024) -> bytes:
    if len(blob) < 16 or blob[:4] != b"BPE ":
        raise BPEError("Missing BPE header")
    compressed_length, output_length = struct.unpack_from("<II", blob, 8)
    if output_length > max_output:
        raise BPEError(f"Output length {output_length} exceeds safety limit {max_output}")
    if compressed_length != len(blob) - 16:
        raise BPEError(f"Compressed length mismatch: header={compressed_length}, actual={len(blob)-16}")
    src = memoryview(blob)[16:]
    pos = 0
    output = bytearray()
    stack: list[int] = []
    while pos < len(src):
        table: list[tuple[int, int | None] | None] = [None] * 256
        i = 0
        while i < 256:
            if pos >= len(src):
                raise BPEError("Truncated BPE code table")
            c = src[pos]; pos += 1
            if c > 127:
                c -= 127
                while c > 0 and i < 256:
                    table[i] = (i, None)
                    i += 1
                    c -= 1
            c += 1
            while c > 0 and i < 256:
                if pos >= len(src):
                    raise BPEError("Truncated BPE code table")
                n = src[pos]; pos += 1
                right = None
                if i != n:
                    if pos >= len(src):
                        raise BPEError("Truncated BPE code pair")
                    right = src[pos]; pos += 1
                table[i] = (n, right)
                i += 1
                c -= 1
        if pos + 2 > len(src):
            raise BPEError("Missing BPE block size")
        size = src[pos] | (src[pos + 1] << 8)
        pos += 2
        while size or stack:
            if stack:
                n = stack.pop()
            else:
                if pos >= len(src):
                    raise BPEError("Truncated BPE data block")
                n = src[pos]; pos += 1
                size -= 1
            entry = table[n]
            if entry is None:
                raise BPEError("Incomplete BPE code table")
            left, right = entry
            if n == left:
                if len(output) >= output_length:
                    raise BPEError("Decoded output exceeds declared length")
                output.append(n)
            else:
                if right is None or len(stack) + 2 > 4608:
                    raise BPEError("Invalid BPE expansion stack")
                # Expansion order follows the Yukes BPE stack (left, then right).
                stack.append(right)
                stack.append(left)
            if len(output) > output_length:
                raise BPEError("Decoded output exceeds declared length")
    if len(output) != output_length:
        raise BPEError(f"Decoded {len(output)} bytes, expected {output_length}")
    return bytes(output)

def main() -> int:
    ap = argparse.ArgumentParser(description="Decode one Yukes BPE resource.")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    decoded = decode_yuke_bpe(args.input.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(decoded)
    print(f"Decoded {len(decoded)} bytes -> {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
