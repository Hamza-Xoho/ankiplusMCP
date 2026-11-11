# Architecture and design rationale

This document is for people who want to change Lecture2Cards or judge whether
its design is sound. For using it, read the [README](../README.md).

## 1. The idea in one paragraph

Making good cards is two kinds of work. Most of it is mechanical: reading PDFs,
OCR, slide maps, rendering previews, checking cloze syntax, hashing files,
enforcing gates, and writing batch files. A model is slow and expensive at that
and is unreliable at it. The rest is judgement: choosing what a card should ask,
spotting a leaked answer, and deciding whether a fact is in the lecture. The
design splits the work along that line. A small, deterministic CLI (`cards`)
does the mechanical work and enforces the rules. An agent skill (`/ankiv2`)
does the judgement work and only ever sees what the CLI hands it. Two
independent reviewer agents check the drafts before anything is written.

An earlier version put everything in one long agent session. A single 24-slide
lecture used 76 model calls, re-read about 12M tokens, and hit the plan's usage
limit before the cards were written. Most of that cost was mechanical work the
agent repeated. That is the main reason for the split.

## 2. Pipeline

```
lecture PDF
   │
   ├─ state init ──────────► builds/<date>_<course-lecture>/build.json   (P0)
   ├─ extract ────────────► source/ (text, slides, objectives, figures, slide map)
   ├─ target ─────────────► target.json (course, lecture, deck name, tags)
   │
   │   ── agent drafts ──► drafts.jsonl, skipped.jsonl                  (P2)
   │
   ├─ check ──────────────► checks/check.json (schema, lint, coverage)  (P3)
   ├─ render ─────────────► renders/ (cloze HTML → PNG sheets)
   ├─ figures (optional) ─► occlusion masks for labelled figures
   │
   ├─ packets ────────────► review/round N/{maintainer,student}/  (P4)
   │   ── two reviewer agents, each reads only its PROMPT.md ──► *_report.jsonl
   ├─ apply ──────────────► validated rewrites, conflicts, apply_log.json
   │   (at most 2 rounds)
   │
   ├─ gate ───────────────► gate.json, passed/failed, pinned to drafts hash (P5)
   ├─ write ──────────────► write/batches/*.json, expected.json       (P6)
   │   ── agent calls the Anki MCP tools, records receipts ──► Anki
   ├─ state record-write ─► build.json.write (counts from receipts only)
   └─ report ─────────────► report.md                                  (P7)
```

The CLI never talks to Anki. `cards write` produces payloads. The agent sends
them through the Anki MCP tools (`add_notes`, `update_note_fields`,
`card_suspend`, `find_notes`, `notes_info`) and records what came back. There is
no direct-write code path in the CLI, so the CLI has no network dependency.

## 3. Repository map

| Path | What it is |
|---|---|
| `src/cards/cli.py`, `common/dispatch.py` | Argument parsing and dispatch. Holds no logic. |
| `src/cards/common/` | Shared helpers: paths (with traversal and symlink refusal), atomic file writes with provenance headers, hashing, output formatting, errors, token estimate. Imports nothing else from `cards`. |
| `src/cards/state.py` | Build creation, facts, phase transitions, resume rules, merged-source refusal. |
| `src/cards/extract/` | PDF text and layout (PyMuPDF), OCR (Tesseract), figure detection, objectives, slide map generation. |
| `src/cards/source.py`, `source_data` | Slice and grep access to the extracted source, so agents read pieces, not the whole lecture. |
| `src/cards/target.py` | Course, lecture and deck identity. Filename parsing and manual overrides. |
| `src/cards/check/` | Schema checks (C01–C05: coverage, figures without occlusion or a recorded decision) and lint (L01–L13: cloze numbering, HTML, length, underline and hint rules). |
| `src/cards/render/` | Cloze HTML from the shipped note type, occlusion bodies, contact sheets (Playwright Chromium). |
| `src/cards/figures.py` | Image-occlusion records and previews. |
| `src/cards/review/packets.py` | Builds the reviewer packets: allowlisted inputs, prompts, image manifests, section splits. |
| `src/cards/review/apply.py` | Validates both reports, applies rewrites, writes the audit log. |
| `src/cards/gate.py` | The automatic gate. |
| `src/cards/write/` | Write plan, batch files, import-file emitter. |
| `src/cards/report.py`, `meter/` | Final report, and the usage meter that reads Claude Code transcripts. |
| `src/cards/templates/review/` | Reviewer briefs, rubrics, report formats, house style (packaged). |
| `src/cards/assets/coldrecall-cloze/` | The ColdRecall Cloze note type (packaged). |
| `.claude/skills/anki2/` | The skill source: `SKILL.md` (core rules and the phase table), `phases/*.md` (loaded per phase). |
| `.claude/agents/anki-*.md` | The two reviewer agent definitions. |
| `scripts/package_ankiv2.py` | Builds and installs the public skill and agents for Claude Code and OpenCode. |
| `tests/unit/`, `tests/contract/` | Tests. See section 10. |
| `docs/` | Requirements, design spec, test contract, phase history and decisions. |

