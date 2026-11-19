#!/usr/bin/env python3
"""Decode BPE resources in HSPC/SHDC and save recognized JBOY models."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from parse_hspc import analyze as parse_containers
from decode_yuke_bpe import decode_yuke_bpe
from export_jboy_obj import parse_model, export_obj

def extract_models(data: bytes, source_name: str, output_dir: Path) -> dict:
    containers = parse_containers(data)
    saved = []
    errors = []
    for item in containers["shdc_entries"]:
        if item["magic"] != "BPE ":
            continue
        label = f"{source_name}_SHDC{item['index']}_entry{item['name']}"
        try:
            packed = data[item["offset"]:item["offset"]+item["length"]]
            decoded = decode_yuke_bpe(packed)
            if decoded[:4] != b"JBOY":
                continue
            model_path = output_dir / f"{label}_JBOY.bin"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_bytes(decoded)
            record = {"file": model_path.name, "bytes": len(decoded), "signature": "JBOY"}
            try:
                model = parse_model(decoded)
                obj_path = output_dir / f"{label}.obj"
                summary_path = output_dir / f"{label}_summary.json"
                export_obj(model, obj_path)
                summary = {k:v for k,v in model.items() if k != "meshes"}
                summary["meshes"] = [{k:v for k,v in m.items() if k not in ("vertices","uvs","normals","faces")} for m in model["meshes"]]
                summary["total_vertices"] = sum(m["vertex_count"] for m in model["meshes"])
                summary["total_faces"] = sum(len(m["faces"]) for m in model["meshes"])
                summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
                record.update({"obj": obj_path.name, "summary": summary_path.name,
                               "mesh_count": summary["mesh_count"],
                               "bones": summary["bone_count"],
                               "vertices": summary["total_vertices"],
                               "faces": summary["total_faces"]})
            except Exception as exc:
                record["obj_error"] = str(exc)
            saved.append(record)
        except Exception as exc:
            errors.append({"entry": item["name"], "error": str(exc)})
    return {"source": source_name, "jboy_models": saved, "decode_errors": errors}

def main() -> int:
    ap = argparse.ArgumentParser(description="Extract JBOY models from a decompressed PAC resource.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    result = extract_models(args.input.read_bytes(), args.input.name.split(".")[0], args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = args.output_dir / f"{args.input.stem}-model-extraction.json"
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not result["decode_errors"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
