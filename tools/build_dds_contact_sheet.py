#!/usr/bin/env python3
"""Build visual contact sheets for recovered DDS candidates; do not guess material links."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from PIL import Image, ImageDraw

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_dir",type=Path)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    files=sorted(args.input_dir.glob("*.dds"))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    records=[]
    thumbs=[]
    for path in files:
        try:
            with Image.open(path) as source:
                image=source.convert("RGBA")
                record={"file":path.name,"width":image.width,"height":image.height,"format":source.format,"mode":source.mode}
                thumb=image.copy()
                thumb.thumbnail((240,150))
                thumbs.append((record,thumb.convert("RGB")))
                records.append(record)
        except Exception as exc:
            records.append({"file":path.name,"error":str(exc)})
    cols=4
    cell_w,cell_h=280,190
    rows=max(1,math.ceil(len(thumbs)/cols))
    sheet=Image.new("RGB",(cols*cell_w,rows*cell_h),(238,238,238))
    draw=ImageDraw.Draw(sheet)
    for i,(record,thumb) in enumerate(thumbs):
        x=(i%cols)*cell_w; y=(i//cols)*cell_h
        sheet.paste(thumb,(x+(cell_w-thumb.width)//2,y+4))
        label=record["file"]
        draw.text((x+5,y+158),label[:40],fill=(0,0,0))
        draw.text((x+5,y+174),f'{record["width"]}x{record["height"]}',fill=(40,40,40))
    sheet.save(args.output_dir/"dds-contact-sheet.jpg",quality=88)
    (args.output_dir/"dds-visual-audit.json").write_text(json.dumps({
        "candidate_count":len(files),
        "decoded_image_count":len(thumbs),
        "records":records,
        "warning":"Visual previews only. Material-to-mesh assignments are not inferred by this audit."
    },indent=2)+"\n",encoding="utf-8")
    print(f"DDS candidates={len(files)}; images decoded={len(thumbs)}; contact sheet={args.output_dir/'dds-contact-sheet.jpg'}")
if __name__=="__main__":
    main()
