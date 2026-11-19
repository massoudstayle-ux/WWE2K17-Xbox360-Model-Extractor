#!/usr/bin/env python3
"""Validate candidate bone-parent indices and hierarchy in JBOY summary JSON.

This checks structural consistency only. It does not verify transform math,
bone-space conventions, or whether the skeleton visually matches the mesh.
"""
import argparse
import json
from pathlib import Path

def inspect(summary: dict) -> dict:
    bones=summary.get("bones")
    if not isinstance(bones,list):
        raise ValueError("summary must contain a bones array")
    n=len(bones)
    invalid=[]
    roots=[]
    children=[[] for _ in bones]
    for i,b in enumerate(bones):
        if b.get("index")!=i:
            invalid.append({"bone":i,"issue":"index does not match array position","value":b.get("index")})
        p=b.get("parent_index_candidate")
        if p is None:
            roots.append(i)
        elif not isinstance(p,int) or p<0 or p>=n:
            invalid.append({"bone":i,"issue":"parent index out of range","parent":p})
        else:
            children[p].append(i)
    cycle_nodes=[]
    for start in range(n):
        seen=set()
        cur=start
        while cur is not None:
            if cur in seen:
                cycle_nodes.append(start)
                break
            seen.add(cur)
            if cur<0 or cur>=n:
                break
            cur=bones[cur].get("parent_index_candidate")
    return {
        "bone_count":n,
        "root_bones":[{"index":i,"name":bones[i].get("name","")} for i in roots],
        "invalid_parent_records":invalid,
        "cycle_start_bones":sorted(set(cycle_nodes)),
        "hierarchy_structurally_valid":not invalid and not cycle_nodes,
        "children_per_bone":[{"index":i,"name":bones[i].get("name",""),"children":children[i]} for i in range(n) if children[i]],
        "warning":"Parent indices are candidate fields. Structural validity does not prove correct transforms or skin binding."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("summary",type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    result=inspect(json.loads(args.summary.read_text(encoding="utf-8")))
    text=json.dumps(result,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+"\n",encoding="utf-8")
    print(text)
    return 0 if result["hierarchy_structurally_valid"] else 2
if __name__=="__main__":
    raise SystemExit(main())
