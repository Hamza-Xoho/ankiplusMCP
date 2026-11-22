---
id: PROJ-anki-v2-trd
title: /anki v2 — Technical Requirements for scripts
type: trd
status: draft
version: 0.2.0
owner: project owner
created: 2026-11-04
updated: 2026-11-05
related:
  brief: ./anki-v2-brief.md
---

# /anki v2: Technical Requirements (scripts)

This document says **what each script must do, take, produce and guarantee**, and when the skill calls it. It deliberately does not choose languages, libraries or internal structure; those are the builder's calls (brief §9). Where a current script already does part of the job, it is named, and the builder may reuse it.

Every requirement traces to the brief (`FR-`, `SC-`, `CON-`). Tools are numbered `T-n`, data contracts `D-n`, global rules `G-n`.

**v0.2 (2026-11-05).** Language is Python (brief ADR-13). All tools are subcommands of one `cards` command:

| Tool | Command |
|---|---|
| T-1 | `cards state` |
| T-2 | `cards target` |
| T-3 | `cards extract` |
| T-4 | `cards source` |
| T-5 | `cards check` |
| T-6 | `cards render` |
| T-7 | `cards packets` |
| T-8 | `cards apply` |
| T-9 | `cards gate` |
| T-10 | `cards write` |
| T-11 | `cards figures` |
| T-12 | `cards report` |
| T-13 | `cards meter` |

Other v0.2 changes:
- Decks are flat and named after the slides (ADR-8).
- The gate is automatic (ADR-9).
- The cost meter judges waste checks W-1 to W-8 instead of cost targets (ADR-10).
- The runtime guards and reviewer agents are specified in C-6 and C-7.

---

## G. Global requirements (apply to every tool)

