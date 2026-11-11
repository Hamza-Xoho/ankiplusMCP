# Efficacy design (piece 3)

Status: approved by the owner on 2026-11-10, with every decision at the end
taken as recommended. Nothing here is built yet. Each sub-piece (3a to 3e)
gets its own plan, in order.

This is the third of five pieces of work. Pieces 1 and 2 (public repository,
npx launcher) shipped as 0.2.0. Piece 4 is skill unification and piece 5 is
registry publishing; neither is designed here.

## Intent

Make AnkiPlus MCP good enough to be left alone. Today it is a box of working
tools that a careful person can steer through a host that has a skill, hooks
and reviewer agents. The owner wants it used inside unattended agent systems:
a lecture file arrives from a chat archive, an agent notices it, and cards are
ready before anyone sits down.

For that to be safe and cheap, three things have to be true that are not true
today:

1. The cards that reach Anki are the cards that were checked, byte for byte.
2. The checks cannot be skipped by the agent doing the work, on any host.
3. The work costs few calls and few tokens, and can stop at "ready to write"
   when Anki is closed.

## What was measured

All of these were read in the code or measured on 2026-11-10.

- **Tools.** 33 tools; the schema is 29,599 characters, about 7,400 tokens,
  sent to the model in every session. `create_workspace` and `save_cards`
  each repeat the full card schema and are about 3,100 characters apiece,
  a fifth of the total between them.
- **Round trips.** Seeing one page or figure takes two or three calls
  (`get_page_image` or `list_figures` and `get_figure`, then `get_image`).
  OCR of one figure takes four (`ocr_image`, `get_job`, `read_artifact`,
  `get_image`). Extraction, OCR and rendering all need `get_job` polling.
  `save_cards` replaces the whole card set, so fixing one card resends all of
  them. Most edits need a `get_workspace` first only to learn the revision.
- **Cards pass through the model twice on the way out.** `prepare_write`
  writes batches of up to 100 notes. The agent reads each batch and types it
  again into the Anki MCP's `add_notes`, which takes notes inline and has no
  file input. For a 60-card lecture that is roughly 6,000 to 9,000 tokens in
  and the same out (an estimate from card sizes, not a measurement). The
  larger problem is that nothing compares the retyped copy with the checked
  one. Receipts are stored as `caller_supplied`.
- **The same happens on the way in.** Existing notes (`create_workspace` with
  up to 500 cards), note-type templates and CSS (`render_cards`, up to 110,000
  characters) and the deck list (`resolve_target`) are all read from the Anki
  MCP by the model and typed again into AnkiPlus.
- **Media does not have this problem.** The Anki MCP's `store_media_file`
  accepts a local path.
- **The method is outside the server.** Draft rules, two reviewers and the
  gate live in the `cards` CLI and `.claude/skills/anki2/` (301 lines of
  skill, plus rubrics). The MCP's own skill is 32 lines and says there is no
  required method. `prepare_write` blocks only on malformed clozes and
  occlusions.
- **Card fields are not checked for active content.** Anki runs HTML and
  JavaScript in card fields. Nothing stops a `<script>` or an `onerror`
  attribute from being staged for writing.
- **Adapters.** The MCP layer calls CLI entry points with a faked argument
  object in four places (`extract.run`, `source.run`, `render.run`,
  `meter.run`), imports four private names (`_write`, `_regions`,
  `_occlusion`, `_images`), depends on the CLI's build-folder layout, and
  writes a fake `engine/build.json` so the extractor can find its source.
- **Extraction time.** On a synthetic 12-page PDF on an 8-core Mac: rendering
  a figure takes 0.14 s; OCR of one figure takes 19.2 s. OCR runs Tesseract
  four times per figure (four page-segmentation modes, about 4.4 s each) on an
  input of 5,600 by 3,600 pixels, because figures are rendered at 4x and then
  doubled. Extraction uses four OCR workers. Forty-five figures at 19 s over
  four workers is about 215 s, which matches the recorded 220 s. One pass on a
  quarter-size image took 0.63 s. This was synthetic; label recall on real
  figures was not measured.
- **The lock.** Extraction holds the workspace lock from start to finish, so
  every other call on that workspace waits, although extraction already writes
  into a fresh folder and only needs the lock to publish the result.
