---
name: "anki"
description: "Makes AnKing-style Anki cards (cloze, tagged, image occlusion) from lectures or a study session via AnkiMCP. Every batch is rendered as the student will see it and reviewed by two independent agents: an AnKing maintainer (content) and a student (look and use). Also reads due cards and retention and repairs failing cards."
---

# Anki

Cards that pass exams, written from the source in the source's own terms, in
the house style of the AnKing deck: mostly cloze, bold on the main subject,
one relationship per sentence, styled like AnKing's own cards, and tagged so any
lecture can be found, filtered, suspended or unsuspended in one search.

**No card reaches Anki without passing the review panel.** Every draft is first
rendered through the real note type, exactly as it will look on a phone, and
tiled into contact sheets. Then two independent agents review it in parallel:

- **The maintainer** reads the card text against the source, the way an AnKing
  deck maintainer reviews a suggestion, card by card *and* as a set.
- **The student** sees only the contact sheets. They study each card the way they
  would during reviews (front, commit an answer, flip) and judge how it looks
  and how it is to use.

See **The review panel** below.

This skill has three jobs. Work out which one you're doing before touching Anki.

| Job | When | How many cards | Review panel |
|---|---|---|---|
| **1. BUILD** a deck from source material | "make cards from this lecture / PDF / chapter", "card L3", "occlude this diagram" | Coverage-driven, no cap — every testable item, ranked into tiers | Render + both reviewers on every note, plus set review; post-write spot check |
| **2. HARVEST** at the end of a study session | the `learning` skill's commit step | A handful — only must-know atoms that surfaced. Zero is normal | Same, small batch. Skipped only when zero cards |
| **3. READ & REPAIR** | session read-back; "what's due?"; "this card keeps failing" | — | Every rewrite rendered and reviewed with its siblings and near-twins |

Read `references/card-quality.md` before writing the first card of a session.
For figures, `references/image-occlusion.md`. Scripts are in `scripts/`, next
to this file. Where `card-quality.md` and this file disagree, **this file wins**
(it carries the newer AnKing maintainer conventions and what rendering showed).
In particular, `card-quality.md`'s examples put `<b>` *inside* cloze braces and
underline every direction word. Both are now wrong: see **Formatting**.

---

## Connection

- **Server:** the AnkiMCP add-on (AnkiWeb code `124672614`), running inside
  Anki 25.07+ at `http://127.0.0.1:3141/`. **Anki must be open.**
- **Tool names vary by where you are running** — `add_notes` may appear as
  `mcp__anki__add_notes`, `mcp__remote-devices__anki__add_notes`, and so on. Use
  whichever exists.
- **No Anki tools, or they fail?** Say so in one sentence (usually: Anki is
  closed, or the connector isn't set up — the cold-recall repo's
  `docs/03-troubleshooting.md`). Never claim cards were made. For a BUILD, offer
  to write the notes to a file Anki imports in one step — see **Fallback: import
  file** at the end. The reviewer still runs first.
- **Facts about the tools that trip people up:**
  - `create_deck` allows **two levels** only (`Parent::Child`).
  - `find_notes` returns **note** ids. Suspending, unsuspending and
    `get_card_memory_state` take **card** ids — get them from `notes_info`
    (each note lists its `cards`) or `cards_stats(deck)` (every card with its
    `cid`, tags and `dueToday`). One cloze note can make several cards.
  - `add_notes` takes one deck and one note type per call, at most 100 notes,
    and checks duplicates against the first field (`Text` for Cloze).
  - `get_card_memory_state` needs FSRS turned on in the deck options.
  - Cloze siblings (c1, c2… of one note) are buried for each other on the same
    day — so a fact split across siblings is reviewed on different days, and a
    fact split across *notes* can collide on the same day.

The vault lives at `<your notes vault>`.

---

## What belongs on a card

The vault holds **understanding** — mechanisms, derivations, the learner's own
explanation and errors. Anki holds **what must come back on demand** — terms,
values, named things, classifications, sequences, labelled structures, and the
exam-facing *facts that fall out of* a mechanism.

Two rules keep the stores honest:

- **No essay cards.** A card whose answer is an explanation belongs in the vault
  as a concept. Card the facts the explanation produces, not the explanation.
- **No atom-list notes in the vault.** A list of terms is cards, not a note.

AnKing's own bar for whether a card earns its place: **it directly helps you
answer an exam question.** "Might be tested" and "nice to have" are not reasons.

For **HARVEST** the bar is stricter, because the session has just built the
understanding in the vault: card only atoms that **(i)** can't be derived from
something the learner now holds **and (ii)** are genuinely must-know for the
exam or the clinic.

---

## House style — AnKing

Full rules and worked ✗/✓ rewrites: `references/card-quality.md`. The core,
including the conventions from the AnKing maintainers' submission guidelines:

**Content**

- **Cloze is the default for everything textual.** One sentence, one
  relationship, enough visible context that exactly one answer fits.
- **Two or three clozes per note**; blanks that form one answer **share a
  number**; cap ~5 per note except a genuine enumeration.
- **Cloze both sides of a relationship** (drug as c2, class as c1) instead of
  making reversed cards.
- **One item per deletion** — a comma inside a blank is a list card in disguise.
  Never blank a filler word; blank the operative word.
- **`a(n)` before a blank.** No counts that tell you when to stop. Grammar
  (singular/plural, verb agreement) must not give the answer away. Better
  still, rephrase so no article sits before the blank ("contains the
  {{c2::indole}} ring"); students read `a(n)` as clunky.
- **Context words stay outside the blank:** "bacterial {{c1::peptidoglycan}}
  cell walls", not "{{c1::bacterial peptidoglycan}} cell walls".
- **Members of a scheme-specific group** (aliphatic, aromatic, basic…): if
  another amino acid, drug or structure would also fit the blank in a
  different scheme, state the exception in the visible text: "(histidine
  counts as heterocyclic)". This was the commonest blocker in testing.
- **Sibling clozes must not answer each other:** "aspartic acid … {{c3::acidic}}"
  is answered by the visible name. Blank what the names don't give away.
- **The source's terms and the source's hedges.** "Associated with" never
  becomes "causes". Use the lecturer's vocabulary, but shape it into a card
  sentence — don't paste whole slide sentences or paragraphs verbatim.

