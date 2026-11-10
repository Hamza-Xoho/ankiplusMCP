#!/usr/bin/env python3
"""Render Anki cloze drafts as the student will see them, and lint them.

Renders through the note type's REAL template and CSS (saved from AnkiMCP
model_templates / model_styling), at phone width, cropped to content:
  - one FRONT per cloze number (the student must attempt every blank)
  - one BACK per note, with every cloze revealed (backs differ only by highlight)
Then tiles them into CONTACT SHEETS, so a reviewer opens a few images instead of
hundreds: sheets/sheet_NN_fronts.png and sheets/sheet_NN_backs.png cover the same
notes; open the fronts sheet, commit answers, then open the backs sheet.
Desktop renders only for a small sample (--desktop-sample). Scripts are stripped
(add-on snippets such as AMBOSS carry tokens). Also writes deterministic lint.

Usage:
  render_cards.py --drafts drafts.jsonl --model-dir model/ --out renders/ [--only n01,n02] [--per-sheet 8]
  render_cards.py --anki-html cards.jsonl --model-dir model/ --out renders/   # HTML from present_card

model/ holds front.html, back.html, style.css.
drafts.jsonl: {"id":..., "fields":{"Text":..., "Extra":...}, "tags":[...]}
cards.jsonl: {"id":..., "question":<html>, "answer":<html>}
Writes renders/cards/*.png, renders/sheets/*.png, renders/sheets.json (student's
reading order), renders/lint.json
"""
import argparse, html, json, re, sys
from pathlib import Path

CLOZE = re.compile(r"\{\{c(\d+)::(.*?)(?:::((?:(?!\}\}).)*?))?\}\}", re.S)
SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
STOP_U = {"and", "or", "both", "the", "a", "an", "of", "in", "to", "is", "are", "with", "all"}


def cloze_field(text, n, side):
    def sub(m):
        num, ans, hint = int(m.group(1)), m.group(2), m.group(3)
        if n is None:  # back with every cloze revealed
            return f'<span class="cloze" data-ordinal="{num}">{ans}</span>'
        if num != n:
            return f'<span class="cloze-inactive" data-ordinal="{num}">{ans}</span>'
        if side == "front":
            return f'<span class="cloze" data-ordinal="{n}">[{html.escape(hint) if hint else "..."}]</span>'
        return f'<span class="cloze" data-ordinal="{n}">{ans}</span>'
    return CLOZE.sub(sub, text)


def fill(template, fields, tags, n, side, front_html=""):
    t = SCRIPT.sub("", template)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    def section(m):
        neg, name, body = m.group(1) == "^", m.group(2).strip(), m.group(3)
        present = bool(re.sub(r"<[^>]+>|\s|&nbsp;", "", fields.get(name, "")))
        return body if present != neg else ""
    for _ in range(3):  # nested sections
        t = re.sub(r"\{\{([#^])([^}]+)\}\}(.*?)\{\{/\2\}\}", section, t, flags=re.S)
    def field(m):
        spec = m.group(1).strip()
        if spec == "FrontSide":
            return front_html
        if spec == "Tags":
            return " ".join(tags)
        parts = spec.split(":")
        name = parts[-1]
        if "cloze" in parts[:-1]:
            return cloze_field(fields.get(name, ""), n, side)
        if name == "Tags" or spec.endswith(":Tags"):
            return " ".join(tags)
        return fields.get(name, "")
    return re.sub(r"\{\{(.*?)\}\}", field, t)


def page(css, body, mobile, night):
    hcls = ("mobile iphone " if mobile else "") + ("night_mode" if night else "")
    bcls = "card card1" + (" nightMode night_mode" if night else "")
    return (f"<!doctype html><html class='{hcls}'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<style>{css}</style></head><body class='{bcls}'><div id='qa'>{SCRIPT.sub('', body)}</div></body></html>")


