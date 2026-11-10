# Image Occlusion — verified reference

Confirmed against a real note in a live collection and a working end-to-end
test. **No add-on is required**: Anki's native Image Occlusion note type stores
masks as *text*, so notes can be written directly through `add_notes`.

---

## Where the scripts run — decide this first

The scripts need Python. The finished image has to end up **on the computer
running Anki**, because `store_media_file` reads a local path there. That gives
three situations:

| You are running in… | Scripts run | How the image reaches Anki |
|---|---|---|
| **Claude Code** (Code tab or terminal) on the same computer as Anki | Locally | `store_media_file(path="/absolute/path/fig.png")` |
| **Claude app chat** with a workspace, and the user's computer linked (a folder attached with **+ → Add folder**) | In the workspace | Write the PNG back into an attached folder on the computer, then `store_media_file(path=<that absolute local path>)` |
| **Claude app chat** with no way to put a file on the user's computer | — | Don't occlude. List the figures worth occluding (slide, labels, why) so the user can make them in Anki: **Add → note type Image Occlusion** takes about a minute per figure |

Never pass a multi-megabyte image as base64 `data` to `store_media_file` — it
goes through the conversation and wastes most of the context window.

**Dependencies.** `python3 -m pip install --user pymupdf pillow numpy pytesseract`
plus the `tesseract` program (macOS `brew install tesseract`; Windows: the UB
Mannheim installer; Linux `apt install tesseract-ocr`). Check with
`python3 -c "import pymupdf, PIL, numpy"` and `tesseract --version`.

**No tesseract?** Everything except OCR still works. Look at the figure, write
the rects by hand (fractions of the image, see below), and check them with
`build_occlusion.py --preview`. Tag those notes `#ColdRecall::!Flags::IO_estimated`.
Don't install system software on the user's machine without asking.

---

## Procedure

Script paths are relative to this skill's folder (`scripts/`).

```bash
# 1. Enumerate figures first (see SKILL.md) — then pull the chosen ones at 4x
python3 scripts/extract_figures.py LECTURE.pdf --pages 7,10 --out ./figs
#    vector-drawn diagram or scanned slide? add --whole-page

# 2. OCR the labels to fractional rects, with a visual preview
python3 scripts/ocr_regions.py figs/p10_fig1.png --json r.json --preview p.png

# 3. LOOK at p.png next to the figure. Add missing labels, note junk groups.

# 4. Build the Occlusion field from the groups worth testing, and look again
python3 scripts/build_occlusion.py --in r.json --keep 1,2,3 \
        --preview figs/p10_fig1.png --preview-out kept.png
```

Then through the Anki connector:

```
store_media_file(filename="med241-l003-p10-organelles.png", path="/abs/path/figs/p10_fig1.png")
add_notes(deck_name="MED241::3. Cell organelles",
          model_name="Image Occlusion",
          notes=[{"fields": {"Occlusion": "<string from build_occlusion.py>",
                             "Image": "<img src=\"med241-l003-p10-organelles.png\">",
                             "Header": "Organelles of a typical animal cell (slide 10)",
                             "Back Extra": "", "Comments": ""},
                  "tags": ["#ColdRecall::#Source::MED241::L003_Cell_organelles",
                           "#ColdRecall::!Tier::2"]}])
```

Name media files after the source and slide so they never collide across
lectures.

---

## Field syntax (verified)

Note type `Image Occlusion`, fields: `Occlusion`, `Image`, `Header`, `Back Extra`, `Comments`.

```
Occlusion: {{c1::image-occlusion:rect:left=.2755:top=.077:width=.2783:height=.069:oi=1}}<br>
           {{c2::image-occlusion:rect:left=.626:top=.1436:width=.2736:height=.0702:oi=1}}<br>
Image:     <img src="paste-1ebf66d62ce15e0f377f5e7fcb5735fc299eb123.jpg">
Header:    Lateral view of the brain
```

- **Coordinates are fractions of image dimensions (0–1), not pixels.** They
  survive resizing, so the stored image can be a different resolution from the
  one OCR measured, as long as it is the same crop.