- **Repeat sources.** `create_workspace` never looks for an existing
  workspace with the same source hash. Workspaces list in random-ID order with
  no label, no dates and no stage.
- **File types.** PDF, text and Markdown only. Slide records already have a
  `speaker_notes` field; it is always empty.
- **Handshake.** The server reports version 1.30.0, which is the MCP
  library's version, not its own.
- **What the frozen tests pin.** The twelve frozen contract tests run the
  `cards` CLI as a subprocess. They import only `cards.common` (`execute`,
  `CardsError`, `Refused`, `Result`, `render`, `tokens`). One frozen test bans
  network imports anywhere in `src/cards/`. So internal function names in
  `src/cards/` are free to change as far as the frozen tests are concerned.
- **The frozen tests are only half a safety net here.** Without the private
  lecture fixtures the contract suite runs 261 tests and skips 24, and the
  24 are the ones that exercise extraction, figures and rendering on real
  lectures. The 3a plan therefore records the CLI's output before the
  refactor and compares after every change, and asks the owner for the
  private fixtures before it is signed off.

## Goals

- A staged write is bound to the exact checked cards, and when AnkiPlus writes
  to Anki itself the receipt is verified by reading the notes back.
- A server-enforced write gate that the calling model cannot weaken, and a
  method an agent can follow on any host from what the server returns.
- About 19 tools in under 4,500 tokens of schema, enforced by a test.
- One call to see an image, one call to change one card, one call to OCR a
  figure, no polling loop for ordinary work.
- "Ready to write" is a real state that survives Anki being closed, restarts
  and days of waiting.
- The same source delivered twice lands in the same workspace.
- A person or agent can list workspaces and see which lecture each is, what
  stage it is at and what it needs next.
- Every mechanical step can be run from a script with JSON in and out.
- PowerPoint files are accepted.
- A lecture is readable within 60 s of a cold start.
- The MCP layer calls typed functions, not CLI entry points.

## Non-goals

- Skill rewriting or merging, and sorting `.claude/` from the product. That
  is piece 4. This piece only moves enforcement into the server and makes the
  existing guidance retrievable.
- Publishing to npm, PyPI or the MCP registry (piece 5).
- Watching chats, scheduling, or deciding which file is which lecture. The
  system around AnkiPlus does that.
- Model calls from inside the server, model keys, or reliance on MCP sampling.
- A general proxy for the Anki MCP. The bridge, if approved, has a fixed short
  list of operations.
- Deleting notes, syncing with AnkiWeb, unsuspending, scheduling, or changing
  note types through AnkiPlus.
- Searching AnKing decks for existing coverage. That stays a judgement the
  host model makes through the Anki MCP. An unattended run records it as not
  checked.
- Changing the legacy `/anki2` pipeline's behaviour, its gate or its phases.
- Word, Keynote or Google Slides files. Remote HTTP hosting.

## Anti-goals

- Any tool argument, environment variable set by the caller, or message that
  lets an agent skip or lower the write gate.
- A write to Anki that was not staged from gate-passed cards, or a second
  write of the same cards after a crash or a retry.
- Calling a receipt verified when the server did not read it back itself.
- Calling two reviews independent. The server cannot know who wrote them.
- The server failing to start, or hanging, because Anki is closed.
- Touching notes that are not the user's own (AnKing notes, other note types).
- A faster extraction that silently finds fewer figure labels.
- Any change in what the `cards` CLI prints or writes.

## Constraints

- `AGENTS.md` freezes `src/cards/`, the contract tests in
  `.codex/contract.sha256`, `.claude/`, `.codex/` and `.agents/`. Only the
  owner lifts that.
- The 2026-11-07 design says the server never connects to Anki and has no
  mandatory review gate. Both are reopened below as owner decisions, not
  assumed.
- No network import in `src/cards/` (frozen test). Any Anki connection lives
  in `src/ankiplusmcp/`.
- A project hook blocks shell commands that mention local ports. Bridge tests
  must use an in-memory fake, and the Anki address must come from config, not
  from a command line.
- Stdio and ordinary tools are the baseline. Progress notifications, prompts
  and resources may be used where a host supports them and never required.
