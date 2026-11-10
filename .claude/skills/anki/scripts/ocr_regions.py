#!/usr/bin/env python3
"""
ocr_regions.py (v2) — find text-label regions in a figure and emit fractional
rects for Anki's native Image Occlusion `Occlusion` field.

Usage:
    python3 ocr_regions.py IMAGE [--json out.json] [--preview out.png]
                                 [--conf 20] [--min-len 2] [--no-group]

Emits JSON: {"width","height","regions":[{text,conf,left,top,width,height,group}],
             "repeated","low_confidence","note"}

WHY THIS PREPROCESSES (measured, not guessed):
Slide figures use anti-aliased dark text on light backgrounds. Feeding that to
Tesseract raw fails badly. On a real 15-label anatomy figure at 1802x1501:

    raw image,      psm 12  ->  2/15 labels   (the naive approach)
    raw image,      psm  6  ->  6/15
    threshold<128,  psm 11  -> 12/15
    threshold<128 + 2x,     -> 13/15  <- all unique labels present

So: binarise at 128, upscale 2x, and try several psm modes, keeping the best.
Threshold is the single highest-leverage step; psm choice matters less once
the image is binarised.

REPEATED LABELS:
A label appearing N times (e.g. "Proximal" three times on one figure) must have
ALL its instances share one cloze index, or the card shows the answer elsewhere
on the image. Instances are grouped by normalised text automatically.
"""
import argparse, json, sys
from collections import defaultdict

PSM_MODES = [11, 6, 12, 4]


def _binarise(img, threshold=128, scale=2):
    import numpy as np
    from PIL import Image
    g = img.convert("L")
    a = np.array(g)
    b = Image.fromarray(np.where(a < threshold, 0, 255).astype("uint8"))
    if scale != 1:
        b = b.resize((b.width * scale, b.height * scale), Image.LANCZOS)
    return b


def _words(im, psm, min_conf, min_len):
    import pytesseract
    d = pytesseract.image_to_data(im, config=f"--psm {psm}",
                                  output_type=pytesseract.Output.DICT)
    out = []
    for i, txt in enumerate(d["text"]):
        t = txt.strip()
        if not t or len(t) < min_len:
            continue
        try:
            conf = float(d["conf"][i])
        except (ValueError, TypeError):
            continue
        if conf < min_conf:
            continue
        out.append({"text": t, "conf": conf,
                    "left": d["left"][i], "top": d["top"][i],
                    "width": d["width"][i], "height": d["height"][i],
                    "line_id": (d["block_num"][i], d["par_num"][i], d["line_num"][i])})
    return out


def merge_line_words(words, gap_ratio=1.2):
    """Tesseract returns ONE BOX PER WORD: 'Frontal lobe' arrives as two boxes.
    Occluding them separately asks the learner to recall the word 'lobe'."""
    out, lines = [], defaultdict(list)
    for w in words:
        lines[w["line_id"]].append(w)
    for ws in lines.values():
        ws.sort(key=lambda w: w["left"])
        cur = None
        for w in ws:
            if cur is None:
                cur = dict(w); continue
            gap = w["left"] - (cur["left"] + cur["width"])
            if gap <= gap_ratio * max(cur["height"], w["height"]):
                right = max(cur["left"] + cur["width"], w["left"] + w["width"])
                bottom = max(cur["top"] + cur["height"], w["top"] + w["height"])
                cur["top"] = min(cur["top"], w["top"])
                cur["left"] = min(cur["left"], w["left"])
                cur["width"] = right - cur["left"]
                cur["height"] = bottom - cur["top"]
                cur["text"] += " " + w["text"]
                cur["conf"] = min(cur["conf"], w["conf"])
            else:
                out.append(cur); cur = dict(w)
        if cur is not None:
            out.append(cur)
    return out


