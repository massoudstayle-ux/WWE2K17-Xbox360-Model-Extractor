#!/usr/bin/env python3
"""Extract non-BPE SHDC resources and validate embedded DDS texture candidates.

This is a conservative recovery pass: it preserves each raw resource and only
labels an embedded DDS when its standard header fields are plausible. It does
not decode proprietary texture formats.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

from parse_hspc import analyze


def dds_header(data: bytes, offset: int) -> dict | None:
    if offset < 0 or offset + 128 > len(data) or data[offset:offset+4] != b"DDS ":
        return None
    size, height, width = struct.unpack_from("<III", data, offset + 4)
    pf_size = struct.unpack_from("<I", data, offset + 76)[0]
    if size != 124 or pf_size != 32 or not (1 <= width <= 32768 and 1 <= height <= 32768):
        return None
    return {"offset": offset, "width": width, "height": height, "header_size": size}


def extract(data: bytes, source_name: str, output_dir: Path) -> dict:
    parsed = analyze(data)
    saved = []
    textures = []
    for item in parsed["shdc_entries"]:
        start, length = item["offset"], item["length"]
        raw = data[start:start+length]
        if item["magic"] == "BPE ":
            continue
        label = f"{source_name}_SHDC{item['parent_index']}_entry{item['index']}_{item['name']}"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / f"{label}.resource.bin"
        raw_path.write_bytes(raw)
        record = {"file": raw_path.name, "bytes": len(raw), "magic": item["magic"]}
        saved.append(record)
        pos = 0
        while True:
            rel = raw.find(b"DDS ", pos)
            if rel < 0:
                break
            info = dds_header(raw, rel)
            if info:
                dds_path = output_dir / f"{label}_dds{rel:08X}.dds"
                dds_path.write_bytes(raw[rel:])
                textures.append({"file": dds_path.name, "bytes": len(raw)-rel, **info})
            pos = rel + 4
    return {
        "source": source_name,
        "non_bpe_resources_saved": len(saved),
        "validated_dds_candidates": len(textures),
        "resources": saved,
        "textures": textures,
        "note": "DDS files are candidates validated by header only; proprietary texture resources may need a separate decoder."
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract non-BPE SHDC resources and DDS candidates.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    result = extract(args.input.read_bytes(), args.input.stem, args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = args.output_dir / f"{args.input.stem}-texture-resource-report.json"
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