def lint(note):
    f = note["fields"]
    text, extra = f.get("Text", ""), f.get("Extra", f.get("Back Extra", ""))
    plain = lambda s: html.unescape(re.sub(r"<[^>]+>", "", CLOZE.sub(lambda m: m.group(2), s)))
    out = []
    def flag(code, msg): out.append({"id": note["id"], "code": code, "msg": msg})
    if re.search(r"\n", extra) and not re.search(r"<br\s*/?>|<div|<li", extra):
        flag("L1", "Extra uses raw newlines - HTML collapses them into one paragraph; use <br>")
    if plain(text).rstrip().endswith("."):
        flag("L2", "card text ends with a full stop")
    us = re.findall(r"<u>(.*?)</u>", text + extra, re.S)
    bad_u = [u for u in us if plain(u).strip().lower() in STOP_U]
    if bad_u:
        flag("L3", f"underline on filler words: {bad_u}")
    if len(us) > 3:
        flag("L4", f"{len(us)} underlines on one note - underline sparingly")
    body = re.sub(r'<div class="src">.*?</div>', "", extra, flags=re.S)
    lines = [l for l in re.split(r"<br\s*/?>|\n", body) if plain(l).strip()]
    if len(lines) > 3:
        flag("L5", f"Extra has {len(lines)} lines - keep it to the why, one contrast, the citation")
    if len(plain(body)) > 220:
        flag("L6", f"Extra is {len(plain(body))} chars - too long to scan after a rep")
    if extra.strip() and 'class="src"' not in extra:
        flag("L13", "citation is not in a <div class=\"src\"> block")
    for m in CLOZE.finditer(text):
        if m.group(3) and len(m.group(3)) > 22:
            flag("L14", f"hint '{m.group(3)}' is long - it will overflow a phone screen")
        if re.search(r"\(–|–[A-Z]", plain(m.group(2))) and "nw" not in m.group(2):
            flag("L15", f"formula in c{m.group(1)} not wrapped in <span class=\"nw\">")
    if len(plain(text)) > 200:
        flag("L7", f"card text is {len(plain(text))} chars - likely more than one relationship")
    if "&amp;amp;" in text + extra or re.search(r"&lt;/?[a-z]", text + extra):
        flag("L8", "escaped HTML will show as raw text")
    nums = {int(m.group(1)) for m in CLOZE.finditer(text)}
    if len(nums) > 5:
        flag("L9", f"{len(nums)} cloze numbers - over the cap unless a genuine enumeration")
    for m in CLOZE.finditer(text):
        if "," in plain(m.group(2)):
            flag("L10", f"comma inside c{m.group(1)} - list in a blank")
    bolds = re.findall(r"<b>", text)
    if len(bolds) > 4:
        flag("L11", f"{len(bolds)} bold runs in the text - bold the main subject only")
    for t in note.get("tags", []):
        if not t.startswith("#ColdRecall") and t.startswith(("#AK_", "#AnKing", "AK_")):
            flag("L12", f"tag '{t}' writes into AnKing's tag tree - use #ColdRecall::")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts"); ap.add_argument("--anki-html")
    ap.add_argument("--model-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma-separated note ids (round 2: only what changed)")
    ap.add_argument("--per-sheet", type=int, default=8, help="notes per contact sheet")
    ap.add_argument("--desktop-sample", type=int, default=3, help="notes also rendered at desktop width")
    ap.add_argument("--light", action="store_true", help="also render the sample with night mode off")
    a = ap.parse_args()
    md, out = Path(a.model_dir), Path(a.out)
    (out / "cards").mkdir(parents=True, exist_ok=True); (out / "sheets").mkdir(exist_ok=True)
    css = (md / "style.css").read_text()
    front_t, back_t = (md / "front.html").read_text(), (md / "back.html").read_text()
    only = set(a.only.split(",")) if a.only else None

    notes, lints = [], []   # [(id, [(label, html)] fronts, (label, html) back)]
    if a.drafts:
        for line in open(a.drafts):
            if not line.strip():
                continue
            note = json.loads(line)
            if only and note["id"] not in only:
                continue
            note.setdefault("fields", {"Text": note.get("text", ""), "Extra": note.get("extra", "")})
            lints += lint(note)
            f, tags = note["fields"], note.get("tags", [])
            nums = sorted({int(m.group(1)) for m in CLOZE.finditer(f.get("Text", ""))}) or [1]
            fronts = [(f"{note['id']}_c{n}", fill(front_t, f, tags, n, "front")) for n in nums]
            back = (f"{note['id']}", fill(back_t, f, tags, None, "back", fronts[0][1]))
            notes.append((note["id"], fronts, back))
    elif a.anki_html:
        for line in open(a.anki_html):
            if line.strip():
                c = json.loads(line)
                notes.append((str(c["id"]), [(f"{c['id']}", c["question"])], (f"{c['id']}", c["answer"])))
    else:
        sys.exit("give --drafts or --anki-html")

    from playwright.sync_api import sync_playwright
    def shot(b, html_body, path, width, mobile, night=True):
        pg = b.new_page(viewport={"width": width, "height": 40})
        pg.set_content(page(css, html_body, mobile, night))
        pg.screenshot(path=str(path), full_page=True); pg.close()

    rendered = []  # (id, [(label, front_png)], (label, back_png))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, (nid, fronts, back) in enumerate(notes):
            fp = []
            for label, h in fronts:
                path = out / "cards" / f"{label}_front.png"; shot(b, h, path, 390, True); fp.append((label, path))
            bp = out / "cards" / f"{back[0]}_back.png"; shot(b, back[1], bp, 390, True)
            if i < a.desktop_sample:
                shot(b, back[1], out / "cards" / f"{back[0]}_back_desktop.png", 1100, False)
                if a.light:
                    shot(b, back[1], out / "cards" / f"{back[0]}_back_light.png", 390, True, night=False)
            rendered.append((nid, fp, (back[0], bp)))
        b.close()

    sheets = make_sheets(rendered, out / "sheets", a.per_sheet)
    (out / "sheets.json").write_text(json.dumps(sheets, indent=1))
    (out / "lint.json").write_text(json.dumps(lints, indent=1))
    nf = sum(len(r[1]) for r in rendered)
    print(f"{len(rendered)} notes, {nf} fronts -> {len(sheets)} sheet pairs in {out}/sheets.json; "
          f"{len(lints)} lint findings -> {out}/lint.json")
    for l in lints:
        print(f"  {l['id']} {l['code']}: {l['msg']}")