def merge_stacked_lines(regions, gap_ratio=0.8, overlap_frac=0.45):
    """Merge vertically stacked lines of ONE multi-line label into a single region.

    Must run BEFORE grouping. Without it, a word shared by two different
    multi-line labels collides: "SMOOTH / ENDOPLASMIC / RETICULUM" and
    "ROUGH / ENDOPLASMIC / RETICULUM" both yield a bare "ENDOPLASMIC", which
    text-matching then merges into one cloze index - hiding a word in two
    unrelated labels at once.

    Gap and size are judged against the block's FIRST-LINE height (_lh), not its
    accumulated height. Measured against the accumulated height, the third line
    of a 3-line label looks half-sized and fails the test, leaving an orphan
    ("RETICULUM") that then collides in exactly the way this function exists to
    prevent.
    """
    regs = sorted(regions, key=lambda r: (r["top"], r["left"]))
    out = []
    for r in regs:
        placed = False
        for m in out:
            l1, r1 = m["left"], m["left"] + m["width"]
            l2, r2 = r["left"], r["left"] + r["width"]
            inter = min(r1, r2) - max(l1, l2)
            narrow = min(m["width"], r["width"]) or 1e-9
            lh = m["_lh"] or 1e-9
            vgap = r["top"] - (m["top"] + m["height"])
            same_size = 0.5 <= (r["height"] / lh) <= 2.0
            if (inter / narrow >= overlap_frac
                    and -0.25 * lh <= vgap <= gap_ratio * lh
                    and same_size):
                bottom = max(m["top"] + m["height"], r["top"] + r["height"])
                right = max(r1, r2)
                m["left"] = min(l1, l2)
                m["top"] = min(m["top"], r["top"])
                m["width"] = right - m["left"]
                m["height"] = bottom - m["top"]
                m["text"] = m["text"] + " " + r["text"]
                m["conf"] = min(m["conf"], r["conf"])
                placed = True
                break
        if not placed:
            n = dict(r)
            n["_lh"] = r["height"]          # this block's single-line height
            out.append(n)
    for m in out:
        m.pop("_lh", None)
    return out


def _norm(t):
    return t.lower().strip(" .,:;()")


# Junk OCR routinely invents from arrowheads, rules and citation lines.
_JUNK_EXACT = {"vv", "ww", "ay", "pr", "en", "ee", "te", "ae", "wide", "nam"}


def _is_junk(text, region_top):
    """Reject arrowhead artifacts, source URLs and figure credits."""
    t = text.strip()
    low = t.lower()
    if _norm(t) in _JUNK_EXACT:
        return True
    # URLs / citation lines, usually along the bottom edge
    if any(m in low for m in ("http", "www.", ".com", ".org", "/units", "://")):
        return True
    if region_top > 0.93 and (len(t) > 14 or "/" in t):
        return True
    # mostly non-alphabetic => not a label
    alpha = sum(c.isalpha() for c in t)
    if alpha < max(2, len(t) * 0.5):
        return True
    # repeated single character ("VVV", "III")
    if len(set(low.replace(" ", ""))) == 1:
        return True
    return False


def _looks_like_label(r):
    """Real figure labels are words, not fragments.

    Measured on two real slide figures: genuine labels came back at confidence
    85-96, while arrowhead/line artifacts came back as 2-3 character fragments
    at confidence 20-66. Short low-confidence fragments are therefore dropped;
    anything >=4 chars is kept for the human to judge from the preview.
    """
    t = r["text"].strip()
    alpha = "".join(c for c in t if c.isalpha())
    # Fragments: 1-3 letters are artifacts unless OCR is very sure.
    if len(alpha) <= 3 and r["conf"] < 75:
        return False
    # A 4+ letter run is word-shaped; keep it even at low confidence and let the
    # preview decide. ('Right' came back at conf 25 on a real figure and is a
    # genuine label - dropping it silently is the failure mode that matters.)
    return len(alpha) >= 4