Dependency direction is documented in [`design-spec.md`](design-spec.md) §2.
`common` depends on nothing. Feature modules depend on `common` and on each
other only through the documented outputs (files), not through imports of
internal state.

## 4. The build folder and the state machine

Each lecture gets one folder, `builds/<YYYY-MM-DD>_<course>-L<nnn>/`, under
`./builds` or `$CARDS_BUILDS`. Every artefact is a file in that folder, so a
build can be stopped at any point and resumed in a new session.

`build.json` holds:

- `source`: the PDF path and its SHA-256. Resuming with a different file is refused.
- `phase` and `history`: the current phase and every start and finish, with timestamps.
- `facts`: observed facts (Anki reachable, note type exists, deck exists). Only the
  documented keys can be set.
- `review`, `gate`, `write`: round number, gate status and drafts hash, and write counts.

Phases run in order: P0 preflight, P1 extract and target, P2 draft, P3 check and
render, P4 review, P5 gate, P6 write and verify, P7 report. The only backward
moves allowed are P4→P3 (for a second review round after rewrites) and P5→P4.
A phase cannot be skipped. P6 requires a passed gate in `build.json`.

Resume rules, in the skill: never replay extraction, `source --all`, or drafting
past P2. Reuse finished review reports and launch only missing reviewers. Never
resend a write batch that already succeeded. If a write's success is ambiguous,
stop and reconcile against Anki before retrying.

## 5. CLI contract

Every subcommand follows the same output rules, so an agent can read results
cheaply:

- Line 1 is `OK`, `FINDINGS` or `ERROR`.
- Then at most 40 lines and 2,000 characters.
- Then `→ <path>` lines for files written.
- Exit codes: `0` ok, `1` findings the agent must address, `2` error,
  `3` refused (a prerequisite is missing or an action is not allowed yet).
- Errors name the field and the remedy, for example
  `ERROR E10 …: line 1 field source is a multi-lecture or merged file — use one lecture PDF per build`.

Written artefacts start with a provenance comment
(`<!-- cards <tool> <version> <timestamp> -->`) so a reader can tell what made
a file. JSON artefacts carry the same information in `_meta`.

Refusals are errors, never silent. A flag or environment variable cannot skip a
check. The gate and write commands have no bypass.

## 6. Source extraction and the slide map

`cards extract` reads the PDF once. Text comes from PyMuPDF. Where a page has
little or no text layer, Tesseract OCR fills the gap. Figures are detected, and
any figure with several text labels is flagged for image occlusion. The result
is `source/slides.json` plus a one-line-per-slide `source/map.md`.

The skill reads the map, then pulls only the slides it needs with
`cards source --slides N` or `--grep`. This keeps a full lecture out of the
model's context. Flagged slides that need a look get a page image
(`--page-image N`), and only those images are opened.

