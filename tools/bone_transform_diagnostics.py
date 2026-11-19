#!/usr/bin/env python3
"""Report plausibility checks for JBOY bone candidates without assigning semantics."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

VECTOR_FIELDS = ("local_position_candidate", "local_rotation_euler_radians_candidate", "global_position_candidate", "translation_candidate")

def _vec(value):
    return isinstance(value, list) and len(value) in (3, 4) and all(isinstance(x, (int, float)) and math.isfinite(x) for x in value)

def inspect(summary: dict) -> dict:
    bones = summary.get("bones")
    if not isinstance(bones, list):
        raise ValueError("summary must contain a bones array")
    count = len(bones)
    parent_errors, field_stats, bone_reports = [], {}, []
    parents = {}
    for i, bone in enumerate(bones):
        idx = bone.get("index", i)
        parent = bone.get("parent_index_candidate")
        valid = parent is None or (isinstance(parent, int) and 0 <= parent < count and parent != i)
        if not valid:
            parent_errors.append({"bone_index": idx, "parent_candidate": parent})
        if valid and parent is not None:
            parents[i] = parent
        report = {"index": idx, "name": bone.get("name", ""), "parent_candidate": parent, "parent_valid": valid, "fields": {}}
        for field in VECTOR_FIELDS:
            value = bone.get(field)
            usable = _vec(value)
            report["fields"][field] = {"present": value is not None, "valid_numeric_vector": usable, "value": value if usable else None}
            if usable:
                magnitude = math.sqrt(sum(float(x)*float(x) for x in value[:3]))
                field_stats.setdefault(field, []).append(magnitude)
        bone_reports.append(report)
    cycles = []
    for start in range(count):
        seen, node = set(), start
        while node in parents:
            if node in seen:
                cycles.append(sorted(seen))
                break
            seen.add(node)
            node = parents[node]
    unique_cycles = []
    for cycle in cycles:
        if cycle not in unique_cycles:
            unique_cycles.append(cycle)
    stats = {field: {"valid_count": len(mags), "magnitude_min": min(mags), "magnitude_max": max(mags), "magnitude_mean": sum(mags)/len(mags)} for field, mags in field_stats.items()}
    return {"bone_count": count, "candidate_parent_invalid_count": len(parent_errors), "candidate_parent_invalid": parent_errors,
        "candidate_parent_cycle_count": len(unique_cycles), "candidate_parent_cycles": unique_cycles,
        "vector_field_statistics": stats, "bones": bone_reports,
        "warnings": ["Magnitude statistics do not identify units or coordinate basis.",
        "global_position_candidate and translation_candidate may overlap raw record bytes and must not be treated as independent.",
        "No transform, parent hierarchy, bind pose, or skinning semantics are confirmed."]}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("summary", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = inspect(json.loads(args.summary.read_text(encoding="utf-8")))
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("bone_count", "candidate_parent_invalid_count", "candidate_parent_cycle_count", "vector_field_statistics", "warnings")}, indent=2))
    return 0 if not report["candidate_parent_invalid_count"] and not report["candidate_parent_cycle_count"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
