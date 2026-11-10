#!/usr/bin/env python3
"""
extract_figures.py — pull figures out of a lecture PDF at OCR-grade resolution.

Usage:
    python3 extract_figures.py LECTURE.pdf --pages 7,10 --out ./figures
    python3 extract_figures.py LECTURE.pdf --all --out ./figures
    python3 extract_figures.py LECTURE.pdf --pages 7 --whole-page --out ./figures

--whole-page renders the entire page instead of its embedded images. Use it when
a diagram is drawn as vector shapes (no embedded image, so nothing is found) or
when the slide is a scan. Crop is then the whole slide; drop the title/footer
regions with build_occlusion.py --keep.

WHY NOT JUST EXPORT THE EMBEDDED IMAGE:
The embedded raster in a slide deck is often small (300x361 in a measured case).
OCR on that fails. Re-rendering the image's placement rectangle at 4x gives
~1800px wide, which is what makes label detection work.

Requires: pymupdf  (pip install pymupdf)
"""
import argparse, os, sys


def figures(pdf_path, pages=None, out_dir=".", zoom=4, min_frac=0.05, whole_page=False):
    import pymupdf
    doc = pymupdf.open(pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    written = []
    idxs = range(len(doc)) if pages is None else [p - 1 for p in pages]
    for i in idxs:
        if i < 0 or i >= len(doc):
            print(f"  ! page {i+1} out of range", file=sys.stderr)
            continue
        page = doc[i]
        if whole_page:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            path = os.path.join(out_dir, f"p{i+1:02d}_page.png")
            pix.save(path)
            written.append((path, pix.width, pix.height))
            print(f"  {path}  {pix.width}x{pix.height}  (whole page)")
            continue
        parea = abs(page.rect.get_area()) or 1
        rects = []
        for im in page.get_images(full=True):
            for r in page.get_image_rects(im[0]):
                if abs(r.get_area()) / parea >= min_frac:
                    rects.append(r)
        # keep the largest few, biggest first; skip tiny logos
        rects.sort(key=lambda r: -abs(r.get_area()))
        if not rects:
            print(f"  ! page {i+1}: no embedded image big enough. If it has a diagram, "
                  f"it is probably vector-drawn - re-run with --whole-page", file=sys.stderr)
        for n, r in enumerate(rects, 1):
            pix = page.get_pixmap(clip=r, matrix=pymupdf.Matrix(zoom, zoom))
            name = f"p{i+1:02d}_fig{n}.png"
            path = os.path.join(out_dir, name)
            pix.save(path)
            written.append((path, pix.width, pix.height))
            print(f"  {path}  {pix.width}x{pix.height}")
    return written


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("pdf")
    a.add_argument("--pages", help="comma-separated 1-based page numbers")
    a.add_argument("--all", action="store_true")
    a.add_argument("--out", default="./figures")
    a.add_argument("--zoom", type=float, default=4)
    a.add_argument("--min-frac", type=float, default=0.05,
                   help="ignore images smaller than this fraction of the page (logos)")
    a.add_argument("--whole-page", action="store_true",
                   help="render whole pages (vector diagrams, scanned slides)")
    ns = a.parse_args()
    pages = None
    if ns.pages:
        pages = [int(x) for x in ns.pages.replace(" ", "").split(",") if x]
    elif not ns.all:
        a.error("give --pages 7,10 or --all")
    out = figures(ns.pdf, pages, ns.out, ns.zoom, ns.min_frac, ns.whole_page)
    print(f"\n{len(out)} figure(s) -> {ns.out}")
    print("Next: python3 ocr_regions.py <figure.png> --json r.json --preview p.png")