Cold extraction is the slow step, and OCR dominates it. OCR runs on a thread
pool (one worker per core by default). The MCP server also passes an OCR cache
that remembers results by image content, so a repeat run there skips OCR. The
`cards` CLI passes no cache, so each CLI run does its OCR again. Measured on a synthetic 12-page PDF with one 1400x900
labelled figure per page (8 cores, Tesseract 5.5.4): rendering takes 0.08 s per
figure; OCR takes 13.9 s per figure on one worker; a cold `extract_source` takes
52.4 s; a repeat into a new folder with the same cache takes 1.2 s. These
numbers are synthetic. `tests/tools/time_extract.py` reproduces them. An
earlier document gave 220 s for cold extraction of one fixture, measured before
these changes. That fixture has not been re-measured, and the two numbers are
not comparable.

In the MCP server the text comes first and the figure labels follow. When every
slide is read and every figure crop is saved, and before OCR starts, the core
writes an early `map.md` and `slides_summary.json`. In them every figure says
"labels pending". The job's progress then names the map's path and says it is
readable now. Until OCR ends:

- `read_source`, `search_source` and `get_page_image` work as usual.
- `read_artifact` reads the early map at the same path the finished job
  returns, and adds `labels_pending: true`.
- `list_figures` and `get_figure` return each figure with `ocr_labels: null`
  (not yet read, unlike `[]`, read and none found) and `labels_pending: true`.
  Crops are readable.
- `check_cards` with `coverage` refuses with `LABELS_PENDING` and names the
  job. It needs the finished extraction. Retry when the job completes.

When OCR ends the final map and summary replace the early ones, and they are
the same files the CLI writes. A published extraction always wins over the
early text. The early text is used only while its job is queued or running.
The CLI writes no early map.

The `cards` core is callable through typed functions such as
`cards.extract.extract_source` and `cards.extract.ocr_figures`. The MCP server
calls these directly. It does not build argument objects or write `build.json`
to reach the core. The one exception is `measure_usage` in `sources.py`, which
still builds an argument object and leaves the MCP in a later piece.

## 7. Drafting and checking

The drafting step is judgement, so it lives in the skill (`phases/draft.md`).
The rules it follows are the house rules: cloze from the lecture's own terms,
hedges and scope preserved, no general-knowledge additions, one relationship
per card, a tier (1 core, 2 supporting, 3 detail) for each note, and a
`source_ref` back to the slide. Drafts go into `drafts.jsonl` in one write, not
note by note, because per-note edits were the most expensive pattern in the
first version.

`cards check` then enforces what can be checked mechanically: schema fields,
unique ids, a valid tier, coverage of every learning objective, and lint rules
for the note-type (cloze numbering, allowed tags, length limits, underline and
hint rules). Blockers stop the build. Findings are short and point to the note.

## 8. Review design

This is the part most worth scrutinising.

**Two reviewers, different jobs.**

- The *maintainer* is an AnKing-style deck maintainer. It reads the drafts, the
  source slices for the cited slides, the objectives, the house style, and the
  reconcile list of existing notes. It checks fidelity to the source, duplication
  against existing notes (proposing an unsuspend instead of a duplicate), and
  style rules A1–A13 per note and S1–S9 across the set.
- The *student* sees only rendered contact sheets and previews, never the text
  sources, drafts or rationale. It judges whether a card is answerable and clear
  as a learner would see it (V1–V9). Keeping it text-blind is deliberate: a
  reviewer that can read the source will mark a card right because it knows the
  answer.

**Packets are allowlists.** `cards packets` copies only the files a reviewer
needs into its folder. A test asserts the allowlist, and asserts that the student
folder has no `.html` or `.jsonl` files. Author reasoning is never written to a
packet, so reviewers judge the card and not the author's intent.

**Prompts are small by design.** Each `PROMPT.md` must fit in 300 estimated
tokens (`ceil(characters / 4)`), checked in code (E60 if not). Image paths are
never listed in the prompt. The packet writes a manifest (`pages/images.md`) and
the prompt names the manifest. That fixed a real failure: a 98-slide merged
source produced an 80-image prompt that overflowed the budget.

