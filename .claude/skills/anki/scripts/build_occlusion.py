#!/usr/bin/env python3
"""
build_occlusion.py — turn chosen regions into an Anki `Occlusion` field value.

Input JSON (stdin or --in):
  {"regions":[{"left":..,"top":..,"width":..,"height":..,"text":"..."}, ...],
   "mode":"one"|"all"}

  mode "one" (default) -> oi=1, hide-one-at-a-time (each region its own card)
  mode "all"           -> oi=0, hide-all-guess-one

Output: the exact string for the Image Occlusion note's `Occlusion` field.

  --keep 1,2,3        keep only these groups (drop titles, credits, junk)
  --preview FIG.png   also draw the kept boxes onto the figure so you can check
                      them — works without OCR, so use it for hand-estimated rects

Hand-estimated regions (no OCR available, or a structure with no text label)
use the same JSON shape; give each distinct label its own "group" number.

Anki native Image Occlusion syntax (verified against a real note):
  {{c1::image-occlusion:rect:left=.2755:top=.077:width=.2783:height=.069:oi=1}}
Coordinates are FRACTIONS of image dimensions (0-1), not pixels.
Shapes joined by <br>, trailing <br>. Each c<n> generates one card.
"""
import argparse, json, sys


def fmt(v):
    """Anki writes leading-dot decimals (.2755). Match that, clamped to 0-1."""
    v = max(0.0, min(1.0, float(v)))
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    if s == "":
        return "0"
    return s[1:] if s.startswith("0.") else s


def cloze_indices(regions):
    """Dense 1..N cloze index per region. Regions sharing a `group` share an
    index; a region with no `group` (e.g. a hand-estimated rect) is its own."""
    remap, out = {}, []
    for i, r in enumerate(regions):
        g = r.get("group", ("solo", i))
        if g not in remap:
            remap[g] = len(remap) + 1
        out.append(remap[g])
    return out


def build(regions, mode="one"):
    """Regions sharing a `group` share a cloze index, so every instance of a
    repeated label hides together. Kept groups are renumbered to a dense 1..N
    so Anki gets contiguous cloze indices after dropping junk."""
    oi = "1" if mode == "one" else "0"
    idxs = cloze_indices(regions)
    parts = []
    for r, idx in zip(regions, idxs):
        parts.append(
            "{{c%d::image-occlusion:rect:left=%s:top=%s:width=%s:height=%s:oi=%s}}"
            % (idx, fmt(r["left"]), fmt(r["top"]),
               fmt(r["width"]), fmt(r["height"]), oi)
        )
    return "<br>".join(parts) + "<br>"


def draw_preview(image_path, regions, out_path):
    """Draw the regions that will actually be occluded, labelled with the cloze
    index each will get. Needs only Pillow — no OCR — so it also checks rects
    estimated by eye (tag those notes #...::!Flags::IO_estimated)."""
    from PIL import Image, ImageDraw
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    palette = [(220,30,30),(0,140,255),(0,170,70),(200,120,0),(150,0,200),(0,150,150)]
    for r, idx in zip(regions, cloze_indices(regions)):
        c = palette[(idx - 1) % len(palette)]
        box = [r["left"]*W, r["top"]*H,
               (r["left"]+r["width"])*W, (r["top"]+r["height"])*H]
        d.rectangle(box, outline=c, width=4)
        d.text((box[0], max(0, box[1]-13)), f"c{idx}", fill=c)
    img.save(out_path)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--in", dest="inp")
    a.add_argument("--mode", default="one")
    a.add_argument("--keep", help="comma-separated group ids to keep (drop the rest)")
    a.add_argument("--preview", metavar="IMAGE",
                   help="also draw the kept regions onto IMAGE (the figure the rects were measured on)")
    a.add_argument("--preview-out", default="occlusion_preview.png",
                   help="where to write the preview (default %(default)s)")
    ns = a.parse_args()
    data = json.load(open(ns.inp) if ns.inp else sys.stdin)
    regs = data["regions"] if isinstance(data, dict) else data
    if ns.keep:
        keep = {int(x) for x in ns.keep.replace(" ", "").split(",") if x}
        regs = [r for r in regs if r.get("group") in keep]
    mode = data.get("mode", ns.mode) if isinstance(data, dict) else ns.mode
    if ns.preview:
        draw_preview(ns.preview, regs, ns.preview_out)
        print(f"preview -> {ns.preview_out}  (LOOK at it before writing the note)", file=sys.stderr)
    print(build(regs, mode))