**Hints**

- **Hints name the category, never the answer:** `{{c1::parotid::gland}}`.
- **Direction blanks get the binary hint, in this order:**
  `{{c1::increases::increases/decreases}}`, `{{c1::high::high/low}}` — unless
  the answer is obvious from context.
- Use the **same hint word for the same category** across the deck (always
  `location`, never `location` on one note and `site` on the next), but
  don't reuse one hint on sister notes whose answers differ and could swap
  (`[structural group]` on aliphatic, branched-chain and aromatic made each
  accept the others). Make it specific: `[chain shape]`, `[ring type]`.
- **A hint must not describe the answer uniquely.** `{{c1::arginine::guanidino
  side chain}}` turns "which amino acids are basic" into "which has a
  guanidino group", which is a leak.
- **Keep hints short** (about 20 characters). A long hint such as
  `[glucogenic/ketogenic/both]` overflows a phone screen; use
  `[gluco/keto/both]`.

**Formatting** — the eye goes to bold first, then underline, then italics

- **`<b>` the main subject** — the named thing the sentence is about (drug,
  disease, structure, cell, enzyme). Don't bold everything that is a noun.
- **Bold goes outside the cloze braces:** `<b>{{c1::tryptophan}}</b>`, never
  `{{c1::<b>tryptophan</b>}}`. In AnKing-styled note types bold has its own
  colour, and inside the braces it hides the answer colour, so the revealed
  answer looks like every other bold word. (The ColdRecall note type guards
  against this too, but write it correctly anyway.)
- **`<u>` sparingly** — at most one or two per note (the student reviewer
  treats every underline as one more AMBOSS look-alike), only a qualifier that
  flips the meaning if misread (`<u>not</u>`, `<u>only</u>`, `<u>most
  common</u>`) or the source's hedge. **Never filler words** (`and`, `both`,
  `the`, `all`). In Anki, the AMBOSS add-on also underlines medical terms in
  teal, so underlines pile up quickly.
- `<i>` for the source's own emphasis. `<sub>`/`<sup>` for chemistry and units
  (`K<sup>+</sup>`, `HCO<sub>3</sub><sup>−</sup>`), never "K+" or "CO2".
- **Disease name bold, abbreviation not:** `<b>Acute kidney injury</b> (AKI)`.
- **No full stop at the end of a card.** Capitals only for names and the start
  of a sentence ("type II pneumocytes", not "Type II Pneumocytes").
- Numbers carry their units, in the source's units.
- **Keep things that mustn't break on one line:** wrap formulas, hyphenated
  terms and multi-word answers in `<span class="nw">…</span>`:
  `<span class="nw">(–COOH)</span>`, `<span class="nw">D-alanine</span>`,
  `{{c1::<span class="nw">glutamic acid</span>}}`. Otherwise phones break
  "(– / COOH)" and "D- / alanine" across lines.
- Mnemonics: bold the mnemonic word (`<b>PVT TIM HaLL</b>`). Don't underline
  letters: in testing, underlined letters looked like AMBOSS links.

**Extra** (shown after answering, never needed to answer)

- **At most three lines, about 200 characters.** In this order, only if useful:
  the one-line *why*; a mnemonic or contrasting look-alike; then the citation
  (`L3, slide 14` / `Kaplan Biochemistry, Ch. 1`) and `Vault: <note name>` if
  the understanding lives there. No "clinical pearls" or rules of thumb the
  source didn't give. A second fact is a second card, not more Extra.
- **Lines are separated with `<br>`, never raw newlines.** HTML collapses
  newlines, so `- a\n- b\n\nSource` renders as one run-on paragraph.
- Capitalise each line. Content lines start with `- ` only when there are
  two or more; a single content line has no dash.
- **The citation is its own block, last:** `<div class="src">Kaplan
  Biochemistry, Ch. 1</div>`. Don't put a `<br>` before it. The note type
  sets it smaller and upright, so it never reads as another bullet. An
  Extra with nothing to add is just the citation block.
- No `<i>`: the ColdRecall note type already sets Extra in muted italics.
  Bold only a named thing being contrasted.

**Images**

- Image shown *before* the answer, text answer → reveal the text **above** the
  image. Image is the answer → reveal it below.
- Image only useful *after* answering → it goes in Extra, not a cloze.

**One-by-one** (sequential reveal) only for items recalled **in a fixed order**
— a mnemonic or a sequence (steps of a pathway, order of treatment). Never for
a 2–3 cloze note unless it is a mnemonic, and never for a set whose members
can't be told apart by order.

| Knowledge shape | Note type |
|---|---|
| Anything that sits in a sentence — terms, values, facts, sequences, enumerations, compare/contrast | **ColdRecall Cloze** (fields `Text`, `Extra`) |
| A labelled figure | **Image Occlusion** |
| A synonym pair tested both ways; a question that genuinely won't become a sentence | Basic (and reversed card) / Basic — rare |

**ColdRecall Cloze** is the house note type. It is a lean clone of the AnKing
MCAT note type's look: slate background, green answer, purple bold, teal
underline, and Extra in muted italics under a rule. It adds review-panel fixes:
a phone gutter, a soft highlight behind the revealed answer (so it doesn't
differ from other bold names by colour alone), left-aligned Extra, the `.src`
citation block, and the `.nw` no-wrap class. It has no AnkiHub hooks,
so AnkiHub updates never touch it. If it's missing (new computer, new profile),
create it once from `assets/coldrecall-cloze/` before writing (see **Setting up the note type**). Don't create any other note
types. Don't write into a shared deck's own note types (AnKingOverhaul, AnKing
MCAT and similar), because those belong to that deck. Existing notes on the
plain `Cloze` type stay where they are unless the user moves them (Browse →
Notes → Change Note Type, mapping `Back Extra` → `Extra`).

---

## Tags and decks

Organisation lives in **tags**, under one root, the way AnKing does it. Decks
stay shallow.