def make_sheets(rendered, outdir, per_sheet, tile_w=300, cols=4, max_h=2400):
    """Tile cards into labelled sheets. Fronts and backs of the same notes share a sheet number."""
    from PIL import Image, ImageChops, ImageDraw
    def tile(items, path):
        tiles = []
        for label, png in items:
            im = Image.open(png).convert("RGB")
            bg = Image.new("RGB", im.size, im.getpixel((2, im.height - 2)))
            box = ImageChops.difference(im, bg).getbbox()
            if box:  # trim the empty card padding below the content
                im = im.crop((0, 0, im.width, min(im.height, box[3] + 16)))
            im = im.resize((tile_w, max(1, int(im.height * tile_w / im.width))))
            cap = Image.new("RGB", (tile_w, im.height + 22), (20, 22, 26))
            cap.paste(im, (0, 22)); ImageDraw.Draw(cap).text((6, 5), label, fill=(240, 200, 90))
            tiles.append(cap)
        rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
        H = sum(max(t.height for t in r) + 8 for r in rows) + 8
        sheet = Image.new("RGB", (cols * (tile_w + 8) + 8, min(H, 10000)), (10, 10, 12))
        y = 8
        for r in rows:
            x = 8
            for t in r:
                sheet.paste(t, (x, y)); x += tile_w + 8
            y += max(t.height for t in r) + 8
        sheet.save(path)
        return str(path)
    out, n = [], 0
    for i in range(0, len(rendered), per_sheet):
        n += 1
        chunk = rendered[i:i + per_sheet]
        f = tile([x for r in chunk for x in r[1]], outdir / f"sheet_{n:02d}_fronts.png")
        bk = tile([r[2] for r in chunk], outdir / f"sheet_{n:02d}_backs.png")
        out.append({"fronts": f, "backs": bk, "notes": [r[0] for r in chunk]})
    return out


if __name__ == "__main__":
    main()