| ID | Requirement |
|---|---|
| G-1 | **Standalone command.** Each tool runs from the command line with file paths and flags only. No interactive prompts. No hidden dependency on the current directory beyond an explicit `--build <dir>`. |
| G-2 | **Wrappable later.** Each tool's logic is callable as a function of (input paths, options) → (output files, summary), so a stage-2 MCP server can expose it unchanged (brief ADR-4). |
| G-3 | **Stdout contract (token budget).** Line 1 is a status word: `OK`, `FINDINGS` or `ERROR`. Then a summary of ≤ ~40 lines or ~2k characters, then the paths of files written. Everything else goes to files. A `--verbose` flag may exist for humans; the skill never uses it. (NFR-1) |
| G-4 | **Exit codes.** 0 = ok · 1 = findings (actionable, not a crash) · 2 = error (one line: cause + remedy) · 3 = precondition missing (e.g. an earlier phase hasn't run). (NFR-3) |
| G-5 | **Deterministic and idempotent.** Same inputs give identical outputs. Ids and ordering are stable. Re-running never duplicates or corrupts. (NFR-2) |
| G-6 | **Local and contained.** No network calls (CON-1). Source files are read-only (CON-4). Writes happen only inside the build folder or a declared cache folder. |
| G-7 | **Provenance.** Every generated file records the generator name, version and creation time (a header line for text files, fields for JSON). |
| G-8 | **Precise failures.** Schema or input errors name the file, the line or record, and the field. |
| G-9 | **Text safety.** UTF-8 throughout. Preserves HTML inside card fields byte-for-byte. Handles Greek letters, sub/superscripts and paths with spaces (the Google Drive path has spaces). |
| G-10 | **Self-describing.** `--help` in ≤ 20 lines. Each tool has at least one fixture test (§F). |
| G-11 | **Speed.** Interactive tools finish in < 10 s. Extraction and rendering finish in < 60 s for a 60-slide lecture or 60 notes on the owner’s Mac. (NFR-4) |

---

## D. Build folder and data contracts

```
builds/<YYYY-MM-DD>_<lecture-id>/
  build.json                 D-1  phase state (resume point)
  target.json                D-2  deck, tags, note type
  source/
    slides.json              D-3  per-slide text, figures, flags
    map.md                   D-4  one line per slide
    objectives.json          D-5  learning objectives
    figures/                 extracted figure images (+ OCR previews)
    pages/                   low-res page renders, created on demand only
  drafts.jsonl               D-6  the notes (also the inventory)
  skipped.jsonl              D-7  deliberately not carded
  checks/check.json          D-8  validation, lint, coverage, stats
  model/                     note type template + CSS snapshot (for rendering)
  renders/                   contact sheets + sheets.json (existing format)
  review/round<k>/
    maintainer/              D-9  packet
    student/                 D-9  packet
    maintainer_report.jsonl  D-10
    student_report.jsonl     D-10
    apply_log.json           D-11
  gate.json                  D-12
  write/                     D-13 batches, suspend list, import fallback, expected counts
  report.md                  D-14
```

**D-1 `build.json` (state).**
- **Identity:** build id, job (`build|harvest|repair`), source path, source hash.
- **Phase:** current phase (`P0`–`P7`), and phase history entries of {phase, status, started_at, ended_at}. The timestamps let the cost meter split usage by phase.
- **Preflight facts:** `anki_reachable`, `deck_exists`, `note_type_exists`, `existing_note_count`, `deck_decision`.
- **Review:** round number, and each reviewer's verdict.
- **Gate:** status `pending|passed|failed`, `drafts_hash`, `checked_at` (automatic, ADR-9).
- **Write results:** created, updated, suspended, errors.
- **Tool versions used.**

**D-2 `target.json`.** Deck name, deck depth, source tag, subject and system tags, tier tag templates, note type, legacy tag names to reconcile, and lecture id / number / title. The `confident` flag is false when the filename couldn't be parsed.

**D-3 `slides.json`.** One record per PDF page, 1-based:
- `n`, `title`
- `text` in reading order, with list structure kept
- `speaker_notes` (if any), `word_count`
- `figures`: each with {fig_id, file, bbox, `ocr_labels` (text + confidence), `repeated_labels`}
- `flags`, from:
  - `image_only`: little or no text layer, mostly image
  - `low_text`
  - `repeated_title`: same title as the previous slide, which is the citation-shift hazard
  - `scan`: no text layer at all
  - `objectives`: this slide lists learning objectives

**D-4 `map.md`.** A header (lecture id, slide count, objective count, flag count), then one line per slide of ≤ ~110 characters:

`NN | title | <words>w | fig:<k> (<first labels…>) | <ILO refs> | <flags>`

ILO refs are a heuristic match of slide text to objective text, marked `~` when uncertain. Target for a 24-slide lecture: ≤ ~2.5k tokens (FR-4).

**D-5 `objectives.json`.** A list of {id `ILO1`…, text, slide}. Empty list plus a `no_objectives` flag when none were detected. Objectives are never invented.

**D-6 `drafts.jsonl` note record.**
- `id`: `n001`…, stable across rounds
- `kind`: `cloze|io|basic`; `notetype`; `deck`
- `fields`: e.g. {Text, Extra}; IO notes carry the image path, preview path and masks
- `tags`
- `tier`: 1–3
- `objective`: ILO id or null
- `source_ref`: list of slide numbers
- `group`
- `action`: `create`, or `update` + `nid` for an existing own note
- `status`: `draft|fixed|dropped|unresolved`

**D-7 `skipped.jsonl`.** {slide, item (short), reason}. The reason is one of:
- `not_testable`
- `anking_covers` (with an AnKing nid)
- `covered_by` (with a note id)
- `out_of_scope`
- `other`

Plus an optional note.

**D-8 `checks/check.json`.**
- `findings`: each {code, severity `blocker|warn`, note_id or slide, message}
- `coverage`: {slides_uncovered: slides with neither a note nor a skip record; objectives_without_t1}
- `stats`: {notes, cards (sum of cloze numbers), tier counts, tier3_share, per-group counts}

**D-9 Review packets.** Self-contained folders. A reviewer needs nothing outside its packet.
- **maintainer/** contains:
  - brief, rubric (A1–A13, S1–S9) and report format, from templates
  - house style
  - `drafts.jsonl`, the round's subset plus group siblings
  - `source_slices.md`: full text of every cited slide plus ±1 neighbour, under `## Slide N` headings
  - `map.md`, `objectives.json`, `check.json`
  - page images for flagged cited slides only
  - `reconcile.md`: the Anki search queries to run for duplicates and AnKing overlap (FR-16)
- **student/** contains:
  - brief, rubric (V1–V9) and report format
  - `sheets.json` + sheet images, or the selected subset (brief Q-3)
  - occlusion previews

**D-10 Reviewer report (JSONL, written by the reviewer agent).**
- Per-card or per-note records: {reviewer, note_id, card (e.g. `c2`) or null, verdict `pass|fix|reject`, codes[], blocker (bool), evidence, rewrite {fields} or null}. Student records also carry `attempt` (answer + right/alternative/unknowable).
- Set records: {type `set`, code, notes[], finding, fix}.
- One closing record: {type `summary`, verdict `PASS|PASS_WITH_FIXES|FAIL`, stats}.

**D-11 `apply_log.json`.** applied[], declined[] {id, reason}, conflicts[] (both reviewers rewrote the same note differently), changed_ids[], dropped[], unresolved[].

**D-12 Gate.** `gate.json`: verdicts, open blockers, `drafts_hash`, counts per kind and tier, notes to write suspended, `status: passed|failed`. Nobody reads it before writing (ADR-9); T-12 summarises it.

**D-13 `write/`.**
- `batches/NN.json`: the exact arguments for each Anki add call (one deck and note type, ≤100 notes, CON-3)
- `updates.json`: field updates for existing notes
- `suspend.json`: which notes to suspend and why
- `expected.json`: expected created, updated and suspended counts, and the search strings to verify them
- `import.txt`: Anki import-file fallback, with header lines

**D-14 `report.md`.** The final report (≤ ~25 lines; brief FR-21).

---

## Orchestration: phase → tools → what the main agent reads

| Phase | Tools / actions | Main agent reads (target) |
|---|---|---|
| P0 Preflight | T-1 `state init`. Anki tools: note-type list, deck list. Facts recorded with T-1. | ≤ 10 lines |
| P1 Extract + target | T-3 `extract`, then T-2 `target` (deck from slide 1). The deck is created with `create_deck` if missing; it is one level, so AnkiMCP can create it. | `map.md` + objectives + target, ≤ ~3k tokens |
| P2 Draft | T-4 `cards source --all` (once), T-4 `--page-image` for flagged slides only, house-style phase file. Claude writes `drafts.jsonl` and `skipped.jsonl`. IO: T-11. | Slide text once (≈5–6k for L006) + flagged images |
| P3 Check & render | T-5 `cards check`, T-6 `cards render` | Findings only |
| P4 Review | T-7 `cards packets`. The two pinned agents (C-7) get packet paths. T-8 `cards apply`. Round 2 scoped. | Apply summary + conflicts only |
| P5 Automatic gate | T-9 `gate`. No human approval; failure stops the build with the reason. | 1–5 lines |
| P6 Write | T-10 `write`, then stage-1 Anki add calls per batch (or `--direct` if Q-1 passed), suspend, verify against `expected.json`. Results recorded with T-1. | Batch files (stage 1 inline only) |
| P7 Report | T-12 `report`, which calls T-13 on this session for the usage line | `report.md` |

---

## T. Tools

### T-1 `cards state`: build state and resume
- **Serves:** FR-2, FR-17, SC-7. **Phase:** all.
- **Inputs:** `--build <dir>`, plus one subcommand:
  - `init`: source path, job
  - `get`
  - `set key=value…`
  - `phase <Pn> start|done`
  - `next`
- **Outputs:** `build.json` (D-1).
- **Behaviour:**
  1. `init` creates the folder and state. If a build for the same source hash exists, it reports it, and the phase reached, instead of creating a new one.
  2. `phase` appends timestamped history.
  3. `set` records facts, such as Anki check results that only Claude can obtain in stage 1.
  4. `next` prints the next phase, its entry condition, and which phase file and tool come next. This is what a resumed session reads first.
- **Stdout:** `next` ≤ 6 lines. Others ≤ 3 lines.
- **Failures:** a corrupt state file (exit 2, with a backup kept); `init` on a path that isn't a file (exit 2).
- **Acceptance:** init → phases → `next` round-trips. A second `init` on the same PDF resumes. Killing a run mid-phase and calling `next` names the right phase.

### T-2 `cards target`: deck, tags, note type
- **Serves:** FR-1, SC-6, ADR-8. **Phase:** P1, right after T-3 (it reads slide 1 from `slides.json`).
- **Reuses:** current `deck_name.py` for filename parsing, source tag and legacy tags.
- **Inputs:** `--build`; the lecture filename (from `build.json`), or `--course --number --title`; optional `--subject`, `--system`; `--existing-decks <file>` (deck list saved by Claude in P0, so collisions can be checked).
- **Outputs:** `target.json` (D-2).
- **Behaviour:**
  1. Parse the `COURSE_L###_[date]_slug` filename, or use the manual flags. This gives the course, number and source tag.
  2. Deck name = the title on slide 1 (`slides.json` record 1, `title`), cleaned:
     - whitespace collapsed
     - `::` replaced with ` - `
     - trailing slide numbers or dates dropped
     - at most 100 characters
     If slide 1 has no usable title (empty, under 3 characters, or the course code alone), use the humanised filename topic: dashes become spaces, sentence case.
  3. If `--existing-decks` lists a deck with that exact name and the build's source tag isn't already in it (Claude records `deck_has_source_tag` in P0), append ` (<COURSE> L<nnn>)`. A re-run of the same lecture reuses its own deck.
  4. Deck depth is always 1. `target.json` sets `create_deck: true` when the deck isn't in the list.
  5. Emit the tags and legacy tags.
- **Stdout:** deck, whether it will be created, source tag (≤ 6 lines).
- **Failures:** filename not parseable gives `confident:false` and exit 1, with the one question to ask the owner (course, number, title). Never guess.
- **Acceptance:**
  - L006 gives deck `Endoplasmic Reticulum, Mitochondria & Golgi Apparatus` (or whatever slide 1 actually says) and the source tag `#ColdRecall::#Source::MED241::L006_…`.
  - A slide 1 without a title falls back to the filename topic.
  - A name collision with another lecture gets the suffix.
  - A malformed filename gives exit 1 with the question.

### T-3 `cards extract`: lecture → text, figures, objectives, map
- **Serves:** FR-3, FR-4, FR-6, FR-7, SC-1. **Phase:** P1. **Model tokens:** zero.
- **Reuses:** current `extract_figures.py` (4× re-render of figure rectangles) and `ocr_regions.py` (label OCR with binarise + upscale + multi-mode). Both measured as necessary for label recall.
- **Inputs:**
  - the source path: a PDF, or a text/markdown file for pasted notes (UC-3)
  - optional `--slides 5-12` for a partial build (UC-2)
  - `--build`
- **Outputs:** `source/slides.json` (D-3), `source/map.md` (D-4), `source/objectives.json` (D-5), `source/figures/`.
- **Behaviour:**
  1. Hash the source. If the hash matches the cache, skip and say so (FR-6).
  2. Per page: title, text in reading order (columns and bullets kept), speaker notes.
  3. Per embedded or vector figure: export it at OCR-grade resolution, OCR the labels, and record repeated labels.
  4. Flag pages (D-3 flags). A page with no text layer gets whole-page OCR so the map still has a title and a word count.
  5. Detect learning objectives (a slide titled objectives/outcomes/ILOs with a numbered or bulleted list). Never synthesise them.
  6. Link slides to objectives heuristically, for the map only.
  7. Text sources become sections treated as "slides", split on headings or blank-line blocks, with the same outputs.
- **Stdout:** slide count, figure count, flag counts, objective count, map path (≤ 8 lines).
- **Failures:**
  - unreadable or cloud-only file: exit 2 with "make it available offline"
  - encrypted PDF: exit 2
  - zero text and OCR unavailable: exit 2
- **Acceptance:**
  - L006: 24 slides, objectives found, map ≤ ~2.5k tokens, titles correct
  - L007: figures exported with ≥ 85% of visible labels OCR'd
  - an image-only fixture page is flagged and still titled
  - a re-run on the unchanged file is a cache hit

### T-4 `cards source`: slice reader
- **Serves:** FR-5, FR-8, RISK-1. **Phases:** P2, P4 (packets use it), REPAIR.
- **Inputs:** `--build` plus one of:
  - `--slides 10-12,14`
  - `--all`
  - `--grep <term>`
  - `--figure <fig_id>`
  - `--page-image <n>`
- **Outputs:**
  - stdout text for slices. `--all` is the one sanctioned full read: compact, one `## Slide N — title` heading per slide, no figure dumps.
  - `--page-image` renders `source/pages/pNN.png` at a resolution that is legible but small, and prints its path.
- **Behaviour:**
  - `--grep` returns matching lines with slide numbers (≤ 20 hits).
  - `--figure` prints the figure path and its OCR labels.
- **Stdout:** the slice text itself. Here the stdout budget is the slice size, not G-3's default.
- **Failures:** slide out of range (exit 2), build not extracted (exit 3).
- **Acceptance:** slides 10–12 return exactly those three. `--all` for L006 is ≈5–6k tokens. A `--page-image` render stays under ~1.5k image tokens.

### T-5 `cards check`: validation, lint, coverage, stats
- **Serves:** FR-11, SC-4, RISK-2. **Phases:** P3, and after each fix round.
- **Reuses:** the lint rules currently inside `render_cards.py` (trailing full stop, underline count, Extra length, escaped HTML, cloze count, comma in blank, bold count, foreign tag trees, citation placement, hint length, unwrapped formula).
- **Inputs:** `--build` (reads `drafts.jsonl`, `skipped.jsonl`, `slides.json`, `objectives.json`, `target.json`).
- **Outputs:** `checks/check.json` (D-8).
- **Behaviour:**
  1. Validate the schema (D-6, D-7). Ids must be unique. `source_ref` slides must exist. Tags must include the source and tier tags, all under `#ColdRecall::`. Deck and note type must match `target.json`.
  2. Lint each note. Mark the known exceptions (enumerations exceeding cloze or bold counts) as `warn`.
  3. Coverage: slides with neither a note nor a skip record; objectives with no tier-1 note; objectives whose enumeration sits below tier 1 (the measured L-failure).
  4. Stats: tier mix and tier-3 share, with a warning when it is under ~5%.
- **Stdout:** `OK` + one stats line, or `FINDINGS` + up to 30 findings grouped by code, with the path to the full list.
- **Failures:** malformed JSON line (exit 2, with the line number).
- **Acceptance:** a clean fixture prints 1–2 lines. A broken fixture with one of each fault prints each. An uncovered slide and an objective with no tier-1 note are both caught.

### T-6 `cards render`: contact sheets
- **Serves:** FR-12. **Phases:** P3, P4 round 2, post-write spot check.
- **Reuses:** current `render_cards.py`, essentially unchanged: the real template and CSS, phone width, night mode, one front per cloze, one back per note, 8 notes per sheet pair, `--only`, `--anki-html`. Lint moves to T-5 (or is shared with it).
- **Inputs:** `--build`, `--only <ids>`, `--per-sheet`, `--anki-html <file>` for post-write checks; `model/` (the note-type snapshot).
- **Outputs:** `renders/sheets/*.png`, `renders/sheets.json`.
- **Behaviour:** as today. Scripts in templates are stripped (NFR-6).
  - **Default note-type source:** the copy shipped in the skill's `assets/coldrecall-cloze/`. That way Claude never has to fetch the templates and CSS through Anki tools and echo them into files, which cost ~4k characters per build in L006.
  - **When to refresh:** only when the note type's CSS is changed during a build. The existing rule already mirrors such changes into the assets copy.
- **Stdout:** sheet count and the `sheets.json` path (≤ 4 lines).
- **Acceptance:** 40 L006 notes give 5 sheet pairs. `--only n007,n015` re-renders those notes only.

### T-7 `cards packets`: reviewer inputs
- **Serves:** FR-13, FR-14, FR-16, SC-8, CON-6. **Phase:** P4.
- **Inputs:**
  - `--build`, `--round <k>`
  - `--only <ids>` (round 2: changed notes; the tool adds group siblings itself)
  - `--student-subset all|half` (brief Q-3)
- **Outputs:** `review/round<k>/maintainer/`, `review/round<k>/student/` (D-9). Each contains a `PROMPT.md`: the ≤ ~300-token instruction the main agent passes verbatim, pointing at the packet's files and naming where to write the report (D-10).
- **Behaviour:**
  1. Refuse to build (exit 3) if T-5 has blocker findings unresolved. Lint gets fixed before reviewers spend tokens.
  2. Copy the brief, rubric and report-format templates from the skill's `templates/review/`.
  3. Maintainer slices: every slide cited by the included notes ±1 neighbour, via T-4. Page images only for flagged cited slides. Include `reconcile.md` with the exact searches to run (source tag, legacy tags, key terms against the AnKing decks).
  4. Student: sheet images per the subset rule, plus occlusion previews. **No drafts, source or HTML** (CON-6).
  5. For more than ~80 notes, split the maintainer per-card review into section packets plus one set-level packet over all drafts (current rule).
  6. Each `PROMPT.md` tells the reviewer to open all of its images in **one** turn (parallel reads), never one image per turn, and to write its report to the named file. In L006 the student's one-image-per-turn reading cost ~1.6M re-read tokens.
  7. Print the two `PROMPT.md` paths and the agents to use: `anki-maintainer` and `anki-student` (C-7), never `fork`.
- **Stdout:** packet paths, file counts, the agent instruction (≤ 8 lines).
- **Acceptance:**
  - L006 maintainer packet contains source slices for every cited slide and nothing from the author's reasoning
  - the student packet contains only sheets and templates
  - the round-2 packet contains only changed notes + siblings
  - `PROMPT.md` is ≤ ~300 tokens

### T-8 `cards apply`: merge and apply fixes in one step
- **Serves:** FR-15, SC-2. **Phase:** P4.
- **Inputs:** `--build`, `--round <k>`; both reviewer reports (D-10); optional `--decline <id>:<reason>` entries supplied by Claude.
- **Outputs:**
  - updated `drafts.jsonl`, with the previous version kept as `drafts.r<k>.jsonl`
  - `apply_log.json` (D-11)
  - `skipped.jsonl` updated for rejections
- **Behaviour:**
  1. Validate both reports. A missing or malformed report gives exit 2, naming which one.
  2. Merge findings by note. A student V2 "alternative answer" escalates to an A2 blocker.
  3. Apply every rewrite and rejection, except where the two reviewers' rewrites of one note conflict. Those go to `conflicts`, untouched, for Claude to decide.
  4. Record declines Claude passed in.
  5. Mark notes `fixed`, `dropped` or `unresolved`. Unresolved means a blocker still open after round 2, written suspended with the `Review_unresolved` tag.
  6. Flag findings that point at the note type's CSS (the same layout fault on many cards) as `css_fix_needed`, instead of patching cards one by one.
  7. Print changed ids and whether round 2 needs agents (> 8 changed) or a self-review (≤ 8 changed).
- **Stdout:** counts (applied / declined / conflicts / dropped), changed ids, the round-2 decision, and each conflict on one line (≤ 20 lines).
- **Acceptance:** fixture reports with fixes, rejects, a conflict and a CSS finding produce correct drafts, a correct log, and the conflict left untouched. There are zero per-note edit calls by the main agent in an L006 run.

### T-9 `cards gate`: automatic gate
- **Serves:** FR-17, CON-9, ADR-9. **Phase:** P5.
- **Inputs:** `--build` (drafts, check, apply logs, reviewer reports).
- **Outputs:** `gate.json`: verdicts, open blockers, drafts hash, counts per kind and tier, unresolved notes to write suspended. Sets `build.json` `gate.status` to `passed` or `failed` and stores `gate.drafts_hash`.
- **Behaviour:**
  1. **Pass** requires all of these:
     - the latest round's maintainer and student summaries are `PASS` or `PASS_WITH_FIXES`
     - no blocker is open except on notes marked `dropped` or `unresolved` (unresolved notes are written suspended)
     - T-5 shows no schema or lint blockers
  2. Otherwise **fail**: exit 1 with the reasons, one per line.
  3. There is no human prompt and no flag that skips the checks.
- **Stdout:** `OK` or `FINDINGS`, with counts or reasons (≤ 10 lines).
- **Acceptance:**
  - A passing L006 fixture sets `passed`.
  - A `FAIL` verdict, an open blocker, or a schema blocker each set `failed` with the reason.
  - No input path skips the checks.

### T-10 `cards write`
- **Serves:** FR-18, FR-19, FR-20, CON-3, CON-9. **Phase:** P6, only when `build.json` has `gate.status = passed` **and** the current drafts hash equals `gate.drafts_hash` (otherwise exit 3).
- **Inputs:** `--build`; `--mode inline|direct`. `direct` exists only if spike Q-1 succeeds; otherwise `inline`.
- **Outputs:** `write/` (D-13).
- **Behaviour:**
  1. Split the notes that passed the gate by kind into batches of ≤ 100, one deck and note type each. Updates go separately.
  2. Each batch file holds *only* the fields Anki needs (fields, tags, deck, note type), so a stage-1 inline call carries no extra payload.
  3. `suspend.json` lists tier 3 + unresolved notes. `expected.json` holds the expected counts and verification searches. `import.txt` is the fallback.
  4. `direct` mode (conditional on Q-1) writes to Anki itself, then verifies and records the results.
- **Stdout:** batch count, note counts, verification searches (≤ 10 lines).
- **Failures:** gate not passed (exit 3), drafts changed after the gate (hash mismatch, exit 3).
- **Acceptance:** L006 gives one cloze batch of 40, a suspend list of 2, and an `import.txt` that imports cleanly into a scratch profile.

### T-11 Figure and occlusion tools (existing)
- **Serves:** FR-10. **Phase:** P2.
- **Reuses as-is:** `extract_figures.py`, `ocr_regions.py`, `build_occlusion.py` (shared label → shared index, `--keep`, preview).
- **Changes required:**
  1. Accept T-3's `fig_id`s and write into `source/figures/`.
  2. Write occlusion records in D-6 form for direct appending to `drafts.jsonl`.
  3. Follow G-3's stdout contract.
- **Acceptance:** an L007 figure produces an IO draft record and a preview that the student packet includes.

### T-12 `cards report`
- **Serves:** FR-21. **Phase:** P7.
- **Inputs:** `--build`.
- **Outputs:** `report.md` (D-14) with:
  - created and updated counts per kind and tier
  - deck, suspended count, tier-3 share
  - figures occluded and skipped
  - review rounds, fixed/rejected/declined counts, conflicts and how they were resolved, and whether the review was independent
  - the student's attempt score
  - AnKing unsuspend proposals
  - the `tag:` search
  - the reminder to sync
  - **the usage line** (FR-27): T-12 calls T-13 on the current session's transcript and appends one line of calls, peak context and cost estimate, plus any failed waste check by ID
- **Stdout:** the report (≤ 25 lines).
- **Acceptance:** L006 report numbers match Anki read-back.

### T-13 `cards meter`: measure usage (developer tool)
- **Serves:** FR-24, all SCs, RISK-6. **Used:** after acceptance runs, not during a build.
- **Inputs:**
  - a Claude Code session id or transcript path, plus its subagent transcripts
  - optional `--build` for phase attribution from `build.json` timestamps
  - a price table (configurable)
- **Outputs:** `cost.json` + `cost.md`. Both must report:
  - per-call rows: time, model, input, cache write, cache read, output, context size, tools used
  - totals
  - first-call and peak context
  - auto-compactions (count, tokens before and after)
  - per-subagent totals, including whether each was a fork and its first-call context
  - image reads in the main context
  - repeated large tool inputs (the same payload sent more than once)
  - tool errors followed by retries
  - API-equivalent cost, per phase where attribution is available
  - pass/fail for each waste check W-1 to W-8 (brief §6), with the evidence (call index, tool, argument excerpt ≤ 120 characters) for any failure
  - `--line` mode: one summary line for the build report
- **Behaviour:**
  - De-duplicates multi-block assistant messages by message id, so usage is counted once per call.
  - **Finding the current session:** the newest `*.jsonl` under `~/.claude/projects/<cwd-slug>/` whose modification time is at or after `build.json`'s P0 start, plus its `subagents/` folder.
  - **Environment baseline for W-8:** the main session's first-call context.
- **Acceptance:** on the 2–3 Nov L006 transcript it reproduces:
  - 76 main calls
  - first-call context ≈ 79k and peak ≈ 166k
  - 2 compactions
  - 2 fork subagents
  - API-equivalent ≈ $9
  - W-1 (2 compactions), W-2 (PDF page images), W-3 (2 forks), W-4 (`add_notes` payload sent 3×), W-5 (localhost curl), W-6 (9 edits to `drafts.jsonl`), W-7 (sheet views) and W-8 all **fail**: the meter must catch every waste the audit found

---

## C. Configuration (not scripts)

- **C-1 Lean workspace (FR-25).** Exact keys: design spec §7. Project-level settings for `this repository` that:
  - turn off plugins, hooks and MCP servers the skill doesn't use (the claude-flow/ruflo set, whose agent and skill listings, tool names, routing hook and CLAUDE.md lines cost ~15k tokens per call)
  - trim AnkiMCP's exposed tools to the ones the skill uses

  The builder picks the mechanism. Verify with T-13: first-call context drops ≥ 10k tokens.
- **C-2 Deck convention.** Superseded by ADR-8: flat decks named after the slides (see T-2). Existing nested decks are left alone.
- **C-3 Templates.** `templates/review/` holds the maintainer and student briefs, rubrics and report formats (ported from the current SKILL.md, with report formats changed to D-10 JSONL). These are not loaded by the main agent.
- **C-4 Deferred.** Pulling existing notes into draft format for REPAIR (brief FR-23) needs either an Anki read that writes to a file (stage 2) or Claude echoing note content. It is deferred with brief Q-4, so no T-tool is specified for it in v1.
- **C-5 HARVEST (brief FR-22).** Reuses T-5 to T-10 unchanged, with no new tool. The `learning` skill hands over the atoms; Claude writes them to `drafts.jsonl`; 8 or fewer notes go to self-review instead of T-7. Shipped with REPAIR per brief Q-4.

- **C-6 Runtime guards (Claude Code hooks in `this repository/.claude/`).** Four PreToolUse hooks, each fail-closed, in Python:

  | Hook | Matcher | Blocks |
  |---|---|---|
  | `block_fork.py` | `Agent` | `tool_input.subagent_type == "fork"` |
  | `block_pdf_read.py` | `Read` | `tool_input.file_path` ending `.pdf`, any case. With `CARDS_PDF_GUARD=build` (default) it blocks only while `builds/.current` exists, so v1 `/anki` keeps working. Phase 7 sets `always`. Message: use `cards extract` and `cards source`. |
  | `block_local_http.py` | `Bash` | Commands containing `127.0.0.1`, `localhost:`, `0.0.0.0:` or `[::1]`. Message: Anki is reached only through the `mcp__anki__*` tools; on a hard error, stop and report. |
  | `require_review_before_write.py` | `mcp__anki__add_notes\|mcp__anki__add_note\|mcp__anki__update_note_fields\|mcp__anki__update_notes` | Blocks while `builds/.current` names a build whose gate hasn't passed, or whose drafts hash no longer matches. With no active build (manual use), the call is allowed. |

  The shipped scripts are tested by `tools/verify_hooks.py`. Phase 6 wires them and confirms each fires in a real session.

- **C-7 Reviewer agents (`this repository/.claude/agents/`).**

  | Agent | Model | Effort | Tools | Settings |
  |---|---|---|---|---|
  | `anki-maintainer` | `claude-sonnet-5-5` | `high` | `Read, Grep, Glob, Write, mcp__anki__find_notes, mcp__anki__notes_info` | `permissionMode: dontAsk`, `omitClaudeMd: true`, `maxTurns: 14` |
  | `anki-student` | `claude-sonnet-5-5` | `medium` | `Read, Write` | `permissionMode: dontAsk`, `omitClaudeMd: true`, `maxTurns: 6` |

  Each body says only: read `PROMPT.md` in the packet folder you are given; follow it; write the report where it says; return at most 5 lines. The rubric lives in the packet (C-3), not in the agent file.
  - **Main session:** SKILL.md frontmatter `model: claude-sonnet-5-5`, `effort: medium`, and the Cards project setting `model: claude-sonnet-5-5`.
- **C-8 Student subset (resolves brief Q-3).** T-7 gives the student every sheet pair when there are ≤ 6 pairs (48 notes). Above that, it gives every pair containing a tier-1 note plus at least one note from each group, and says in `PROMPT.md` which pairs were left out.

---

## F. Fixtures and acceptance tests

| Fixture | Used by | Purpose |
|---|---|---|
| L006 PDF (`MED241_L006_2026-09-13_endoplasmic-reticulum-mitochondria-and-golgi-apparatus.pdf`) | T-2, T-3, T-4, T-5 to T-10, T-12 end-to-end | Brief SC-1 to SC-8 baseline comparison |
| L007 PDF (`MED241_L007_2026-09-14_anatomy-of-the-pectoral-region.pdf`) | T-3, T-11, T-7 | Figure-heavy and occlusion path |
| `drafts_broken.jsonl` | T-5 | One fault per lint, schema and coverage code |
| Reviewer report fixtures (fix, reject, conflict, CSS finding, malformed) | T-8 | Merge and apply logic |
| Image-only page and text-only "pasted notes" file | T-3 | Flags, OCR fallback, text-source path |
| 2–3 Nov L006 transcript | T-13 | Reproduce the baseline numbers |

**End-to-end acceptance.** A fresh Claude Code session in the lean workspace runs `/anki2` + the L006 PDF, with no human replies. T-13 on that session must pass W-1 to W-8, and the report must show SC-4 holding. The owner then does the SC-5 side-by-side comparison with the v1 deck. The same run is then repeated on L007.

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-11-04 | Initial TRD, companion to brief v0.1.0 |
| 0.2.0 | 2026-11-05 | `cards` subcommands; flat deck from slide 1 (T-2); automatic gate (T-9); waste checks and the per-build usage line (T-12, T-13); runtime guards (C-6), pinned reviewer agents (C-7), student subset rule (C-8) |
