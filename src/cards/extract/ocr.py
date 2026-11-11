"""Measured v1 OCR: threshold 128, upscale 2x, four PSM modes."""
from collections import defaultdict

PSM_MODES = [11, 6, 12, 4]
CACHE_LIMIT = 2000


def _binarise(img, threshold=128, scale=2):
    from PIL import Image
    # A PIL lookup table yields exactly the v1 binary pixels without allocating
    # numpy's intermediate int64 array for every OCR-grade image.
    b = img.convert("L").point(lambda value: 0 if value < threshold else 255)
    if scale != 1:
        b = b.resize((b.width * scale, b.height * scale), Image.LANCZOS)
    return b


binarise = _binarise


def _words(im, psm, min_conf, min_len, encoded=None):
    import csv
    import io
    import os
    import subprocess
    if encoded is None:
        buffer = io.BytesIO()
        im.save(buffer, format='TIFF', compression='raw')
        encoded = buffer.getvalue()
    try:
        process = subprocess.run(
            ['tesseract', 'stdin', 'stdout', '--psm', str(psm), 'tsv'],
            input=encoded, capture_output=True, timeout=30,
            env={**os.environ, 'OMP_THREAD_LIMIT': '1'}, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        from ..common.errors import CardsError
        raise CardsError('E24', 'OCR: field tesseract unavailable or failed',
                         'install Tesseract with English data and retry extraction') from exc
    rows = list(csv.DictReader(io.StringIO(process.stdout.decode()), delimiter='\t'))
    d = {key: [row[key] for row in rows] for key in
         ('text','conf','left','top','width','height','block_num','par_num','line_num')}
    for key in ('left','top','width','height'):
        d[key] = [int(x) for x in d[key]]
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

    import io
    buffer = io.BytesIO()
    binim.save(buffer, format="TIFF", compression="raw")
    encoded = buffer.getvalue()
    best, best_score = [], -1
    for psm in PSM_MODES:
        ws = _words(binim, psm, min_conf, min_len, encoded)
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



words = _words

_VERSION = []


def tesseract_version():
    """First line of `tesseract --version`, cached for the process; 'unknown' if it cannot run."""
    if not _VERSION:
        import subprocess
        try:
            run = subprocess.run(['tesseract', '--version'], capture_output=True, timeout=30, check=True)
            text = (run.stdout or run.stderr).decode(errors='replace').strip()
            _VERSION.append(text.splitlines()[0] if text else 'unknown')
        except (OSError, subprocess.SubprocessError):
            _VERSION.append('unknown')
    return _VERSION[0]


def _cache_key():
    import hashlib
    return hashlib.sha256(repr((tesseract_version(), PSM_MODES, 20, 2, 0.004, True)).encode()).hexdigest()[:16]


def cached_extract(path, cache_dir):
    """`extract(path)`, remembered in `cache_dir` by image content and OCR settings."""
    if cache_dir is None:
        return extract(path)
    import hashlib
    import json
    from pathlib import Path
    from ..common.files import atomic_write
    cache_dir = Path(cache_dir)
    entry = cache_dir / f'{hashlib.sha256(Path(path).read_bytes()).hexdigest()}.{_cache_key()}.json'
    try:
        cached = json.loads(entry.read_text(encoding='utf-8'))
        if isinstance(cached, dict) and 'regions' in cached and 'repeated' in cached:
            return cached
    except (OSError, ValueError):
        pass
    result = extract(path)
    try:
        atomic_write(entry, json.dumps(result, ensure_ascii=False))
        stale = []
        for other in cache_dir.glob('*.json'):
            try:
                stale.append((other.stat().st_mtime, other.name, other))
            except OSError:
                pass
        stale.sort()
        for _, _, other in stale[:max(0, len(stale) - CACHE_LIMIT)]:
            if other != entry:
                other.unlink(missing_ok=True)
    except OSError:
        pass
    return result