- Anki writes leading-dot decimals (`.2755`). `build_occlusion.py` matches this.
- Shapes joined with `<br>`; the field ends with a trailing `<br>`.
- Each `c<n>` generates **one card**. `c1`..`cN` → N cards from one note.
- `oi=1` = hide-one-at-a-time (one region hidden per card, rest visible).
  `oi=0` = hide-all-guess-one.
- `rect` is right for nearly all label occlusion. `ellipse` and `polygon` exist.
- `Header` names the figure and slide; `Back Extra` takes the one-line context
  (what the figure is for), exactly as on a cloze.

---

## OCR reliability — measured, and how it was fixed

The naive approach (feed the embedded image to Tesseract at psm 12) found
**2 of 15 labels** on a real anatomy figure. That is not a usable tool. Two
changes fixed it, both built into `ocr_regions.py`.

### 1. Resolution — re-render, never export

Slide figures embed small. The measured case was 300×361 for the planes figure
and 409×372 for the directional-terms figure. Re-rendering the image's
*placement rectangle* at 4× gives 1350×1429 and 1802×1501. `extract_figures.py`
does this. Exporting the embedded raster and OCRing it is a wasted step.

### 2. Binarisation — the single biggest lever

Anti-aliased dark text on a light background defeats Tesseract. Hard-threshold
it and the same engine reads it. Measured on the 15-label figure at 1802×1501,
counting distinct target labels found:

| Preprocessing | psm 6 | psm 11 | psm 12 | psm 4 |
|---|---|---|---|---|
| none (raw) | 6 | 5 | **2** | 0 |
| threshold < 100 | 10 | 11 | 11 | 10 |
| threshold < 128 | 12 | 12 | 12 | 12 |
| threshold < 128 + 2× upscale | **13** | **13** | **13** | **13** |

Raw + psm 12 — the obvious default — is the worst cell in the table, and once
the image is binarised the psm mode barely matters: preprocessing dominates.
The script still sweeps psm 11/6/12/4 and keeps the best.

### 3. Repeated labels must share a cloze index

The same figure carries "Proximal" three times and "Distal" three times.
Occluding one instance leaves the other two visible — the card displays its own
answer. `ocr_regions.py` groups instances by normalised text and assigns one
`group` (cloze index) per distinct label. On that figure: 17 regions → 13 cards.

### 4. Multi-line labels must be merged before grouping

Grouping by matching text is right when the same *complete* label repeats. It is
wrong when a word appears inside two different multi-line labels: "SMOOTH /
ENDOPLASMIC / RETICULUM" and "ROUGH / ENDOPLASMIC / RETICULUM" would otherwise
leave two bare `ENDOPLASMIC` regions that text-matching fuses into ONE cloze —
hiding a word inside two unrelated organelle names at once.
`merge_stacked_lines()` merges stacked lines of one label first, judging gap
and size against the block's *first-line* height (judged against the
accumulated height, the third line of a 3-line label looks half-sized and is
left behind as an orphan that collides).

### 5. What still needs a human

The scripts find text. They do not know what is worth testing.

- Titles and captions get detected — "Body Planes" is a title, not a label. Drop it.
- Source URLs and credits are filtered by position and content, but new shapes
  of junk appear.
- A genuine label came back at **confidence 25** ("Right"). The filter keeps
  anything 4+ letters regardless of confidence and reports it under
  `low_confidence`, because silently dropping a real label is worse.
- Labels OCR misses entirely need estimating by hand, tagged `IO_estimated`.

### 6. Some figures are not worth OCR at all

Stylised outline fonts, watermarks and dense sub-labelling defeat detection. A
real organelle diagram produced 39 regions of which a third were artifacts.
When the junk ratio is that high, hand-place rects for the labels that serve an
objective — ten organelle names beat twenty-nine watermark fragments.

---

## Non-text targets

OCR only finds text. When the thing worth hiding is a structure with no label,
estimate the rect by looking at the image, tag the note `IO_estimated`, and
render the preview — never write estimated rects blind.

## What not to occlude

Titles, slide footers, page numbers, institution names, figure credits,
copyright lines, axis units that are not the tested content. Occluding these
produces cards that test nothing.