| Tag | Example | Purpose |
|---|---|---|
| `#ColdRecall::#Source::<Course>::L<nnn>_<Title>` | `#ColdRecall::#Source::MED241::L003_Cell_organelles` | Where it came from. Unsuspend or filter a whole lecture with one search |
| `#ColdRecall::^Subjects::<Subject>` | `#ColdRecall::^Subjects::Histology` | Discipline |
| `#ColdRecall::^Systems::<System>` | `#ColdRecall::^Systems::Renal` | Organ system — medicine/dentistry only; omit otherwise |
| `#ColdRecall::!Tier::<1-3>` | `#ColdRecall::!Tier::3` | Exam value. Tier 3 is written suspended |
| `#ColdRecall::!Session::<YYYY-MM-DD>` | `#ColdRecall::!Session::2026-09-27` | Harvested in a study session |
| `#ColdRecall::!Flags::IO_estimated` | | Occlusion boxes placed by eye, not OCR |
| `#ColdRecall::!Flags::Review_unresolved` | | Reviewer blocker not fixed after two rounds — written suspended |

- **Get the deck and tags from the script, not by hand:**
  `python3 scripts/deck_name.py "<lecture filename>" --subject Histology --system Cell`.
  It parses `COURSE_L###_[YYYY-MM-DD]_topic-slug` filenames into
  `COURSE::<n>. <Topic>` and the matching source tag. If it can't parse the name
  (`confident: false`), **ask the user once** for course (or book), number and
  title, then run it with `--course --number --title`. Never invent a deck name,
  and never ask for one the filename already gives.
- **Tag text:** no spaces (use `_`); `::` only between levels.
- **Every tag lives under `#ColdRecall::`.** Never write into another deck's tag
  tree (`#AK_MCAT_v2::…`, `#AK_Step1_v12::…`). Your own card would then show
  up in AnKing's own searches and filters.
- **Match what's already there.** Before writing into an existing deck, check
  `tag_management` → `get_tags` for that deck. If it already uses another scheme
  (e.g. older cold-recall `subject::`/`topic::`/`src::`, or ankipro's
  `src::`/`tier::`), keep using that scheme for that deck and say so. When
  reconciling, search the legacy tags too (`deck_name.py` prints them).
- **Decks:** two levels, `Course::<n>. Topic`. Check `list_decks` first — course
  codes normalise (`BIO 101` → `BIO101`), so reuse an existing spelling rather
  than creating a near-duplicate. The user's existing convention wins.
- **Searching:** `tag:X` also matches X's children, so
  `tag:#ColdRecall::#Source::MED241` is the whole course.

---

## The review panel

The author never grades its own cards. Each batch of drafts goes through three
steps:

1. **Render and lint.** A script renders every card into contact sheets, plus
   mechanical findings.
2. **Review.** Two independent agents run **in parallel, in the same
   message**:
   - **The maintainer** (content: text + source).
   - **The student** (look and use: contact sheets only).
3. **Merge.** You merge both reports, fix, re-render what changed, and
   re-review it.

### Token budget — read this first

The panel is the expensive part of the skill. One measured run (24 notes, two
rounds) spent about **1 million subagent tokens**, mostly because the student
opened about 180 screenshots one at a time, twice. Each image opened is a turn,
and every turn re-reads the agent's growing context. The rules below keep a
lecture-sized batch to a fraction of that:

- **Contact sheets, not screenshots.** The student gets `renders/sheets.json`:
  a fronts sheet and a backs sheet per 8 notes. That's about 6 images for 24
  notes instead of 138.
- **One back per note** (every cloze revealed); fronts stay one per cloze.
  Desktop renders only for 3 sample notes, which you check yourself.
- **The maintainer reads text, not pages.** Give it `slides.md` (per-slide text
  from `pdftotext -layout`, one `## Slide N` heading each). It opens a page
  image only to verify a figure or an occlusion.
- **Round 2 is scoped to what changed.** Re-render with `--only <changed ids>`.
  The student gets only those sheets; the maintainer gets only those notes plus
  their `group` siblings. Never re-send the whole batch.
- **Small batches skip the agents.** For **≤ 8 changed or new notes** (most
  HARVESTs, most REPAIRs, deck fixes), do the two self-review passes from **No
  subagent available?** on the sheets, and say it was a self-review. Use the
  agents for BUILDs and remakes.
- **Keep payloads out of your own context.** Write drafts with a script, not by
  echoing JSON into the conversation; print only counts and lint.

### When it runs

- **BUILD:** Phase 4, after every note (text and occlusion) is drafted and
  before anything is written to Anki, plus a spot check after writing.
- **HARVEST:** after the atoms are drafted, before they are written — or, in
  propose-first mode, before they are proposed. Skipped only when there are
  zero drafts.
- **REPAIR:** on every rewrite or split, reviewed together with the failing
  card's siblings and near-twins.

### Step 1 — Render and lint

`scripts/render_cards.py` fills each draft into the note
type's real template and CSS at phone width (390 px, AnkiMobile classes, night
mode), cropped to content. It renders one front per cloze number and one back
per note with every cloze revealed, then tiles them into labelled contact
sheets: `renders/sheets/sheet_NN_fronts.png` and `sheet_NN_backs.png` cover the
same notes, and `renders/sheets.json` lists them in reading order. The first 3
notes also get a desktop back (`--desktop-sample`, `--light` for day mode).
Single cards stay in `renders/cards/` if you need one. Scripts are stripped, so
add-on snippets such as AMBOSS, which carry login tokens, never run or appear.

```bash
# use the note type as it is in Anki now (preferred): once per session save
#   model_templates("ColdRecall Cloze") → model/front.html, model/back.html
#   model_styling("ColdRecall Cloze")   → model/style.css
# or, if Anki isn't reachable, the copy shipped with this skill:
#   --model-dir <skill>/assets/coldrecall-cloze
python3 <skill>/scripts/render_cards.py --drafts drafts.jsonl --model-dir model --out renders
```

Drafts carry their fields under the note type's own names:
`{"id":"n017","fields":{"Text":"…","Extra":"…"},"tags":[…],…}`. The script
writes `renders/sheets.json` and `renders/lint.json`.
The lint findings are mechanical, not judgements:

- raw newlines in Extra
- a trailing full stop
- underlines on filler words, or more than three underlines
- Extra over three lines or about 200 characters
- card text over about 200 characters
- escaped HTML
- more than 5 cloze numbers
- a comma inside a blank
- more than 4 bold runs
- tags inside another deck's tree
- a citation outside `<div class="src">`
- a hint longer than about 20 characters
- an unwrapped formula inside a blank

L9 (cloze count) and L11 (bold count) are expected on a genuine enumeration;
say so and move on.

Fix lint findings yourself before the reviewers run. They are free to fix, and
fixing them first leaves the reviewers' attention for judgement calls.
**Look at the first fronts sheet and one backs sheet yourself** before sending
the batch out. That's two images, and it catches layout faults before they cost
a reviewer round.

Image Occlusion notes aren't rendered by the script. Their preview PNGs from
`build_occlusion.py` go to the student instead.

### Maintainer — what it gets, and what it doesn't

Write these to files in your working directory (never the vault) and give the
agent their paths. It must be able to open them in its own environment — if
the source lives on the user's computer, stage it or extract its text first.

1. **`drafts.jsonl`** — one note per line:
   `{"id":"n017","notetype":"ColdRecall Cloze","deck":"…","fields":{"Text":"…","Extra":"…"},"tags":[…],"tier":2,"source_ref":"L025 slide 12","objective":"LO3","group":"g04"}`.
   `group` ties related notes (one enumeration, one compare/contrast, one
   figure). Occlusion drafts carry the image path, the preview PNG path and the
   mask list.
2. **The source as text:** `slides.md`, built with `pdftotext -layout` and
   one `## Slide N` heading per page. Add page images (`pdftoppm -r 80 -f N -l N`)
   only for slides that carry a figure the drafts use, i.e. occlusions or
   "the figure labels…" claims.
3. **`existing.jsonl`** — the notes already in the target deck and source tag
   (`find_notes` → `notes_info`), plus any AnKing notes the search turned up for
   the same concepts, with their note ids. This is what lets it catch
   duplicates and interference with cards outside the batch.
4. **The learning objectives** and, for BUILD, the verified manifest.
5. **`references/card-quality.md`**, this file's **House style** section,
   `renders/lint.json`, and the brief below.

It does **not** get your reasoning, your earlier drafts, or your opinion of the
cards. Use `subagent_type: general-purpose` (it needs file reading and PDF/image
viewing). Over ~80 notes: split the per-card review across parallel agents by
section, and run **one** set-level agent over the whole `drafts.jsonl` — set
problems only show when the whole set is in view.

### Maintainer brief (pass it verbatim, filling the paths)

> You are an AnKing deck maintainer reviewing a batch of suggested notes for a
> medical student's deck. Your job is to find what is wrong, not to approve.
> You have: drafts at `<drafts.jsonl>`, source at `<source>`, existing and
> AnKing notes at `<existing.jsonl>`, objectives at `<objectives>`, and the
> house style in `<card-quality.md>` plus the rubric below. Judge every note
> against every rule, then judge the set as a whole. Every finding must cite a
> rule code and concrete evidence (the exact text, and the slide for fidelity
> findings). Don't invent rules; don't flag taste. Where you flag, write the
> corrected note. Return only the report format below.

### Rubric — the maintainer, per note

| Code | Check | Blocker when… |
|---|---|---|
| **A1 Atomic** | One relationship per sentence; each cloze number tests one thing | Two facts in one blank, a clause deleted, a list inside a blank |
| **A2 One answer** | Given only the visible text, exactly one answer fits; a category hint where the level is ambiguous | A classmate who knows the fact could still answer differently |
| **A3 No leakage** | Article (`a(n)`), counts, singular/plural, verb agreement, a hint naming the answer, or a sibling cloze's visible text don't give it away | Any leak |
| **A4 Blank value** | The operative, high-yield word is blanked — not filler, not the obvious word | Blank carries no information |
| **A5 Fidelity** | Stated in the source at the cited slide; source's terms and hedges kept; nothing imported from general knowledge; not a pasted paragraph | Unsupported, wrong slide, hedge lost or strengthened |
| **A6 Exam value** | Directly helps answer an exam question; tier matches (objective-linked → tier 1; nothing tier 1 that maps to no objective) | Trivia at tier 1–2; objective content at tier 3 |
| **A7 Note type** | Cloze default; IO for labelled figures; Basic only when justified; no MCQ, list or essay cards | Wrong type |
| **A8 Cloze structure** | 2–3 clozes norm, ≤5 except enumerations; shared numbers for one answer; both sides of a relationship clozed where both are tested; direction blanks hinted `increases/decreases`; consistent hint vocabulary | Structural defect that changes what is tested |
| **A9 Formatting** | Bold the main subject only, outside the cloze braces; underline sparingly and never filler; italics for source emphasis; sub/sup; disease bold, abbreviation not; no trailing full stop; sentence-case capitals; units present | Polish only, never a blocker |
| **A10 Extra** | Front answerable without it; ≤3 lines joined by `<br>`; why → mnemonic/look-alike → citation → vault; nothing the source didn't give; capitalised; `- ` lines when 2+ | Front depends on Extra, or Extra carries a second fact |
| **A11 Images & occlusion** | Reveal placement correct; each mask covers exactly one label and nothing else; repeated labels share an index; titles, leader lines or legends don't leak; image actually inspected | Leaking or mis-covering mask |
| **A12 Tags, deck & note type** | Source, tier, subject (and system where it applies) tags present, correctly spelled, all under `#ColdRecall::`; written with `ColdRecall Cloze` | Missing source or tier tag; a tag in another deck's tree |
| **A13 One-by-one** | Only for ordered recall (mnemonic or sequence), never a plain 2–3 cloze note | Misapplied |

### Rubric — the maintainer, the set