- No push, tag or publish without the owner's go-ahead.
- No private lecture fixtures are in the repository. Work that needs real
  figures needs them from the owner.

## Approaches considered

1. **Tighten in place.** Keep both earlier decisions and the freeze. Do only
   what the MCP layer can do alone: fewer tools, inline waits, partial card
   edits, lookup by hash, labels and stage, a strict gate, a command-line
   face, the handshake fix, and extraction off the lock.
   Gains: no reversals, lowest risk, most of the token saving.
   Costs: cards still pass through the model twice and receipts stay
   unverified; an unattended agent needs the whole Anki MCP, including delete;
   OCR speed, system Chrome and the tag-root lint cannot be fixed because they
   are inside `src/cards/`; the adapters stay as they are; PowerPoint support
   has to copy the slide format into a second place.

2. **Core, gate and bridge. Recommended.** Lift the freeze on `src/cards/`
   source files only and give the mechanical operations typed functions. Cut
   the tool surface. Put the write gate in the server. Add an optional Anki
   bridge that is off until configured, and make "staged" the normal end state
   so nothing depends on Anki being open.
   Gains: fixes every measured problem; the unattended agent can run with no
   Anki MCP at all, so its reach into the collection shrinks to "add gated
   cards".
   Costs: reverses two earlier decisions; the server gains network code and a
   dependency on one particular Anki MCP's tool shapes; it is the most work.

3. **Pipeline server.** One tool takes a source and returns written cards.
   The server drives drafting and review itself through MCP sampling or its
   own model key.
   Rejected: it needs model calls in the server or a host feature most hosts
   lack, takes the judgement away from the host model, and is the phase
   controller the 2026-11-07 design removed on purpose.

Approach 2 is the recommendation because approach 1 leaves the two things
that matter most for unattended use unsolved: what reaches Anki is still an
unchecked retyped copy, and the agent still holds delete rights on the
collection. If the owner declines the bridge, the freeze lift or both, the
design degrades cleanly to approach 1: sub-pieces 3b and 3c below do not
depend on either decision.

## This is five pieces

They share this document but each gets its own plan, built and released in
this order:

| | Piece | Depends on | Owner decision needed |
|---|---|---|---|
| 3a | Core and speed | nothing | freeze lift |
| 3b | Tools and state | 3a preferred, not required | tool rename |
| 3c | Write gate and method | 3b | gate reversal |
| 3d | Anki bridge | 3b, 3c | bridge |
| 3e | PowerPoint | 3a | new dependency |

3a goes first because speed, system Chrome, PowerPoint and the tag-root lint
all need the same freeze decision, and because cutting the tool surface on
top of faked argument objects would build on the thing being removed. 3d goes
last because the bridge only ever writes cards the gate has passed.

## 3a. Core and speed

### The core is `src/cards/`, with typed functions

*(My call.)* The reusable logic stays where it is and keeps its module names.
Each operation the MCP uses gets a public function with plain arguments, and
the CLI's `run(args)` becomes a thin wrapper over it. No new package and no
second copy.

Exactly what would change in `src/cards/`, if the freeze is lifted:

| File | Change |
|---|---|
| `extract/__init__.py` | New `extract_source(source, out_dir, slides, workers, on_progress, should_cancel)` that takes the source path directly. `run(args)` calls it. Removes the need for a fake `build.json`. |
| `extract/ocr.py` | Public names for the binarise and word steps (underscore names kept as aliases; a unit test imports `_words`). Optional result cache and worker count. Defaults unchanged. |
| `extract/pdf.py`, `extract/figures.py` | Accept the output folder and a progress callback as arguments. |
| `source.py` | New `page_image(pdf, out, page)`. `run` calls it. |
| `figures.py` | Public `parse_regions`, `occlusion_markup`, `write_images` (underscore aliases kept). |
| `render/__init__.py` | New `render_rows(rows, out_dir, css, per_sheet, browser)`. `run` calls it. `browser` selects bundled Chromium (default, as now) or the system's Chrome. |
| `check/lint.py` | `lint(note, enumeration, tag_root)` with today's value as the default. |
| `common/files.py` | Public `atomic_write` (`_write` kept as an alias). |
| `extract/pptx.py` | New file, only if 3e is approved. |

