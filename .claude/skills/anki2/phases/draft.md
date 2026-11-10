# P2: draft

Load only while drafting, never on resume past P2. Read the source once with
`.venv/bin/cards source --build <build> --all`; afterwards use the map and slices.
`drafts.jsonl` is the inventory as well as the notes: no separate manifest.

## Reconcile and cover

Search the source tag, target legacy tags, target deck and AnKing concepts using
`mcp__anki__find_notes`; inspect relevant matches with `notes_info`. Reuse own
notes with `action: update` and their existing nid. AnKing matches become
unsuspend proposals and `anking_covers` skips, never duplicate new notes.
Keep proposals with note/card ids in `<build>/anking-proposals.json`; do not act
on them automatically. Never rewrite AnKing's fields, tags or note types.

Cover every testable item, with no count cap. Map items to stated objective ids.
Keep source terms, hedges and units; mechanism essays belong in understanding
notes, while their examinable facts belong on cards. Do not create vault files.
For anatomy, order coverage bones/landmarks → joints → movements → muscles →
nerves/vessels. Enumerate figure candidates by objective coverage and record why
any are skipped. `cards check` blocks (C05) any slide whose figure has five or more
OCR labels unless the slide has an io note or a `skipped.jsonl` record whose item
starts `Figure:` and gives the reason. Labelled anatomy figures are the default
candidates for occlusion; skip one only with a stated reason. Load
`phases/occlusion.md` only when actually occluding a figure.

## Tiering

| Tier | Meaning | Evidence |
|---|---|---|
| 1 | Must know | Stated objective, explicit exam emphasis, summary or repeated core fact |
| 2 | Likely examinable | Supporting definitions, values, classifications, labelled structures |
| 3 | Peripheral completeness | Asides, extended details, background and worked examples |

An objective's enumerated members belong in Tier 1; do not promote a clinical
aside without objective support. A Tier-3 share below about 5% is a warning to
recheck tiering, not a quota to invent peripheral cards. Tier 3 is written
suspended. For explicitly requested carding ahead, record the request in
`<build>/write/carding-ahead.json`; write.md explains the additional suspension.

## House style — AnKing

- Default text type: `ColdRecall Cloze`, fields `Text` and `Extra`. Use a sentence
  with one relationship and enough visible context for exactly one answer.
  Use two or three clozes where useful, at most about five except enumerations.
  Parts of one answer share a number; cloze both sides rather than reverse notes.
- One item per deletion; never hide a comma-separated list or a filler word.
  Keep context outside blanks. Rephrase grammar that leaks the answer; use
  `a(n)` only when an article cannot be removed. Avoid counts that cue completion.
- State classification schemes and exceptions visibly when alternatives fit.
  Sibling names must not reveal each other's answers.
- A hint names a category, not the answer, stays short (about 20 characters),
  and uses consistent vocabulary. Sister notes with swappable answers need
  distinguishable hints. Direction blanks use binary hints in this order:
  `{{c1::increases::increases/decreases}}`, `{{c1::high::high/low}}`, unless obvious.
- Bold the main subject, not every noun. Put `<b>` outside cloze braces:
  `<b>{{c1::tryptophan}}</b>`. Underline at most one or two meaning-changing
  qualifiers or source hedges; never filler. Italics only for source emphasis.
- Bold full disease names, not their abbreviations. No final full stop; capitals
  only for sentence starts and proper names. Use `<sub>`/`<sup>` for chemistry
  and units. Keep units with values in the source's units.
- Use `<span class="nw">…</span>` for formulas, hyphenated terms and multiword
  answers that must stay together on phones. Bold mnemonic words; do not
  underline individual letters. One-by-one reveal is only for fixed-order
  sequences or mnemonics, never an unordered set.
- Extra is optional context after answering, never necessary to answer. At most
  three lines/about 200 characters: brief why, useful contrast/mnemonic, citation.
  No imported clinical pearls or a second testable fact. Separate lines with
  `<br>`, not raw newlines. Capitalise each line; use `- ` only with multiple
  content lines. Citation goes last in its own `<div class="src">L006, slide 7</div>`
  with no preceding `<br>`. No `<i>` in Extra; the model already styles it.
- An image needed before answering belongs on the front, with text revealed
  above it. An image useful only afterwards belongs in Extra. Labelled figures
  use native `Image Occlusion`; Basic/reversed types are rare, only if preflight
  explicitly supports them. Do not invent a note type to bypass target checks.

## Draft schema summary

Write `<build>/drafts.jsonl` and `<build>/skipped.jsonl` in **one Write each**.
Do not then read/echo either file. JSONL is one object per line, no fences or
blank lines. Script-generated files may start with an `_meta` record; do not
invent script provenance for hand-authored drafts.

Each draft has:

- `id`: stable unique `n001` style id, never reused after dropping.
- `kind`: `cloze`, `io` or `basic`; `notetype` and flat `deck` from `target.json`.
- `fields`: exact note-type field names with string HTML values.
- `tags`: target source tag, matching tier tag and applicable base tags, all under
  `#ColdRecall::`; no spaces in tags, use underscores.
- `tier`: integer 1–3; `objective`: objective id or null; `source_ref`: nonempty
  list of actual 1-based PDF page numbers; `group`: shared concept/sibling id.
- `action`: `create` with `nid: null`, or `update` with positive existing note id.
- `status`: initially `draft`; later scripts manage `fixed`, `dropped`, `unresolved`.
- For IO, `media: [{"path":"source/figures/…png","filename":"L006_…png"}]` and
  `preview`: build-relative generated preview path; see occlusion.md.

A skip has `slide` (real page number), `item`, `reason`, and an explanatory
`note`. Allowed initial reasons: `not_testable`, `anking_covers` (requires `nid`),
`covered_by` (requires an existing draft `note_id`), `out_of_scope`, `other`.
Use skips for deliberate omissions, not to conceal missed objective coverage.

Write text drafts before running `cards figures`: that tool appends IO notes and
preserves their ids on an identical rerun. Do not overwrite its additions.
Review rewrites go through `cards apply`, never a sequence of note Edits.