| Code | Check |
|---|---|
| **S1 Duplication** | The same fact carded twice — inside the batch, against the existing deck, or against an AnKing note (which should be **unsuspended instead**). Name both note ids |
| **S2 Interference** | Near-twin cards that will produce "it's one of these two": the discriminator must be visible and underlined on each, or the pair merged into one compare note |
| **S3 Consistency** | The same term spelled, capitalised and formatted the same everywhere (British vs American spelling follows the source); same hint vocabulary; same units; same bolding of the same subject |
| **S4 Both directions** | Relationships the exam tests both ways are clozed both ways; a syndrome or triad has a forward and a reverse note |
| **S5 Families complete** | An enumeration has every member, in source order, one deletion each; a compare/contrast covers every axis the source gives; no orphan member carded without its set |
| **S6 Grouping** | Facts that belong together sit on one note as siblings; one note doesn't carry two unrelated facts; a fact split across notes isn't half-answered by the other |
| **S7 Coverage** | Every stated objective has tier-1 cards; any tier-1/2 content in the source with no card |
| **S8 Tier shape** | Tier distribution and the tier-3 share (under ~5% on a BUILD means the tiers have flattened) |
| **S9 Order** | Anatomy is base-first — flag muscle or nerve cards for a region whose bones and joints have no cards |

### Report format — the maintainer

```
VERDICT: PASS | PASS_WITH_FIXES | FAIL
NOTES:
- n017 | FIX | A3 blocker: "an {{c1::artery}}" — article leaks vowel → "a(n)"
       | rewrite: <full corrected Text> | extra: <corrected Extra or "unchanged">
- n018 | REJECT | A6: aside on slide 9, maps to no objective, not exam-facing
- n019 | PASS
SET:
- S2 | n021 ↔ n034 | loop vs thiazide calcium — discriminator not visible on n034 | fix: <…>
- S1 | n040 duplicates AnKing nid 1234567890 → unsuspend that note instead
STATS: notes N · pass P · fix F · reject R · blockers B · tier mix 1/2/3 · tier-3 share x%
```

`FAIL` = any blocker, or a set finding that needs re-extraction (sections
missing, wholesale drift). Polish-only findings are `PASS_WITH_FIXES`.

### Student — what it gets, and what it doesn't

**Only the contact sheets** (`renders/sheets.json`, plus occlusion previews) and
the brief below, plus its own rubric and report format. It gets no drafts, no
source, no maintainer rubric and no HTML. It
judges what a student actually sees, not what the author meant. It must be able
to open images (`subagent_type: general-purpose`). For more than 5 sheet
pairs (about 40 notes), give it a representative half (every group, every note
type, all of tier 1), not every sheet.

### Student brief (pass it verbatim, filling the path)

> You are a second-year medical student doing your daily Anki reviews, about
> 300 cards, mostly on your phone, often tired. You use the AnKing decks every
> day and know what a clean card feels like. `<renders/sheets.json>` lists
> contact sheets of new cards about to go into your deck, at phone width. Each
> pair covers the same notes: a FRONTS sheet (one tile per card, labelled
> note_cN) and a BACKS sheet (one tile per note, every blank revealed). Study
> them for real. For each pair: open the FRONTS sheet and, before opening
> anything else, write for every tile the answer you would give (or "don't
> know"). Then open the BACKS sheet and say for each card whether your answer
> would count, whether another answer would also have fitted, and how it felt
> to use. Open each sheet once; don't re-open images.
> Judge how the cards look and how they are to use, not the medicine. Then look
> at the batch as a whole. Every finding names the tile label and what you see
> in it. Return only the report format below.

### Rubric — the student

| Code | Check | Blocker when… |
|---|---|---|
| **V1 Question clear** | Within ~3 seconds of seeing the front you know what is being asked; your eye lands on the blank or the main subject first | You can't tell what's being asked |
| **V2 Honest attempt** | Your committed answer vs the back: right, a defensible alternative, or unknowable from the front | A defensible alternative answer (send to the maintainer as A2) |
| **V3 Answer pops** | On the back, the revealed answer is the first thing you see; nothing else competes in colour or weight | The answer looks like the surrounding text |
| **V4 Extra scans** | Extra reads in ~5 seconds: separate short lines, the citation clearly last, nothing you'd skip | A wall of text, or lines run together |
| **V5 Visual calm** | No colour or emphasis overload: few underlines, no rainbow of bold/italic/underline, nothing harsh on the eye at 6 am | Harsh enough that you'd edit it mid-review |
| **V6 Rendering faults** | No raw HTML or entities (`&amp;`, `<br>` showing), broken sub/superscripts, collapsed lines, overflow, images too small to read, tables wider than the phone | Any visible fault |
| **V7 Phone fit** | The front fits one phone screen without scrolling; no awkward one-word wrap lines; hints short | Front needs scrolling |
| **V8 Fatigue** | Would you dread seeing this card for the 50th time? Too long, too much to read, too much effort for one fact | — (polish) |
| **V9 Batch look** | The cards share one visual grammar (same emphasis habits, similar length); sister cards of one note feel like a family | — (polish) |

Remember that real Anki adds what the render can't: the AMBOSS add-on's teal
underlines on medical terms. Treat every underline you see as one more on top
of those.

### Report format — the student

```
VERDICT: PASS | PASS_WITH_FIXES | FAIL
CARDS:
- n017_c2 | ATTEMPT "tryptophan" → right | V3 blocker: revealed answer is purple like the other three names; can't spot it
- n022_c1 | ATTEMPT "don't know" → front gives no hook | V1 blocker: "[...] are seen in it" — asking what?
- n030_c1 | PASS
BATCH:
- V9 | n040–n048 underline every adjective; the rest underline nothing
STATS: cards N · attempts right R · alternatives A · blockers B
```

### Step 3 — Merge, fix, re-render

1. **Merge the two reports by note.** Both reviewers flagging the same note is
   strong evidence. A student V2 alternative answer is a maintainer-grade A2
   blocker. A student finding the maintainer called fine still stands: it's
   what the card *looks like*, which the maintainer never saw.
2. **Apply every blocker fix and every rejection.** Decline a fix only with a
   concrete reason (the reviewer misread the source — cite the slide; the
   student misjudged a render — show the screenshot), and put that in the
   report to the user.
3. **Apply polish fixes** unless they conflict with the deck's existing
   convention.
   When the two reviewers pull opposite ways, which is usually underlines
   (the maintainer wants a discriminator, the student counts AMBOSS
   look-alikes), keep **one** underline on the true discriminator and move
   other emphasis into the visible wording.
   Layout faults the student finds on many cards (edges, wrapping, alignment)
   are fixed once in the note type's CSS with `update_model_styling`, and
   mirrored into `model/style.css` and `assets/coldrecall-cloze/style.css`, not card by card.
4. **Re-render and re-review only what changed** (`--only`), plus the set
   checks for any group you touched. If round 1 left ≤ 8 notes changed, round 2
   is your own two-pass self-review on the new sheets, with no agents. At most **two rounds.** A blocker still open after round
   two: drop the note, or write it suspended tagged
   `#ColdRecall::!Flags::Review_unresolved`, and say which.
5. A `FAIL` for missing sections or systematic drift sends you back to Phase 1,
   not to patching.

If a reviewer agent dies mid-run (network drop, timeout), relaunch it once
with the same brief; that doesn't count as a round.

### Post-write spot check (BUILD; optional for HARVEST)

The renderer imitates Anki's template engine. After writing, check what Anki
itself produced:

1. Pick 3 cards: the longest, one with an image or table, and one tier-1 card.
2. Run `present_card` with `show_answer: true` on each and write `{id,
   question, answer}` to `cards.jsonl` with a script; don't echo the HTML.
3. Run `render_cards.py --anki-html cards.jsonl --model-dir model --out
   renders/post`.
4. Look at the resulting sheet yourself. If `present_card`'s HTML has the same
   structure as the renderer's (`span.cloze`, `span.cloze-inactive`,
   `hr#answer`, `div#extra`), comparing the HTML is enough.