Not touched: `gate.py`, `write/plan.py`, `state.py`, `build.py`, `review/`,
`meter/`, `cli.py`, `templates/`, `assets/`, and every file in
`tests/contract/`.

The rule for this work: the frozen contract tests and the existing unit tests
pass unchanged, and `cards` output is byte-identical. A contract test that
would need editing is a stop and a question to the owner, not an edit.

Then `src/ankiplusmcp/` drops every `SimpleNamespace`, every underscore
import and the fake `build.json`.

### Extraction speed

Steps that cannot change which labels are found. These ship in 3a:

- **Work outside the lock.** Extract into the fresh folder, take the lock
  only to check the source hash and publish. *(MCP layer; needs no freeze
  lift.)*
- **Two stages.** Text and figure crops finish first and the slide map is
  returned; figure labels follow in the background. The map marks figures
  whose labels are pending. Anything that needs labels (figure listing,
  occlusion, the gate) waits for them.
- **Use the machine.** OCR workers default to the CPU count, not four.
- **Do not repeat work.** Identical figure images are read once. OCR results
  are cached by image hash, settings and Tesseract version, across workspaces.
- **Progress and cancel between figures**, not only before and after.

Steps that could change which labels are found. These do not ship unless a
benchmark on real figures shows no loss:

- Stop after the first page-segmentation mode when it already found enough.
- Cap the OCR input size.

Target, restated: slide map and text readable within 60 s cold for a 60-slide
lecture; a repeat extraction under 2 s. Full label completion is reported as a
measured number, not promised.

### Small items

- **Handshake version** comes from package metadata. A test compares the two.
- **System Chrome.** Config `browser = auto | chromium | chrome | <path>`.
  `auto` uses bundled Chromium when installed, else the system's Chrome, else
  the existing dependency error. `doctor` and `setup` say which is in use and
  stop offering the download when Chrome is found. The `cards` CLI default is
  unchanged.

## 3b. Tools and state

### Tool surface

| New tool | Replaces | What changes |
|---|---|---|
| `status` | `capabilities`, `list_workspaces`, `get_workspace`, `get_report` | No ID: server facts and workspaces, newest first, filterable by stage, label and source hash. With an ID: label, stage, what is needed next, revision, counts, jobs, write report. |
| `open_workspace` | `create_workspace`, `extract_source` | Finds the workspace for this source hash or creates one, starts extraction, waits, returns the slide map. |
| `read_source` | `read_source`, `search_source` | Optional `query`. |
| `view` | `get_page_image`, `get_figure`, `get_image` | Takes up to four image references, returns the images. |
| `figures` | `list_figures`, `export_figures` | |
| `ocr_image` | `ocr_image` and three follow-ups | Returns regions directly. |
| `build_occlusion` | `build_occlusion`, `import_image` | Returns the mask preview image in the same result. |
| `resolve_target` | same | |
| `edit_cards` | `save_cards`, `save_omissions` | Add, replace, patch named fields of, or remove individual cards; record omissions. Returns check findings for the cards it touched. |
| `get_cards` | same | |
| `check_cards` | same | Also reports gate status and what is missing. |
| `render_cards` | `render_cards` and polling | Waits, returns sheet references. |
| `review_packet` | `prepare_review` | Self-contained: cards or sheets, rubric, report format. |
| `submit_review` | same | |
| `apply_changes` | same | Can also decline a proposed fix with a reason. |
| `stage_write` | `prepare_write` | Runs the gate, writes the plan, marks the workspace staged. |
| `record_results` | `record_external_results` | Registered only when the bridge is off. |
| `push_to_anki` | new | Registered only when the bridge is on (3d). |
| `read_artifact` | `list_artifacts`, `read_artifact` | No artifact named: lists them. |
| `job` | `get_job`, `cancel_job` | Can wait for a change; `cancel` flag. |
| `get_guidance` | same | |

`measure_usage` leaves the MCP and becomes a command-line subcommand; it
reads Claude Code transcripts only and is not card work.

Rules that apply across the surface:

- **One image reference form** everywhere an image is named: an artifact ID,
  `page:<n>`, `figure:<id>`, `sheet:<n>:fronts|backs`, or an absolute path
  under a source root (copied into the workspace on first use).