**Large sets are split.** Over 80 notes, the maintainer work is split into
section packets, each with its own slices and images. Set-level rules run once
over the whole set.

**Two rounds at most.** Round 1 is the full review. Round 2 is scoped to the
notes that changed, and only if the changes are large enough to warrant it. After
round 2, unresolved findings go to the gate as they are.

**Apply is strict.** `cards apply` validates both reports before it changes any
draft. Malformed records exit 2 and name the reviewer and line. Reports that
disagree on the same note produce a conflict, and that note is left unchanged. A
rewrite that would introduce a lint blocker is not applied and goes to the next
round. Every decision is written to `apply_log.json`.

## 9. Gate and write safety

**The gate is fail-closed.** `cards gate` passes only if all of these hold:

- the latest round's reports exist, both have a single closing verdict of `PASS` or `PASS_WITH_FIXES`;
- no report changed after it was applied (hashes compared);
- the drafts have not changed since review was applied;
- no open blocker remains, and no CSS fix is pending;
- `cards check` reports no schema or lint blocker.

It writes `gate.json` with the drafts SHA-256 and copies the status into
`build.json`.

**Write refuses if anything moved.** `cards write` requires a passed gate and
recomputes the drafts hash. Any edit after the gate makes the gate stale, and
write refuses with E71. Batches hold at most 100 notes, each batch has one deck
and one note type, and `expected.json` records what the write should produce.

**Counts come from receipts.** After the agent writes, `cards state record-write`
reads `write/receipts.json` (the ids Anki returned), refuses if any batch failed,
and records counts from those receipts, never from the plan. `cards report`
refuses if the counts do not reconcile.

**Only the agent writes.** Writes go through the Anki MCP tools. In Claude Code,
a PreToolUse hook in this repository blocks those tools until the gate passes.
That hook is not part of the packaged skill. In OpenCode, the skill's instructions
and `cards write`'s refusals are the only guard, so the packaged skill asks the
user to confirm the plan once.

**What the write never does.** It never deletes. It never edits a note except
an earlier card for the same lecture that the draft step identified by id. It
never unsuspends an existing AnKing note without an explicit request. A duplicate
that Anki refuses is listed as skipped.

## 10. Runtime adapters and packaging

The skill source is in `.claude/skills/anki2/` and uses the project's own paths
(`.venv/bin/cards`, the project's reviewer agents, and Claude Code's Task tool
names). `scripts/package_ankiv2.py` builds a portable copy named `ankiv2`:

- `.venv/bin/cards` becomes `cards` on `PATH`.
- Claude-specific model and effort pins are removed, so each host chooses its own.
- MCP tool references are described by suffix, with the prefix per runtime
  (`mcp__anki__X` in Claude Code, `tools.anki.X` or `anki_X` in OpenCode).
- Reviewer agents are emitted for each runtime. The OpenCode versions are
  subagents with edit limited to `**/review/**` and shell denied.

Reviewer templates and the note-type assets are vendored into
`src/cards/templates/` and `src/cards/assets/`, and packaged with the wheel, so
the CLI does not depend on the repository layout. Unit tests check that the
packaged copies match the skill copies.

## 11. Decisions and why