If computer use is available and the user wants it, a screenshot of the real
Anki preview (Browse → the card → Preview) is the only way to see the add-ons
as they render. Fix any difference from the pre-write render with
`update_note_fields`.

### No subagent available?

Also the default for small batches (see **Token budget**). Do two genuinely
separate passes:

1. **Content:** clear your head of the drafting, open `drafts.jsonl`, the
   source and `existing.jsonl` fresh, and walk the maintainer rubric note by
   note, then the set.
2. **Look and use:** open the fronts sheet, commit an answer for every tile,
   then open the backs sheet, and walk the student rubric.

Produce the same reports, and say in the final report that the review was a
self-review, not independent.

---

## Job 1 — BUILD a deck from source material

Five phases, in order. Don't skip VERIFY or REVIEW: unverified extraction and
unreviewed authoring are where card quality dies. One lecture per chat — a dense
lecture is a lot of work, and on a paid plan it is a lot of usage.

### Phase 1 — EXTRACT

Read the source **completely** before writing anything. Never card from a
summary of it.

Build an inventory. For each testable item record: the claim **in the source's
own wording**, where it is (slide/page — count pages, don't infer them: two
consecutive slides with the same title and figure read as one and silently shift
every later citation), the objective it serves, and a tier.

| Tier | Meaning | Signals |
|---|---|---|
| **1 — must-know** | Near-certain to be examined | A stated learning objective; "high-yield", "will be examined", "remember"; bolded, boxed or repeated; summary slides; past papers |
| **2 — likely** | Standard examinable content | Body content supporting an objective; labelled diagrams; definitions, values, classifications, mechanisms-as-fact |
| **3 — completeness** | Real but peripheral | Asides, extended detail, background, worked examples |

Volume is **coverage-driven, no cap** — a dense lecture can yield 150+ cards.
The tiers do the pruning. **Tier 3 is written suspended**: the cards exist and
are searchable, but stay out of reviews until the user unsuspends them.

**Carding ahead of the lecture?** If the user hasn't been taught this yet,
write *everything* suspended and give them the one search to run once it's
taught — `tag:#ColdRecall::#Source::<…> -tag:#ColdRecall::!Tier::3` → select all
→ Unsuspend. That is the AnKing workflow: build ahead, unsuspend as you go.

Write the inventory to a manifest file in your working directory (never in the
vault) before authoring. Don't go straight from reading to `add_notes`.

### Phase 2 — VERIFY the manifest (independent)

This checks *content* — is the inventory right? (Phase 4 checks the *cards*.)
If you can start an independent subagent, do — give it the manifest and the
original source, not your reasoning. If you can't, re-read the source from the
start, section by section, checking each manifest item against it rather than
against your memory of it. It checks, per item:

1. **Supported?** Actually stated in the source, at the cited location? Flag
   anything imported from general knowledge and any citation pointing at the
   wrong slide.
2. **Complete?** Scanning the source independently, what tier-1/2 content is
   missing? Content the manifest's own header mentions but never cards counts.
3. **Faithful?** Has anything drifted in meaning, scope or hedging?
4. **Correctly tiered?** Every stated learning objective has tier-1 items
   covering it — an objective that says "Enumerate X" whose enumeration sits at
   tier 2 is a defect. Nothing is tier 1 that maps to no objective (clinical
   asides are the usual offenders). Report the tier-3 share: **under ~5%** means
   the tiers have flattened and the suspension protects nothing.
   *Measured failure:* on a real lecture whose objective was "Enumerate
   membranous & non-membranous organelles", those cards landed at tier 2 while
   non-objective clinical signs landed at tier 1, and 1 of 101 cards was
   suspended. Content accuracy was perfect — only the tiering broke.
5. **Figures:** are the labels claimed for each figure actually on it, and does
   any label appear more than once?

Repair every flagged item. If the problem is systematic (sections missed,
wholesale drift), redo Phase 1 rather than patching.

### Phase 3 — DRAFT

1. **Reconcile first, never duplicate.** `find_notes` on the deck and the source
   tag (and legacy tags), and search AnKing for the same concepts. Dump what you
   find to `existing.jsonl`. An existing own note is updated with
   `update_note_fields`, not re-added; an AnKing match becomes an unsuspend
   proposal, not a new note. Re-running over the same lecture must not multiply
   cards.