- **Inline waits.** Long operations wait inside the call up to a limit and
  send progress notifications when the client asked for them. Past the limit
  they return a job reference, and `job` can wait again. No busy polling.
- **Every result that changes or reads a workspace returns its revision**, so
  no call is needed only to learn it. Expected-revision checks stay.
- **The card schema appears once**, in `edit_cards`.
- **Names break at 0.3.0 with no aliases.** *(My call; see decision 5.)* The
  mapping above goes in `docs/capabilities.md` and the changelog.

### Workspace state

- **Find by hash.** `open_workspace` returns the existing workspace for the
  same source bytes and profile, marked as existing, with its stage. A flag
  forces a fresh one. When the hash is new but the resolved lecture identity
  (course and number) matches another workspace, that workspace is listed as
  related; nothing is merged automatically.
- **Label.** From the caller, else the resolved target, else the filename.
- **Stage.** Computed from what is in the workspace, never set by the caller:
  new, extracted, drafted, ready (gate passes), staged, partly written,
  written. A stale stage (cards changed after staging) shows as such.
- **Next.** The list of unmet requirements for the next stage, each with the
  tool that satisfies it.
- **Journal.** An append-only log per workspace of what the server itself saw:
  slides served, images viewed, renders, reviews, stagings, writes. It feeds
  the gate (3c) and is readable by a person.

### Command-line face

`ankiplusmcp call <tool> '<json>'` runs one tool with the same arguments and
prints the same structured result on stdout, and nothing else. It waits for
long operations. `ankiplusmcp status` and `ankiplusmcp push` are shorthands.
Exit codes follow the `cards` convention: 0 ok, 1 findings, 2 error,
3 refused, and new 4 for "try again later" (Anki unreachable, workspace busy).
The npx launcher forwards these subcommands. A script and a running server
may share a workspace root; the existing file locks already cover that.

## 3c. Write gate and method

### The gate

A gate level is set when the server starts (`--gate` or `gate` in the config
file) and cannot be changed by any tool call. `status` reports it.
`init --unattended` writes `gate = "strict"` into the config it creates.
A profile gains one more setting, its house style: the `coldrecall` profile
names today's rules, the default profile has none.

**basic** (the default for an ordinary install):