| Decision | Why | Trade-off |
|---|---|---|
| Deterministic CLI + judgement skill | Cuts model usage on mechanical work; makes rules testable. | Two things to install and keep in sync. |
| One lecture per build | Citations and deck identity are unambiguous. A merged PDF makes `slide 5` ambiguous and names the deck after the wrong slide. | Multi-lecture topics need separate builds for now. Planned provenance work would allow merged sources. |
| Flat deck named from slide 1, overridable | Matches the user's deck style. The override path is `cards target --course/--number/--title`, not hand edits. | Slide 1 is not always the topic. The override handles that. |
| No human approval before writing | Owner decision (D-5): a human check added a cache-expiring wait and was not used. The review verdict and gate replace it. | A bad card can reach Anki. The README asks students to skim decks. |
| Independent maintainer and student reviewers | Different failure modes: fidelity and duplication versus clarity and answerability. Text-blind student review avoids the reviewer marking answers right because it knows them. | Two agents cost more than one. Usage is the main cost. |
| Allowlisted packets, 300-token prompts, image manifests | Keeps reviewers independent, reproducible and cheap. | Packet code must be kept up to date when inputs change; tests guard it. |
| Two review rounds at most | Bounds cost and prevents endless rewriting. | Some issues reach the gate unresolved; the gate blocks them if they are blockers. |
| Fail-closed gate pinned to a hash | An edit after review cannot slip through unchecked. | Any edit after the gate means repeating review. |
| Receipts, not plans, drive counts | A partially failed write cannot be reported as complete. | Requires the agent to record receipts. |
| Propose unsuspends, not duplicates, for AnKing notes | Avoids doubling cards that already exist in shared decks. | Needs the reconcile search to find them; lecture-tag shapes such as `W4::4-Wed::L029` are searched explicitly. |
| Frozen contract tests | Requirements cannot be quietly weakened to make a change pass. | Changing a requirement means editing the docs and re-freezing by hand. |
| Vendored templates and assets | A wheel must work outside the checkout. | Two copies to keep in sync (a test does this). |

## 12. Testing

- **Unit tests** (`tests/unit/`): helpers, packets and allowlists, apply
  validation, packaging sync, state init, and the cases that produced past bugs.
- **Contract tests** (`tests/contract/`): one file per phase, named in
  [`test-contract.md`](test-contract.md). They run the real CLI. The files listed in
  `.codex/contract.sha256` are frozen: a test can only change by re-freezing it by
  hand, after the requirement changes in the docs.
- **Private fixtures**: tests that need a lecture PDF use files in
  `tests/fixtures/private/`, which is gitignored. With `CARDS_PUBLIC_CI=1` those
  tests skip. Otherwise a missing fixture fails the test.
- **CI** (`.github/workflows/ci.yml`): unit and contract tests, a wheel build,
  an install of the wheel in a clean virtualenv, an isolated `state init` smoke
  test, and a check that merged sources are refused.

## 13. Known gaps

These are recorded in [`decisions.md`](decisions.md) and are not hidden by the
tests.

- **Performance.** Cold extraction of a synthetic 12-page PDF takes 52.4 s on
  8 cores. This is the only data point. The 60-second target was set for a real
  lecture of about 60 slides and is untested on real lectures. The earlier 220 s
  figure was measured on one fixture before these changes; that fixture has not
  been re-measured, and the two numbers are not comparable. Label recall is
  unchanged by construction, because the OCR settings did not change.
- **Image occlusion.** Output quality has been checked on few lectures, and
  one earlier run produced no occlusion notes for a figure-heavy lecture. Check
  C05 now flags that case.
- **Reviewer failures.** An earlier run showed reviewers producing rewrites
  that violated lint, and packets run before their images existed. Both are
  now handled, but the failure mode is worth watching.
- **Single runtime guard.** Only Claude Code has hooks in this repository. The
  packaged skill relies on the CLI's refusals and on instructions elsewhere.
- **Config.** `cards.toml` is reserved for a later version. The defaults it
  would hold are pinned in code.
- **Scope.** HARVEST and REPAIR are not in this version. Codex is not supported.
- **Model pricing.** The usage meter needs prices for each model, which are
  not filled in for every model.

## 14. Glossary

- **Build**: one lecture's working folder and state.
- **Draft**: a proposed note, in `drafts.jsonl`, before review.
- **Tier**: 1 core, 2 supporting, 3 detail. Tier 3 is written suspended.
- **Packet**: the allowlisted folder a reviewer reads.
- **Round**: one pass of review plus apply. At most two.
- **Gate**: the automatic check that must pass before any write.
- **Receipt**: what Anki returned for a write batch.
- **Reconcile**: the search for existing notes on the same facts, so the tool
  proposes an unsuspend instead of a duplicate.
