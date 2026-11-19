#!/usr/bin/env python3
"""Decode every SHDC BPE resource and recover validated embedded DDS candidates."""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

from parse_hspc import analyze
from decode_yuke_bpe import decode_yuke_bpe


def valid_dds(data: bytes, offset: int) -> dict | None:
    if offset + 128 > len(data) or data[offset:offset+4] != b"DDS ":
        return None
    size, flags, height, width = struct.unpack_from("<4I", data, offset+4)
    pf_size, pf_flags = struct.unpack_from("<2I", data, offset+76)
    fourcc = data[offset+84:offset+88].decode("ascii", "replace")
    rgb_bits = struct.unpack_from("<I", data, offset+88)[0]
    if size != 124 or pf_size != 32 or not (1 <= width <= 16384 and 1 <= height <= 16384):
        return None
    if not (pf_flags & 0x4 or (pf_flags & 0x40 and rgb_bits in (8,16,24,32))):
        return None
    if pf_flags & 0x4 and not fourcc.strip("\x00 "):
        return None
    return {"offset": offset, "width": width, "height": height, "fourcc": fourcc, "rgb_bits": rgb_bits}


def recover(data: bytes, source: str, out: Path) -> dict:
    parsed = analyze(data)
    out.mkdir(parents=True, exist_ok=True)
    decoded_count = 0
    dds = []
    errors = []
    other = []
    for item in parsed["shdc_entries"]:
        if item["magic"] != "BPE ":
            continue
        name = f"{source}_SHDC{item['parent_index']}_entry{item['index']}_{item['name']}"
        packed = data[item["offset"]:item["offset"]+item["length"]]
        try:
            decoded = decode_yuke_bpe(packed)
            decoded_count += 1
            if decoded[:4] != b"JBOY":
                raw_path = out / f"{name}.decoded.bin"
                raw_path.write_bytes(decoded)
                other.append({"file": raw_path.name, "bytes": len(decoded), "magic": decoded[:4].decode("ascii", "replace")})
            pos = 0
            while True:
                rel = decoded.find(b"DDS ", pos)
                if rel < 0:
                    break
                info = valid_dds(decoded, rel)
                if info:
                    dds_path = out / f"{name}_texture{len(dds):03d}.dds"
                    dds_path.write_bytes(decoded[rel:])
                    dds.append({"file": dds_path.name, "bytes": len(decoded)-rel, **info})
                pos = rel + 4
        except Exception as exc:
            errors.append({"entry": name, "error": str(exc)})
    return {
        "source": source,
        "bpe_resources_decoded": decoded_count,
        "other_resources_saved": len(other),
        "validated_dds_candidates": len(dds),
        "dds": dds,
        "other_resources": other,
        "decode_errors": errors,
        "note": "DDS candidates pass standard header checks; image payload size/format and material mapping still require validation."
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Decode BPE resources and recover DDS texture candidates.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    result = recover(args.input.read_bytes(), args.input.stem, args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{args.input.stem}-bpe-textures.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