- G1. No technical blockers (today's cloze and occlusion checks).
- G2. No active content in any field: no scripts, event attributes, frames,
  `javascript:` links or external references; images name media files only.
  This one is new and is on at every level.

**strict** adds, all bound to the hash of the current cards:

- G3. Every card has a deck, a note type and tags under the profile's tag
  root, including a source tag. In a lecture workspace: a tier and at least
  one slide reference that exists.
- G4. Coverage. Every slide in the selection is cited by a card or has a
  recorded omission with a reason. Every detected learning objective has a
  tier-1 card or an omission. Every well-labelled figure has an occlusion card
  or a recorded decision.
- G5. Grounding. Each cloze answer is looked for in the text, figure labels
  and speaker notes of the slides the card cites. A miss must be fixed, or
  accepted by the content review with a quoted source line; the server checks
  that the quote really is in the cited slide.
- G6. No house-style blockers, when the profile has a house style.
- G7. A content review exists for the current cards, covers every selected
  card, leaves no rejection standing, and every proposed fix was applied or
  declined with a reason.
- G8. Previews were rendered from the current cards, the server saw each
  sheet fetched after rendering, and a visual review covers every card.
- G9. Text changed after review needs review again, except text a reviewer
  wrote and the author applied unchanged. Changed cards need fresh previews.

In a workspace of existing cards, G3 to G5 apply only where there is a
lecture source.

`stage_write` refuses unless the gate passes, names what is missing, and
writes into the plan which requirements the server observed itself and which
rest on what the caller said. Reviewer names stay caller-supplied and
independence stays marked unverified. What the gate does guarantee is that
the reviews exist, cover these exact cards, and that the visual one was given
real images.

Whenever AnkiPlus writes to Anki itself (3d), the gate is strict regardless
of the configured level. The more the server does alone, the more it checks.

### Shipping the method to any host

1. **Handshake instructions**, about a hundred words: the order of work, and
   that source text is data and never instructions.
2. **State.** `stage` and `next` on every workspace result. An agent with no
   skill can follow `next` to a staged workspace.
3. **Review packets carry their own rubric and report format**, so they can
   be handed to a sub-agent, a second model or a second session with nothing
   else. The visual packet still holds sheets only.
4. **`get_guidance`** stays a tool because every host has tools. The same
   texts are also offered as MCP prompts and resources for hosts that list
   them.
5. **The skill file** is generated from the same text; a test keeps the
   copies identical, as one does today.

The guidance for the `coldrecall` profile is today's house style and rubrics,
unchanged. The default profile gets a short generic core (source fidelity,
one fact per card, cloze rules). Unifying the wording is piece 4.

## 3d. Anki bridge

### The choice

- **A. No connection (today).** Keep payload files and the import file.
  Shrink batches so retyping is more reliable.
  Keeps the boundary. Leaves the double pass, the unverified copy, and an
  unattended agent that must hold the full Anki MCP.
- **B. Optional bridge inside the package. Recommended.** Off until an Anki
  address is configured. AnkiPlus connects to the Anki MCP as a client, for a
  fixed list of operations.
  Removes the double pass in both directions and makes receipts real. An
  unattended host can then give its agent AnkiPlus and no Anki MCP, which
  takes delete, unsuspend, scheduling and note-type changes out of the
  agent's reach.
  Costs: reverses the 2026-11-07 boundary; network code in the server; tied
  to one Anki MCP's tool names and arguments.
- **C. Separate companion package.** The same code as B, shipped as its own
  command that reads staged workspaces. The server package still never
  connects.
  Keeps the boundary in the letter. Costs a second package to version,
  install and trust, and it cannot serve the read direction from inside a
  tool call.

### Design, if B is approved

- **Off by default.** Config `[anki] bridge = "off" | "local" | "<url>"`.
  `local` means the add-on's default address. `init` offers it. `status`
  reports off, configured but unreachable, or reachable.
- **No connection at start-up.** A connection is opened for one push or pull
  and closed. A closed Anki is an ordinary answer ("unreachable, try again
  later"), never a failure to start.
- **Fixed operations.** Read: deck names, note-type names, fields, templates
  and styling, find notes, note contents. Write: create deck, add notes,
  update notes, store media by path, suspend cards. Nothing else can be
  called, and no tool passes arbitrary operations through.
- **Check the other side first.** Before any write the bridge lists the Anki
  MCP's tools and confirms the ones it needs exist with the arguments it
  expects. Otherwise it reports an unsupported Anki MCP and leaves the payload
  files as the way out.
- **Push** (`push_to_anki`, `ankiplusmcp push`):
  - only from a staged plan whose card hash and gate record are current;
  - preflight: note type exists with the plan's field names, deck exists or
    is created, media files are present;
  - batches are journalled before and after sending. After a crash, a batch
    in doubt is settled by reading Anki, never by sending again;
  - Anki's duplicate check stays on. A duplicate is held and reported with
    the existing note's ID, not forced in;
  - updates apply only to notes that, on read-back, have the profile's note
    type and tag root. Anything else is refused;
  - tier-3 cards are suspended using the card IDs Anki returned;
  - every created or updated note is read back and compared with the plan.
    The receipt says verified only for those that match.
- **Pull.** `open_workspace` can take a note search or note IDs and load the
  notes itself. `render_cards` fetches the real templates and styling.
  `resolve_target` reads the deck list. None of it passes through the model.
- **Staged is the normal end of an unattended run.** Pushing is a separate,
  explicit act. Config `push = "manual" | "when_reachable"`; with the second,
  a push attempt that finds Anki closed returns exit code 4 and changes
  nothing, so a scheduler can simply try again.
- **Behind a small interface**, so a second collection adapter (AnkiConnect)
  can be added later without touching the push logic. *(My call.)* Only the
  one Anki MCP is supported and claimed now.
- **Honest wording changes.** `capabilities`, the README and `AGENTS.md`
  stop saying the server never connects; they say when it does and to what.
- **What the host stops seeing.** Today a write is a call to the Anki MCP's
  own tools, so the host's permission rules apply to it, and in this
  repository the `require_review_before_write` hook checks the legacy gate
  first. A bridge write is a call to `push_to_anki` instead. Those host rules
  no longer see it; the server's strict gate is what stands in their place,
  and `push_to_anki` becomes the one permission worth guarding in a host. The
  legacy `/anki2` flow does not use the bridge and is unaffected.

## 3e. PowerPoint

- **Native reader.** `.pptx` is read with python-pptx (MIT, pure Python):
  slide text in reading order, titles, speaker notes (filling the field that
  is empty today) and embedded pictures as figures.
- **Slide images are optional.** Vector diagrams, SmartArt and grouped shapes
  have no picture to extract. If LibreOffice is installed, the file is also
  converted to PDF so page images and whole-slide figures work as they do for
  PDFs. If it is not, those slides are flagged in the map as having drawings
  that could not be rendered, and `doctor` names the fix.
- Old binary `.ppt` is accepted only when LibreOffice is present.
- LibreOffice is never downloaded by AnkiPlus.

## Untrusted input

Files from a group chat reach a model that can affect the collection.

- Source text is returned as data and marked as such; the handshake
  instructions say it is never to be followed.
- G2 keeps active content out of Anki whatever the model was persuaded to
  write.
- The gate level and the bridge settings come from start-up configuration.
  No tool reads them from the caller.
- With the bridge, an unattended host can withhold the Anki MCP from the
  agent entirely.
- Out of scope: a host that lets its agent rewrite the host's own
  configuration and restart servers.

## Testing

- **3a.** The frozen contract tests and unit tests pass unchanged, a recorded
  before-and-after comparison of the CLI's output shows no difference, and
  the full contract suite is run with the owner's private fixtures before
  sign-off. New unit tests for each typed function. A
  test that the MCP layer imports no underscore name and builds no argument
  object. Timing recorded on a fixture, with the machine named.
- **3b.** A schema-budget test (tool count and characters). Protocol tests for
  inline waits, progress, job fallback, image references, partial edits and
  their errors, find-by-hash, stage and next. Command-line tests for JSON
  output and exit codes.
- **3c.** One test per gate requirement, passing and failing. A test that no
  tool argument changes the level. A test with script and event-attribute
  fields. Stale-review and changed-after-review cases.
- **3d.** An in-memory fake Anki MCP (the hook rules out a local port):
  preflight refusal, duplicate held, crash between send and record then
  resume with no second write, read-back mismatch, refusal to update a
  foreign note, unreachable returns "try again later". One manual run against
  the owner's real Anki, only with the owner's go-ahead, reported as what was
  and was not tried.
- **3e.** A generated `.pptx` fixture with text, notes and a picture; the
  flagged-drawing case; the same with LibreOffice when CI has it.
- Label-recall benchmark for any OCR setting change, on real figures.

## Addendum: what the two-model lecture test added (2026-11-11)

One lecture (31 slides, image-heavy) was run through the current MCP and
skill by two models with the same prompt. Both produced usable drafts and an
unsuspension list, and both hit the same problems independently.

Confirmed, already in this design:

- Neither run prepared or submitted a review, and `prepare_write` accepted
  both (3c).
- Both resent the whole card set for small fixes, both failed their first
  save on a stale revision, and both left the MCP to watch the extraction
  job's file on disk because there was no progress (3a, 3b).
- Both copied note-type conventions by hand and previewed without the real
  templates; one found four duplicates of existing cards only by searching
  the collection by hand (3d, the read direction).

New, proposed for 3b and not yet approved; to be accepted or dropped when the
3b plan is reviewed:

- `build_occlusion`'s `mode` values `one` and `all` do not say what they do.
  The two runs ended with opposite settings. Rename them after Anki's own
  terms (hide all, guess one; hide one, guess one).
- Tools that only make derived files (occlusion images, previews, OCR, page
  images) should not bump the card revision.
- `resolve_target` should read a filename with a leading ordinal
  (`10_MED241_L023_…`).
- `build_occlusion` should reuse one media file per source image and let the
  caller name it, not write a new hashed copy on every call.
- The objective identifiers that coverage expects should be returned with the
  slide map, not left to be guessed.
- `doctor` and `init` should warn when a source root contains a symlink that
  leads outside it, because files under it are then refused; and the owner's
  own registration should select the `coldrecall` profile.

## Decided here, as my calls

The owner can overturn any of these while reading.

- The core stays in `src/cards/` under its current names; no new package.
- The legacy `cards gate` and the new write gate are separate code. They
  guard different state and the legacy one is frozen behaviour.
- G2 (no active content) applies at every gate level.
- The server writing to Anki always implies the strict gate.
- Stage is computed, not stored as something a caller can set.
- One generic `call` subcommand, not a second hand-written command per tool.
- `measure_usage` leaves the MCP tool list.
- The bridge sits behind a small interface; one adapter now.
- Tool names break at 0.3.0 without aliases.
- OCR settings that could lose labels do not change without a benchmark.

## Left to the builder

- Exact argument names, result shapes and error codes for the new tools,
  within the table and rules above and the schema budget.
- The inline wait limit, set below the shortest default tool timeout among
  the supported hosts, checked against their documentation at build time.
- How `view` encodes and caps several images in one result.
- Where the hash index lives and how the OCR cache is bounded.
- The matching rule for G5 (case, punctuation, plurals, numbers) and its
  false-positive rate on a real lecture, reported before it is made a blocker.
- The HTML allowlist for G2, taken from what the existing templates and
  house style actually use.
- Which transport the Anki MCP add-on speaks, whether it needs a token, and
  what its note-read tool returns for card IDs.
- How the journal and plan record a batch in doubt.
- Whether card IDs may be omitted and assigned by the server.
- The reading order rule for PowerPoint shapes, and how non-raster pictures
  (EMF, WMF) are handled.
- Version numbers for each sub-piece.

## Decisions for the owner

Most important first. Each has a recommendation; none is assumed.

**Answered 2026-11-10: approved as recommended.** That means: bridge option
B, reading and writing, `push = "manual"` by default, unattended cards tagged
and not suspended; the narrow freeze lift; the strict gate with `basic` as the
ordinary default; the split and order as listed; tool names break at 0.3.0
with no aliases; the 60-second target as restated; python-pptx accepted.
Two things stay open and are not covered by that approval. The test write
into the real collection (decision 1) still needs its own go-ahead when 3d is
built. Decision 6 had no recommendation: until real figures are supplied, only
the safe speed steps ship.

1. **Anki bridge.** A, no connection; B, optional bridge in the package; or
   C, a separate companion. Recommended: B. If B or C:
   - may it read as well as write? Recommended: yes.
   - default `push = "manual"`? Recommended: yes; `when_reachable` is opt-in.
   - should cards pushed by an unattended run carry a flag tag, and should
     they also arrive suspended? Recommended: tag yes, suspended no.
   - a go-ahead, at build time, for one manual test write into a scratch deck
     in your real collection.
2. **Lift the `src/cards/` freeze, narrowly.** Source files only, exactly
   the table in 3a. Contract tests, the hash list, `.claude/`, `.codex/` and
   `.agents/` stay frozen. `AGENTS.md` is edited to say so. Recommended: yes.
   Without it: no OCR speed-up beyond the lock fix, no system Chrome, the
   style lint keeps its fixed tag root, and the adapters stay.
3. **A server-enforced gate.** This reverses "no mandatory review gate in
   this toolkit" from 2026-11-07, for strict mode only. Recommended: yes,
   with `basic` as the default for an ordinary install and `strict` whenever
   the server writes to Anki itself or the install is marked unattended.
4. **The order and the split** into 3a to 3e, each with its own plan and
   release. Recommended as listed.
5. **Breaking tool names at 0.3.0 with no aliases.** Recommended, because
   nothing is published to a registry yet and piece 5 waits for the names to
   settle. The alternative is one release that answers to both.
6. **Real figures for an OCR benchmark.** Either supply a small private set
   of lecture figures so the faster OCR settings can be measured for label
   loss, or accept that only the safe speed steps ship.
7. **The 60-second target.** Accept "slide map and text readable in 60 s,
   figure labels may follow" as meeting it. Recommended: yes.
8. **PowerPoint.** Accept python-pptx as a dependency, and accept that
   without LibreOffice vector diagrams are flagged, not shown. Recommended:
   yes to both.
