#!/usr/bin/env python3
"""Create a heuristic name-based bone map from a JBOY model summary.

Labels are hints only; they are not proof of bone semantics or rig correctness.
"""
import argparse
import json
import re
from pathlib import Path

LABELS = {
    "root": (r"\broot\b",),
    "pelvis": (r"pelvis|hip",),
    "spine": (r"spine|torso|chest",),
    "neck": (r"\bneck\b",),
    "head": (r"(?:^|[^a-z0-9])head(?:$|[^a-z0-9])",),
    "left_arm": (r"left.*(arm|shoulder|hand)|l_(arm|shoulder|hand)|\barm_l\b",),
    "right_arm": (r"right.*(arm|shoulder|hand)|r_(arm|shoulder|hand)|\barm_r\b",),
    "left_leg": (r"left.*(leg|thigh|knee|foot)|l_(leg|thigh|knee|foot)|\bleg_l\b",),
    "right_leg": (r"right.*(leg|thigh|knee|foot)|r_(leg|thigh|knee|foot)|\bleg_r\b",),
}

def classify(name):
    text = str(name or "").lower()
    return [label for label, patterns in LABELS.items() if any(re.search(p, text) for p in patterns)]

def inspect(summary):
    bones = summary.get("bones")
    if not isinstance(bones, list):
        raise ValueError("summary must contain a bones array")
    n = len(bones)
    mapped = []
    parent_errors = []
    for i, bone in enumerate(bones):
        parent = bone.get("parent_index_candidate")
        valid = parent is None or (isinstance(parent, int) and 0 <= parent < n and parent != i)
        if not valid:
            parent_errors.append({"bone_index": i, "parent_candidate": parent})
        mapped.append({
            "index": bone.get("index", i),
            "name": bone.get("name", ""),
            "name_based_labels": classify(bone.get("name", "")),
            "parent_index_candidate": parent,
            "parent_candidate_valid": valid,
            "candidate_transform_fields": {"local_position_candidate": bone.get("local_position_candidate"), "local_rotation_euler_radians_candidate": bone.get("local_rotation_euler_radians_candidate"), "global_position_candidate": bone.get("global_position_candidate"), "translation_candidate": bone.get("translation_candidate"), "unknown_float_0x4C": bone.get("unknown_float_0x4C")},
        })
    label_groups = {}
    for b in mapped:
        for label in b["name_based_labels"]:
            label_groups.setdefault(label, []).append({"index": b["index"], "name": b["name"]})
    return {
        "bone_count": n,
        "name_based_label_groups": label_groups,
        "bones": mapped,
        "invalid_parent_candidates": parent_errors, "transform_field_coverage": {"bones_with_local_position_candidate": sum(b.get("local_position_candidate") is not None for b in bones), "bones_with_local_rotation_candidate": sum(b.get("local_rotation_euler_radians_candidate") is not None for b in bones), "bones_with_global_position_candidate": sum(b.get("global_position_candidate") is not None for b in bones), "bones_with_translation_candidate": sum(b.get("translation_candidate") is not None for b in bones)},
        "interpretation_warning": "Labels are inferred from names only. Parent and transform candidates remain unverified; this is not an FBX skeleton map."
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = inspect(json.loads(args.summary.read_text(encoding="utf-8")))
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not report["invalid_parent_candidates"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