def extract(path, min_conf=20, min_len=2, pad=0.004, group=True):
    from PIL import Image
    img = Image.open(path)
    W, H = img.size
    binim = _binarise(img)
    SW, SH = binim.size

    best, best_score = [], -1
    for psm in PSM_MODES:
        ws = _words(binim, psm, min_conf, min_len)
        merged = merge_line_words(ws)
        # score: prefer more distinct alphabetic labels, then higher mean conf
        alpha = [m for m in merged if any(c.isalpha() for c in m["text"])]
        score = (len(alpha), sum(m["conf"] for m in alpha) / max(len(alpha), 1))
        if score > (best_score if isinstance(best_score, tuple) else (-1, 0)):
            best_score, best, best_psm = score, alpha, psm

    regions = []
    for m in best:
        if _is_junk(m["text"], m["top"] / SH):
            continue
        regions.append({
            "text": m["text"],
            "conf": round(m["conf"], 1),
            "left":   round(max(0.0, m["left"] / SW - pad), 4),
            "top":    round(max(0.0, m["top"] / SH - pad), 4),
            "width":  round(min(1.0, m["width"] / SW + 2 * pad), 4),
            "height": round(min(1.0, m["height"] / SH + 2 * pad), 4),
        })
    regions = [r for r in regions if _looks_like_label(r)]
    regions = merge_stacked_lines(regions)
    regions.sort(key=lambda r: (r["top"], r["left"]))

    # group repeated labels so every instance shares one cloze index
    repeated = {}
    if group:
        by_text = defaultdict(list)
        for r in regions:
            by_text[_norm(r["text"])].append(r)
        gid = 0
        for r in regions:
            r["_key"] = _norm(r["text"])
        seen = {}
        for r in regions:
            k = r["_key"]
            if k not in seen:
                gid += 1; seen[k] = gid
            r["group"] = seen[k]
            r.pop("_key")
        repeated = {k: len(v) for k, v in by_text.items() if len(v) > 1}
    else:
        for i, r in enumerate(regions, 1):
            r["group"] = i

    low = [r["text"] for r in regions if r["conf"] < 50]
    return {
        "width": W, "height": H,
        "psm_used": best_psm,
        "regions": regions,
        "repeated": repeated,
        "low_confidence": low,
        "note": ("OCR assists with coordinates; it does not decide what exists. "
                 "ALWAYS open the preview and compare against the figure before "
                 "authoring. Add any label OCR missed by estimating its rect."),
    }


def preview(path, result, out):
    from PIL import Image, ImageDraw
    img = Image.open(path).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    palette = [(220,30,30),(0,140,255),(0,170,70),(200,120,0),(150,0,200),(0,150,150)]
    for r in result["regions"]:
        c = palette[(r["group"] - 1) % len(palette)]
        box = [r["left"]*W, r["top"]*H,
               (r["left"]+r["width"])*W, (r["top"]+r["height"])*H]
        d.rectangle(box, outline=c, width=4)
        d.text((box[0], max(0, box[1]-13)), f"c{r['group']}", fill=c)
    img.save(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("--conf", type=float, default=20)
    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--json")
    p.add_argument("--preview", dest="prev")
    p.add_argument("--no-group", action="store_true")
    a = p.parse_args()
    try:
        res = extract(a.image, a.conf, a.min_len, group=not a.no_group)
    except ImportError as e:
        sys.exit(f"missing Python package ({e.name}). Install with:\n"
                 f"  python3 -m pip install --user pytesseract pillow numpy\n"
                 f"No OCR at all? Estimate the rects by eye and check them with "
                 f"build_occlusion.py --preview.")
    except Exception as e:
        if type(e).__name__ != "TesseractNotFoundError":
            raise
        sys.exit("the tesseract OCR program is not installed "
                 "(macOS: brew install tesseract; Windows: the UB Mannheim installer; "
                 "Linux: apt install tesseract-ocr).\n"
                 "No OCR at all? Estimate the rects by eye and check them with "
                 "build_occlusion.py --preview.")
    if a.prev:
        preview(a.image, res, a.prev)
    txt = json.dumps(res, indent=2)
    if a.json:
        open(a.json, "w").write(txt)
        n = len({r["group"] for r in res["regions"]})
        print(f"{len(res['regions'])} regions -> {n} cards (psm {res['psm_used']}) -> {a.json}")
        if res["repeated"]:
            print("grouped repeats:", ", ".join(f"{k}x{v}" for k, v in res["repeated"].items()))
        if res["low_confidence"]:
            print("low confidence (verify):", ", ".join(res["low_confidence"]))
        print("REMINDER: open the preview and compare against the figure.")
    else:
        print(txt)
