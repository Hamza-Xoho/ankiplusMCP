# Anki v2

The local `cards` CLI prepares resumable artifacts for the `/anki2` Claude Code
skill. It implements `state`, `meter`, `extract`, `source`, `target`, `check`, `render`,
`figures`, `packets`, and `apply`; the v1 runtime remains untouched.
Nothing is deployed or published, and there is no container build for this CLI.

## Setup and use

Python 3.12 or newer is required. No runtime environment variables or credentials
are required. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/cards state init "/absolute/path/MED241_L006_lecture.pdf"
.venv/bin/cards state get --build builds/<build-id>
.venv/bin/cards state set --build builds/<build-id> facts.anki_reachable=true
.venv/bin/cards state phase --build builds/<build-id> P0 start
.venv/bin/cards state next --build builds/<build-id>
.venv/bin/python -m cards state --help
```

`init` uses `builds/` under the current working directory and writes the folder
name into `builds/.current`. Other actions use the explicit `--build` path and
can run from any directory. A matching source SHA-256 resumes the existing build.
Mark phases `start`, then `done`; `next` returns an interrupted phase or the phase
after the last completion. Phase 6 will supply the runtime phase files it names.
Preflight facts are booleans (`anki_reachable`, `note_type_exists`, `deck_exists`,
`deck_has_source_tag`), a nonnegative integer (`existing_note_count`), or a string
(`deck_decision`). Other keys are rejected. Build artifacts stay local and ignored.

## Checks and handoff

```sh
.venv/bin/python -m pytest -q tests/contract/test_p0_foundations.py tests/unit
```

The Phase 0 contract suite was run before implementation: 9 failures and 18 setup
errors because the package was absent. The owner runs the phase gate, the L006 manual
check, and the contract freeze as described in `prompts/phase-00-foundations.md`.

With Anki running, the separate manual access spike is:

```sh
.venv/bin/python tools/q1_probe.py
```

Run it first in a terminal, then in the authorized Claude Code environment as
specified by the phase prompt. Record both results in `docs/decisions.md`.
The probe is outside the offline package and is not called by `cards` or tests.
Only its reply parser is tested offline. No live Q-1 result is claimed.

The repository still includes the original staged buildkit and setup files.
Private fixtures belong under `tests/fixtures/private/`; missing fixtures fail
explicitly. Source PDFs and the existing Claude runtime are read-only for this phase.

Phase 1 adds the offline usage meter:

```sh
.venv/bin/cards meter --session /path/to/session.jsonl --out /tmp/cards-meter
.venv/bin/cards meter --latest "$PWD" --out /tmp/cards-meter --line
.venv/bin/python -m pytest -q
```

A session ID can replace the transcript path. `--latest` searches the project's
Claude transcript directory; `--build` restricts it to sessions modified since
P0 started and attributes costs to phase timestamps. Normal output starts with
`OK`, `FINDINGS`, or `ERROR`; `--line` emits only the specified `Usage:` line.
Exit 0 means all waste checks pass, 1 means findings, and 2 means invalid input.
Details go to `cost.json` and `cost.md` in `--out`. Sonnet 5.5 costs stay unknown
until the owner fills `src/cards/meter/prices.toml` at the manual gate.

[Lean workspace notes](docs/lean-workspace.md) list the loaded L006 environment,
project settings changes, and remaining user-level steps. The fresh-session
context reduction has not been measured on this host. This checkout stands in
for the owner’s Mac Cards workspace; user-level configuration files were not supplied.

Phase 2 adds the offline source pipeline. Install the system OCR engine once
(on Ubuntu: `sudo apt-get install tesseract-ocr`); Python PDF/image dependencies
are installed by the editable package command above. Tesseract's English data
is required. To reproduce the tested Python dependency versions, run
`.venv/bin/pip install -r requirements.lock`. No model, Anki connection, or credentials are used.

```sh
.venv/bin/cards extract --build builds/<build-id>
.venv/bin/cards source --build builds/<build-id> --slides 10-12,14
.venv/bin/cards source --build builds/<build-id> --grep mitochondria
.venv/bin/cards source --build builds/<build-id> --page-image 10
.venv/bin/cards source --build builds/<build-id> --all
.venv/bin/cards target --build builds/<build-id> --existing-decks /path/to/decks.json
.venv/bin/python -m pytest -q
```

`decks.json` is an offline JSON array of existing deck names. Set
`facts.deck_has_source_tag=true` only when the selected deck already contains
this lecture. Target names a flat deck and reports whether creation is needed.
For unconventional filenames supply all of `--course`, `--number`, and
`--title`; optional subject/system flags add tags.

Extract writes per-slide text, 4× figure crops with OCR labels, literal learning
objectives and a compact map under `source/`. Optional `--slides` selects a
partial extraction. Cache reuse requires matching source bytes, slide selection,
extractor cache version and existing artifacts. A changed source is re-extracted.
Image-only pages receive whole-page OCR. OCR preserves the v1 threshold of 128,
2× upscale, and PSM modes 11/6/12/4; Tesseract reads image bytes via stdin.
The map's `~ILO` links are lexical hints, not evidence of coverage.
Extraction can exit 1 with valid artifacts when slides have flags or no objectives
are stated. Source slices are exempt from the normal stdout limit; page images
have a maximum dimension of 1,000 pixels. The owner runs the Phase 2 gate, visual
checks, label-recall characterization and freeze; no later phase is implemented.

For the manual L007 recall check, the owner writes
`tests/fixtures/private/l007_labels.json` as
`{"fig_id":"p03_f1","labels":["Pectoralis major","…"]}`, choosing a figure ID
from L007's extracted records and labels by eye. Then run:

```sh
.venv/bin/python -m pytest -q -o 'python_functions=char_*' tests/characterization/test_p2_labels.py
```

This separately selected characterization fails explicitly if ground truth is
missing. It is not part of the automated behavioral contracts.

## Phase 3: draft checks, phone sheets and occlusions

```sh
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
.venv/bin/cards check --build builds/LECTURE
.venv/bin/cards render --build builds/LECTURE
.venv/bin/cards render --build builds/LECTURE --only n007,n015
.venv/bin/cards figures --build builds/LECTURE --fig p07_f1 --keep 1,2
.venv/bin/python -m pytest -q tests/contract/test_p3_*.py tests/unit
```

`check` reads D-6 drafts, D-7 skips and extracted slides/objectives plus target.
It writes `checks/check.json`: located schema blockers S01–S09, style findings
L01–L13, uncovered slides/objectives and note/card/tier/group counts. Findings
exit 1; invalid JSON exits 2. Clean output is `OK` and one stats line. The schema
code mapping is recorded in `docs/decisions.md`.

`render` uses the unchanged bundled ColdRecall template/CSS by default, or a
`model/{front.html,back.html,style.css}` snapshot within the build. Install the
Playwright Chromium browser once on the host; Linux browser dependencies must
also be available. It writes sanitized HTML and 390 px night screenshots under
`renders/cards/`, eight notes per sheet pair under `renders/sheets/`, and the
provenance-bearing `renders/sheets.json` mapping. Scripts and browser requests
are disabled. `--only` preserves unselected card images and unaffected sheets;
run a full render first. `--per-sheet` changes the grouping; `--anki-html` reads
a build-contained JSONL of `{id,question,answer}` for post-write checks.

`figures` uses extracted OCR labels, groups repeated labels into shared cloze
indices and appends a stable D-6 IO draft with media and a labelled mask preview
under `source/figures/`. It does not change the lecture or extracted original.
`--regions regions.json` accepts build-contained estimated fractional rectangles
(`left,top,width,height,text,group`), `--keep` filters group IDs, and `--mode all`
selects hide-all rather than the default hide-one. No labels produces one
question to estimate rectangles. Existing edited/dropped IO drafts are refused
rather than overwritten. PNG provenance is stored in adjacent `.png.json` files.

Phase 3 validation uses the private v1 L006 drafts via `tests/p3_helpers.py`;
conversion preserves card field text. The owner runs the Phase 3 gate, visual checks,
freeze and commit. Review packets, gate and Anki writes remain later phases.

## Phase 4: independent review packets and report application

```sh
.venv/bin/cards packets --build builds/LECTURE --round 1
# Launch the named Claude Code agents yourself using their PROMPT.md paths.
.venv/bin/cards apply --build builds/LECTURE --round 1
.venv/bin/cards check --build builds/LECTURE
.venv/bin/cards render --build builds/LECTURE --only n007,n015
.venv/bin/cards packets --build builds/LECTURE --round 2 --only n007,n015
.venv/bin/cards apply --build builds/LECTURE --round 2
.venv/bin/python -m pytest -q
```

Packets refuse unresolved check blockers. Before packet creation, generate any
missing flagged cited page using `cards source --build builds/LECTURE --page-image N`;
packet construction reads only build artifacts and shipped templates. Round 2 adds
group siblings and rebuilds mixed sheets to exclude other notes. The student gets
all pairs through six; above six it gets every tier-1 pair and enough pairs to cover
every group. `--student-subset all` explicitly includes every relevant pair.

Reports go beside the packet directories, named `maintainer_report.jsonl` and
`student_report.jsonl`. JSONL schemas and examples are in each packet. Above 80
notes, the main maintainer packet is for set review, with additional independent
per-note packets under `maintainer-sections/`; launch each with `anki-maintainer`.
Each section names its own `maintainer_sectionNN_report.jsonl`, also required by
apply. The student remains independent of every maintainer packet.

`apply` validates all reports before writing, saves the exact input bytes as
`drafts.rN.jsonl`, applies field rewrites, moves rejected notes to skips and writes
`review/roundN/apply_log.json`. `--decline ID:REASON` drops the named note with that
reason. Conflicting rewrites preserve fields and exit 1. Repeated visual faults
on at least three notes flag CSS work instead of patching notes. Student V2
alternatives become A2 blockers. Open blockers after round 2 mark notes unresolved
and add `#ColdRecall::Review_unresolved`; suspension belongs to Phase 5.
An unchanged apply rerun is idempotent; changed reports or drafts after application
require deliberate resolution in a new round, preserving the existing backup/log.

The Phase 4 handoff is [docs/phase4-review.md](docs/phase4-review.md). Runtime
reviewers, Phase 5, the gate and the contract freeze are not run by this phase.

### Phase 5: gate, write plan and report

```bash
.venv/bin/cards gate --build builds/<build>
.venv/bin/cards write --build builds/<build>
# Complete the inline Anki batches, suspend listed notes, and verify expected counts.
# Record actual counts in build.json.write and mark P6 done before reporting.
CLAUDE_SESSION_ID=<current-session-id-or-transcript-path> .venv/bin/cards report --build builds/<build>
.venv/bin/python -m pytest -q
```

Q-1 has no passing result, so `--direct` is absent. Changed review inputs or drafts require a fresh gate. `write/provenance.json` documents exact native payloads without adding keys to Anki arguments. See [Phase 5 handoff](docs/phase5-write.md) for the L006 demonstration and scratch-profile verification still required.
