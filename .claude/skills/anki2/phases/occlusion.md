# P2: image occlusion

Use only for figures selected by objective coverage. Never Read the PDF.

1. Read the exact `fig_id` from that slide in `source/slides.json`, or from
   `cards figures --build <build> --summary`. Never guess its spelling. Then run
   `.venv/bin/cards source --build <build> --figure <fig_id>`.
   Read the named extracted figure PNG before choosing masks. For a map-flagged
   slide use `source --build <build> --page-image N` and Read only its PNG.
2. Inspect OCR labels and groups returned for the figure. Exclude titles,
   credits, footers, page numbers, watermarks and unrelated labels. Merge stacked
   words of one label; repeated complete labels share a group/cloze index so no
   copy gives away the answer. Do not merge shared words of different labels.
3. Use `.venv/bin/cards figures --build <build> --fig <fig_id> --keep 1,2,3 --mode one`
   with actual relevant group ids. `--mode all` hides all while testing one.
   If OCR misses labels or the target is unlabelled, write a regions file inside
   the build and pass its **build-relative** path with `--regions regions.json`.
   Its array uses `left`, `top`, `width`, `height` fractions in [0,1], plus `text`
   and positive integer `group`. Rectangles must lie within the same image crop.
4. Read the generated preview PNG: every tested label must be covered, no answer
   leaks, no irrelevant boxes. Never estimate unseen masks. Mark estimated notes
   `#ColdRecall::!Flags::IO_estimated`. If the preview is wrong, stop before review
   and resolve the figure input in one deliberate batch; do not overwrite an
   existing generated draft or remove a conflict refusal to force regeneration.

`cards figures` appends the native Image Occlusion note to drafts, with its image,
preview and masks. It initially uses tier 1 and null objective: if different
metadata is needed, prepare it in a single batched drafting operation before P3;
keep all generated fields/media and stable ids. No note-by-note Edits.

Native fields are `Occlusion`, `Image`, `Header`, `Back Extra`, `Comments`.
Each `cN` mask group creates one card; coordinates are fractions, not pixels.
Use source/slide-specific media filenames; the generated media list maps the
build-relative image to the Anki filename. Store media by local absolute path at
P6 on the machine running Anki, never by putting base64 into the conversation.
If that machine cannot access the image, stop and report; do not change transport.