2. **Deck and tags** from `deck_name.py`; `list_decks`.
3. **Draft every text note** into `drafts.jsonl` in the house style, with its
   `group`, `tier`, `objective` and `source_ref`, on `ColdRecall Cloze` (create
   it from `assets/coldrecall-cloze/` if `model_names` doesn't list it).
4. **Draft the occlusions.** Enumerate every candidate figure first: list each
   labelled figure with its slide, its labels and the objective it serves, then
   say which you'll occlude and why you're skipping the rest. Rank by objective
   coverage, not by how clean the figure looks — on a real lecture the tidy
   membrane diagram got occluded while the richer slide-7 organelle diagram, the
   direct visual for two objectives, was skipped. Then follow
   `references/image-occlusion.md` up to (not including) storing media:

   ```bash
   python3 scripts/extract_figures.py LECTURE.pdf --pages 7,10 --out ./figs     # re-render at 4x
   python3 scripts/ocr_regions.py figs/p10_fig1.png --json r.json --preview p.png
   # LOOK at p.png — missing labels, surviving junk, boxes beside rather than on text
   python3 scripts/build_occlusion.py --in r.json --keep 1,2,3 --preview figs/p10_fig1.png
   ```

   Repeated labels share one cloze index (the script does this); a label OCR
   missed is estimated by eye and the note tagged `IO_estimated`. **Never
   occlude an image you haven't looked at.** Add each occlusion to
   `drafts.jsonl` with its image, preview and masks.

### Phase 4 — RENDER & REVIEW

Run **The review panel** on the whole draft set: render and lint, fix the lint,
send the maintainer and the student out in parallel, merge, fix and re-render
(up to two rounds). Nothing is written until both verdicts are `PASS` or
`PASS_WITH_FIXES`, with every blocker resolved, dropped or flagged.

### Phase 5 — WRITE

1. `create_deck` only if genuinely absent.
2. **Write** with `add_notes`, batched per note type (≤100 per call); updates
   with `update_note_fields`; occlusion media with `store_media_file` per
   `references/image-occlusion.md`. Every note carries its source tag, its tier
   tag, and subject/system tags where they apply.
3. **Suspend tier 3** and any `Review_unresolved` notes:
   `find_notes "tag:#ColdRecall::!Tier::3 tag:<source tag>"` → `notes_info` for
   the card ids → `card_management` action `suspend`.
4. **Check:** `find_notes "tag:<source tag> -tag:#ColdRecall::!Tier::3 -tag:#ColdRecall::!Flags::Review_unresolved is:suspended"`
   must return nothing (unless everything was deliberately suspended for
   carding ahead). Spot-check three written notes with `notes_info` against
   `drafts.jsonl`, so that what's in Anki is what passed review.
5. **Post-write spot check** (see The review panel): render three cards from
   Anki's own HTML and look at them.

### Report

Plainly: cards added per note type and per tier, which deck, how many were
updated rather than created, how many AnKing notes are proposed for unsuspending
instead, how many tier-3 cards are suspended, the tier-3 share, figures occluded
and skipped, anything deliberately not carded — and the review: rounds run,
notes fixed / rejected, set findings fixed, any `Review_unresolved`, any fix you
declined and why, whether the review was independent, the student's attempt
score (right / alternatives), the subagent token totals if the tool reports
them, and one backs sheet so the user sees what they're getting.
Then the one search that shows them all: `tag:<source tag>`.

---

## Job 2 — HARVEST at the end of a study session

Called by the `learning` skill at commit, with the atoms it noticed while
teaching.

1. **Test each** against the stricter HARVEST bar above. Drop anything the
   learner can now derive — it lives in the vault note just written. Zero atoms
   is a normal, correct result; never card to fill a quota.
2. **Reconcile** with `find_notes` on the text and the subject/source tags, and
   search AnKing; skip anything already carded, and propose unsuspending an
   AnKing match rather than writing a new note.
3. **Draft** in the house style, checked against the source text read this
   session — no fact from general knowledge the source didn't state.
4. **Render & review.** Run **The review panel** on the drafts, with
   `existing.jsonl` holding the subject's existing notes on the same topic so
   interference and duplication against the deck are caught. Apply the fixes.
   In propose-first mode, show the user the backs sheet alongside the text.
5. **Deck:** the lecture's deck if the session was on a named lecture; otherwise
   `<Subject>::<Topic>` (two levels).
6. **Tags:** `#ColdRecall::!Session::<today>`, the tier (1 or 2 — harvest never
   produces tier 3), the subject tag, and the source tag when there is one.
7. **Create and report in one line**, with the atoms named so they can be pruned:
   *"Carded 4 to Renal::Terminology (reviewed, 1 fixed) — nephr-, -uria,
   -lithiasis, oliguria. Say the word to prune."* If the user said **"propose
   first"** (or the project sets it), list the reviewed drafts and wait.

---

## Job 3 — READ state and REPAIR failing cards

### Read-back (at the start of a study session)

Scope it to **today's subject**. Old debt from other subjects is not today's
problem, and surfacing it derails the session.

1. `cards_stats(deck)` for today's subject deck → count `dueToday`, and collect
   card ids (filter by tag if the deck is shared).
2. `get_card_memory_state` on those cards (in chunks) → anything with
   **retrievability below ~0.85** is weak: earned, decaying "you don't know this
   right now".
3. Report: due today in this subject, and up to five weak atoms by name
   (`notes_info` with `excerpt_chars`). Other subjects get **at most one line**
   (`list_decks` with `include_stats` — "32 cards due across other decks, do them
   in the Anki app"), never drilled.

### Reviewing

Routine reps happen **in the Anki app** — it's faster and purpose-built. In chat,
Claude runs cards (`get_due_cards` → `present_card` → `rate_card`, graded
honestly so FSRS stays true) only for:

- **Interleaving:** a handful of atoms linked to today's topic, cold, before new
  material.
- **Targeted weak-card quizzing,** when the user asks for it.

Never bulk-grind a due queue through chat.

### Repair

A card that keeps failing (`find_notes "tag:leech"`, or persistently low
retrievability) is usually a bad card, not a bad memory.

1. **Diagnose against the panel's rubrics** — ambiguous blank (A2), list in a
   blank (A1), interference with a near-twin (S2), missing context, a leak (A3),
   an answer that doesn't stand out or an unreadable back (V3, V4).
   Pull its siblings and any near-twins into `existing.jsonl`.
2. **Rewrite** the fix into `drafts.jsonl`, and **give it a hook** Anki can't
   supply in Extra: etymology (`-ectomy` ← Greek *ek-tomē*, "a cutting
   out"), the mechanism in a phrase, or a contrast with a look-alike.
3. **Render & review** the rewrite with **The review panel**, then apply with
   `update_note_fields`; split with `add_notes` + `delete_notes`. A leech is
   often a *visual* failure (answer doesn't stand out, a wall of Extra), so
   render the current card too, not just the rewrite.
4. **Graduate it** if the hook makes the fact derivable: promote it to the vault
   as a concept (via the `learning` skill's reconcile rules) and suspend the card.
5. Remove the `leech` tag after fixing. Don't reset a card's history
   (`forget_cards`) unless the user asks.

### Remake a deck (repair at scale)

"Remake the cards in deck X in the new style" runs the review panel over
rewrites of every note:

1. `notes_info` every note. The originals are the content source if the
   textbook can't be opened: say so, and have the maintainer flag what it
   can't verify.
2. Drop what isn't from the source (clinical pearls the originals added) and
   anything an AnKing note already covers (propose unsuspending that note).
3. Write the new notes on `ColdRecall Cloze`. **Suspend** the old notes and tag
   them `#ColdRecall::!Flags::Replaced_<date>`; don't delete them. Give the
   user the one search to delete them once they're happy.

Occasionally, with enough review history and the user's agreement,
`optimize_fsrs_params`; `set_fsrs_params` to raise desired retention on a
high-stakes deck (default 0.90).

---

## Optional: trim the tool list

The add-on exposes ~40 tools and each costs context on every message. In Anki:
**Tools → Add-ons → AnkiMCP Server → Config**, set:

```json
"disabled_tools": [
  "gui_browse", "gui_add_cards", "gui_edit_note", "gui_current_card",
  "gui_show_question", "gui_show_answer", "gui_select_card",
  "gui_deck_browser", "gui_undo",
  "update_model_templates", "model_fields",
  "delete_media_file",
  "card_management:reposition", "card_management:bury",
  "card_management:unbury", "card_management:forget_cards"
]
```

Keep `store_media_file` (image occlusion needs it), `card_management` suspend
and unsuspend, `tag_management`, `cards_stats` and the FSRS tools. Also keep
`model_templates`, `model_styling` and `present_card` (the renderer needs
them), and `create_model` and `update_model_styling` (the ColdRecall note
type).

---

## Fallback: import file

When the Anki tools aren't reachable, a BUILD can still finish — after RENDER & REVIEW
(render with the saved `model/` files, or with `assets/coldrecall-cloze/`):
write the reviewed notes to a UTF-8 `.txt` file the user imports with
**File → Import** in Anki. Put these header lines first so Anki needs no
configuration:

```
#separator:tab
#html:true
#notetype:ColdRecall Cloze
#deck:MED241::3. Cell organelles
#tags column:3
```

Then one note per line: `Text<TAB>Extra<TAB>space-separated tags`. If the note type
doesn't exist on that computer yet, create it first (see **Setting up the note type**). Tier-3
notes can't be suspended by the file — tell the user the search to suspend
them after import (`tag:#ColdRecall::!Tier::3` → select all → Suspend).

---

## Do NOT

- Write, propose or import any card the review panel hasn't passed, or give
  the maintainer your reasoning instead of the drafts and the source, or give
  the student anything but the contact sheets.
- Send cards to review without rendering them and looking at the first sheets yourself.
- Give the student individual screenshots instead of contact sheets, re-send
  unchanged notes in round 2, or launch agents for a batch of 8 notes or fewer.
- Put `<b>` inside cloze braces, separate Extra lines with raw newlines,
  underline filler words, or tag into another deck's tag tree.
- Write own cards with plain `Cloze` or an AnKing deck's note type, rather than
  `ColdRecall Cloze`.
- Ignore a reviewer blocker without a cited reason, or run more than two review
  rounds instead of dropping or flagging.
- Skip VERIFY on a BUILD, or card from a summary instead of the source.
- Paraphrase the source into generic textbook voice, drop its hedges, or paste
  its paragraphs verbatim.
- Make list cards, comma-list deletions, filler-word blanks, or essay cards.
- Default to Basic, or make reversed cards where a two-sided cloze does the job.
- End a card with a full stop, Title-Case ordinary words, or bold every noun.
- Write a new note for a fact an AnKing note already covers — propose
  unsuspending that note.
- Write tier 3 unsuspended without saying so, or let tier 3 fall under ~5% of a
  BUILD without checking the tiering.
- Duplicate a card on a re-run — reconcile first, legacy tags included.
- Invent a deck name, ask for one the filename gives, or create a deck without
  checking `list_decks`.
- Pass note ids where card ids are needed (suspend, memory state).
- Occlude an image you haven't looked at, trust OCR as complete, OCR the embedded
  PDF image directly, or give repeated labels separate cloze indices.
- Occlude the first good figure and stop — enumerate them all first.
- Surface other subjects' review debt beyond one line, or bulk-grind reviews in chat.
- Create any note type other than ColdRecall Cloze, or write into a shared deck's note types.
- Claim cards were made when the Anki tools failed.


---

## Setting up the note type

When `model_names` doesn't list `ColdRecall Cloze`, create it with
`create_model`:
- `model_name: "ColdRecall Cloze"`
- `is_cloze: true`
- `in_order_fields: ["Text", "Extra"]`
- one template named `Cloze`, whose Front and Back are the contents of
  `assets/coldrecall-cloze/front.html` and `back.html`
- `css`: the contents of `assets/coldrecall-cloze/style.css`

The warning that `{{#Extra}}` isn't a field is a false positive. To change the
look later, use `update_model_styling` in patch mode, then update
`assets/coldrecall-cloze/style.css` to match, and re-render a few cards before
and after.

## Running in Claude Code

- **Source files:** read lectures directly from
  `~/Library/CloudStorage/GoogleDrive-<account>/<lecture folder>/`. A
  cloud-only file needs "Make available offline" in Finder first.
- **Anki tools** appear as `mcp__anki__*` once the AnkiMCP server is added to
  Claude Code (see `INSTALL.md`).
- **Working files** (manifest, `drafts.jsonl`, `model/`, `renders/`) go in a
  scratch folder such as `/tmp/anki-<lecture-id>/`, never in the vault or the
  lecture folder.
- **Reviewers** are `Agent` calls with `subagent_type: general-purpose`; launch
  both in one message so they run in parallel.
