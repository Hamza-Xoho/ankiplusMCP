---
id: SPEC-anki-v2
title: /anki v2 — Design Specification
type: design-spec
version: 0.1.0
derived_from:
  charter: docs/anki-v2-brief.md
  charter_version: 0.2.0
  trd: docs/anki-v2-trd.md (0.2.0)
created: 2026-11-05
---

# /anki v2 — Design Specification

> The brief says what and why; the TRD says what each tool must do. This says **how**: names, shapes, transitions, errors. Where this disagrees with the brief, the brief wins and this document is wrong.
> **Test for every section: two competent implementers reading it should produce compatible systems.**

**Two environments, never mixed:**
- **Build time:** Codex (GPT-6.1 Sol) in T3 Code edits this repo. Its rules: `AGENTS.md`, `.codex/`, `.agents/skills/`.
- **Run time:** Claude Code runs `/anki2` in `this repository`. Its rules: `CLAUDE.md`, `.claude/`.

The `cards` CLI is the bridge. Codex builds it; Claude calls it.

---

## 1. Decisions

| # | Decision | Made | Attribution | Settled | Rationale |
|---|---|---|---|---|---|
| D-1 | Deck shape | Flat top-level deck named after the slides (slide-1 title, fallback filename topic, collision suffix ` (MED241 L006)`) | human-decided | 2026-11-05 | the owner: "the deck doesn't get saved within a deck" |
| D-2 | Build folders | Kept locally, gitignored | human-decided | 2026-11-05 | Anki is the source of truth after writing |
| D-3 | Language | Python 3.12, existing `.venv`; revisit per subcommand if it misses G-11 | human-decided (pinned for discussion) | 2026-11-05 | Native code already does the heavy work; tokens are the cost |
| D-4 | Command shape | One `cards` command with subcommands | human-decided | 2026-11-05 | Shared config; maps 1:1 to MCP tools in stage 2 |
| D-5 | Human gate | None. The review verdict is the gate, enforced by `cards gate`, `cards write` and a runtime hook | human-decided | 2026-11-05 | the owner doesn't check cards before writing |
| D-6 | Unresolved blocker after round 2 | Write suspended, tagged `#ColdRecall::!Flags::Review_unresolved` | human-decided | 2026-11-05 | No work lost; nothing broken in reviews |
| D-7 | Runtime guards | Hooks block fork reviewers, raw PDF reads and Bash to local ports | human-decided | 2026-11-05 | The three costliest L006 failures |
| D-8 | Runtime models | Orchestrator `claude-sonnet-5-5`/medium; `anki-maintainer` `claude-sonnet-5-5`/high; `anki-student` `claude-sonnet-5-5`/medium | human-decided (model), derived (effort) | 2026-11-05 | The reviewers are the only quality check, so the maintainer reasons hardest |
| D-9 | Success measure | Waste checks W-1 to W-8; cost reported, not targeted | human-decided | 2026-11-05 | "No tokens wasted as before" |
| D-10 | Student subset | All sheet pairs if there are ≤ 6; above that, pairs holding tier-1 notes plus one note from each group | delegated to Claude | 2026-11-05 | 12 images read in one turn is cheap |
| D-11 | HARVEST, REPAIR | v1.1 | human-decided | 2026-11-05 | — |
| D-12 | Usage line in report | Yes | human-decided | 2026-11-05 | Drift shows up without an audit |
| D-13 | Lean workspace | Cards folder only | human-decided | 2026-11-05 | — |
| D-14 | Rollout | `/anki2` beside `/anki` on branch `anki-v2`; rename after acceptance | human-decided | 2026-11-05 | v1 keeps working during the build |
| D-15 | Build tool | T3 Code + Codex, GPT-6.1 Sol, high reasoning, **Auto** permission mode (workspace-write) | human-decided (tool), derived (settings) | 2026-11-05 | Full access would remove `.codex/` protection |
| D-16 | Code location | Python package at `src/cards/`, installed editable into `.venv`, called as `.venv/bin/cards`. The skill folder holds only prompts, templates and assets. | derived-from-charter | 2026-11-05 | One install; stage-2 MCP server imports the same package |
| D-17 | Hash | SHA-256 hex of file bytes, everywhere (source hash, drafts hash, contract freeze) | derived | 2026-11-05 | The runtime hook and `cards` must compute the same value |
| D-18 | Active build pointer | `builds/.current` holds the build folder name; written by `cards state init`, removed by `cards report` | derived | 2026-11-05 | Lets the runtime write-guard find the build without arguments |

### Deferred to the implementer

| # | Decision | Bounding constraint |
|---|---|---|
| D-n1 | PDF library, OCR engine, renderer | Keep the measured OCR recipe from `ocr_regions.py` (binarise at 128, 2× upscale, multi-psm), or beat it on the L007 label-recall test. No network. |
| D-n2 | Token estimate for size budgets | Use `ceil(chars / 4)` unless a tokenizer is added offline. The same function everywhere. |
| D-n3 | Internal module layout below §2 | Must respect §2's dependency directions |
| D-n4 | Argument parser | stdlib `argparse` or a small dependency. `--help` ≤ 20 lines per subcommand. |
| D-n5 | Test framework details | pytest. Contract tests live in `tests/contract/` with the exact names from the test contract. |
| D-n6 | Direct Anki writer (`write/direct.py`) | Exists only if the Q-1 spike passes. It is the only module allowed to open a socket, and only to `127.0.0.1:3141`. |

---

## 2. Module boundaries

```
src/cards/
  cli.py            dispatcher only
  common/           output contract, errors, provenance, paths, hashing, log
  state.py          T-1
  target.py         T-2   (ports scripts/deck_name.py)
  extract/          T-3   (pdf, text_source, figures, ocr, objectives, mapgen)
  source.py         T-4
  check/            T-5   (schema, lint, coverage)
  render/           T-6   (ports scripts/render_cards.py)
  figures.py        T-11  (ports build_occlusion.py; uses extract/figures, extract/ocr)
  review/           T-7 packets, T-8 apply
  gate.py           T-9
  write/            T-10  (plan, importfile, direct?)
  report.py         T-12
  meter/            T-13  (transcript, waste, prices)
```

| Module | Responsibility | May depend on | Must never |
|---|---|---|---|
| `common` | stdout contract, exit codes, provenance, build-dir resolution, hashing, `log.jsonl` | stdlib | import any other `cards` module |
| `cli` | parse args, call one command function, map exceptions to exit codes | every command module | contain logic |
| `extract`, `target`, `source` | read the source, write `source/` and `target.json` | `common` | write outside the build folder; open the source for writing |
| `check`, `render`, `figures` | validate, lint, render | `common`, `extract` (figures only) | call Anki |
| `review` | build packets, apply reports | `common`, `source` (slice function), `check` (to refuse on blockers) | read files outside the build folder and `.claude/skills/anki2/` |
| `gate`, `write`, `report` | gate decision, write plan, report | `common`, `check`, `meter` (report only) | let any input skip the gate |
| `meter` | read Claude Code transcripts | `common` | write anywhere except its `--out` path |
| `write/direct.py` | optional direct writer | `common` | exist unless Q-1 passed; reach anything but `127.0.0.1:3141` |

**INV-2 (hooked):** no `socket`, `http`, `urllib`, `requests`, `httpx`, `aiohttp` or `websocket` import anywhere in `src/cards/` except `write/direct.py`.

---

## 3. Data shapes

Every JSON file carries `"_meta": {"tool": "cards <sub>", "version": "<pkg version>", "created": "<ISO 8601 UTC>"}` (G-7). JSONL files put the same object on line 1 as `{"_meta": {...}}`, and readers skip it. Markdown files start with `<!-- cards <sub> <version> <created> -->`.

### 3.1 `builds/<YYYY-MM-DD>_<lecture-id>/build.json` (D-1 in TRD)

```json
{
  "_meta": {"tool": "cards state", "version": "0.1.0", "created": "2026-11-05T18:02:11Z"},
  "build_id": "2026-11-05_MED241-L006",
  "job": "build",
  "source": {"path": "/lectures/MED241_L006_2026-09-13_endoplasmic-reticulum-mitochondria-and-golgi-apparatus.pdf",
             "sha256": "9f2c…", "kind": "pdf", "slides": null},
  "phase": "P4",
  "history": [{"phase": "P0", "status": "done", "started_at": "…", "ended_at": "…"}],
  "facts": {"anki_reachable": true, "note_type_exists": true, "deck_exists": false, "deck_has_source_tag": false},
  "review": {"round": 1, "maintainer": "PASS_WITH_FIXES", "student": "PASS_WITH_FIXES"},
  "gate": {"status": "pending", "drafts_sha256": null, "checked_at": null},
  "write": {"created": 0, "updated": 0, "suspended": 0, "errors": []},
  "tools": {"cards": "0.1.0"}
}
```

- **Identity:** `build_id` (immutable). `lecture-id` is `MED241-L006` from the filename, or a slug of the text source name.
- **Immutable once written:** `source.sha256` and `build_id`.
- **Changes:** `history` is append-only; `facts` are set only through `cards state set`.

### 3.2 `target.json`

```json
{"_meta": {…}, "deck": "Endoplasmic Reticulum, Mitochondria & Golgi Apparatus", "deck_source": "slide1",
 "create_deck": true, "course": "MED241", "number": 6, "title": "Endoplasmic reticulum mitochondria and golgi apparatus",
 "source_tag": "#ColdRecall::#Source::MED241::L006_Endoplasmic_reticulum_mitochondria_and_golgi_apparatus",
 "subject_tag": "#ColdRecall::^Subjects::Histology", "system_tag": null,
 "tier_tags": {"1": "#ColdRecall::!Tier::1", "2": "#ColdRecall::!Tier::2", "3": "#ColdRecall::!Tier::3"},
 "legacy_tags": ["src::MED241::L006"], "note_type": "ColdRecall Cloze", "confident": true}
```

`deck_source` is `slide1` or `filename`. A deck name never contains `::`.

### 3.3 `source/slides.json`, `source/map.md`, `source/objectives.json`

```json
{"_meta": {…}, "lecture": "MED241-L006", "slide_count": 24, "source_sha256": "9f2c…",
 "slides": [{"n": 10, "title": "Mitochondria", "text": "• Freely in cytoplasm\n• Number increased in …",
             "speaker_notes": "", "word_count": 64,
             "figures": [{"fig_id": "p10_f1", "file": "figures/p10_f1.png", "bbox": [0.52, 0.18, 0.95, 0.80],
                          "ocr_labels": [{"text": "cristae", "conf": 91}], "repeated_labels": []}],
             "flags": []}]}
```

Flags: `image_only`, `low_text` (< 15 words), `repeated_title`, `scan`, `objectives`.

`map.md` gives one line per slide, ≤ 110 characters:

```
<!-- cards extract 0.1.0 2026-11-05T18:02:15Z -->
# MED241-L006 · 24 slides · 6 objectives · 3 flagged
02 | Learning objectives | 58w | fig:0 | — | objectives
10 | Mitochondria | 64w | fig:1 (cristae, matrix…) | ILO4 | —
14 | MERRF | 41w | fig:1 | ~ILO5 | image_only
```

`objectives.json`:

```json
{"_meta": {…}, "objectives": [{"id": "ILO1", "text": "Enumerate membranous and non-membranous organelles", "slide": 2}], "flags": []}
```

With no objectives found, the list is empty and `flags` is `["no_objectives"]`.

### 3.4 `drafts.jsonl` (one note per line)

```json
{"id": "n007", "kind": "cloze", "notetype": "ColdRecall Cloze", "deck": "Endoplasmic Reticulum, Mitochondria & Golgi Apparatus",
 "fields": {"Text": "<b>RER</b> separates newly made proteins from the {{c1::cytosol::compartment}} inside its {{c2::cisternae}}",
            "Extra": "- Why: keeps secretory proteins out of the cytoplasm<br>- <div class=\"src\">L006, slide 7</div>"},
 "tags": ["#ColdRecall::#Source::MED241::L006_Endoplasmic_reticulum_mitochondria_and_golgi_apparatus", "#ColdRecall::!Tier::1", "#ColdRecall::^Subjects::Histology"],
 "tier": 1, "objective": "ILO3", "source_ref": [7], "group": "g03", "action": "create", "nid": null, "status": "draft"}
```

- `kind` is one of `cloze`, `io` or `basic`. `fields` uses the note type's own field names.
- IO notes add `"media": [{"path": "figures/p10_f1.png", "filename": "L006_p10_f1.png"}]` and `"preview": "figures/p10_f1_preview.png"`.
- `status` is `draft`, `fixed`, `dropped` or `unresolved`.
- `id` is unique and stable across rounds; it is never reused after a drop.

`skipped.jsonl`:

```json
{"slide": 15, "item": "MERRF lysine tRNA mutation detail", "reason": "out_of_scope", "note": "aside, no objective"}
```

### 3.5 `checks/check.json`

```json
{"_meta": {…}, "findings": [{"code": "L03", "severity": "blocker", "note_id": "n012", "slide": null, "message": "comma inside c1"}],
 "coverage": {"slides_uncovered": [19], "objectives_without_t1": [], "objective_enumerations_below_t1": []},
 "stats": {"notes": 40, "cards": 93, "tiers": {"1": 29, "2": 9, "3": 2}, "tier3_share": 0.05, "groups": 14}}
```

Lint codes:

| Code | Rule | Severity |
|---|---|---|
| L01 | Trailing full stop | warn |
| L02 | Underline on a filler word, or more than 3 underlines | warn |
| L03 | Comma inside a cloze | blocker |
| L04 | More than 5 cloze numbers | blocker (warn when the group is flagged as an enumeration) |
| L05 | Escaped HTML in a field | blocker |
| L06 | Raw newline in Extra | blocker |
| L07 | Extra over 3 lines or about 200 characters | warn |
| L08 | Card text over about 200 characters | warn |
| L09 | More than 4 bold runs | warn |
| L10 | A tag outside `#ColdRecall::` | blocker |
| L11 | Citation outside `<div class="src">` | warn |
| L12 | Hint longer than about 20 characters | warn |
| L13 | Unwrapped formula inside a blank | warn |

Schema codes are `S01`–`S09`; each names the file, line and field (G-8).

### 3.6 Review packet and reports

Packet folder: `review/round<k>/<maintainer|student>/`.
- **Maintainer** contains: `PROMPT.md`, `brief.md`, `rubric.md`, `report-format.md`, `house-style.md`, `drafts.jsonl`, `source_slices.md`, `map.md`, `objectives.json`, `check.json`, `reconcile.md`, `pages/`.
- **Student** contains: `PROMPT.md`, `brief.md`, `rubric.md`, `report-format.md`, `sheets.json`, `sheets/`, `previews/`.

Nothing else may be in either folder (CON-6).

Report JSONL, one record per line, written by the agent to `review/round<k>/<reviewer>_report.jsonl`:

```json
{"type": "note", "reviewer": "maintainer", "note_id": "n017", "card": null, "verdict": "fix", "codes": ["A3"], "blocker": true,
 "evidence": "\"an {{c1::artery}}\" — article leaks vowel", "rewrite": {"Text": "…", "Extra": "unchanged"}}
{"type": "note", "reviewer": "student", "note_id": "n022", "card": "c1", "verdict": "fix", "codes": ["V2"], "blocker": true,
 "evidence": "front fits 'stores' and 'packages'", "attempt": {"answer": "stores them", "result": "alternative"}, "rewrite": null}
{"type": "set", "reviewer": "maintainer", "code": "S2", "notes": ["n021", "n034"], "finding": "…", "fix": "…"}
{"type": "summary", "reviewer": "maintainer", "verdict": "PASS_WITH_FIXES", "stats": {"notes": 40, "pass": 31, "fix": 8, "reject": 1, "blockers": 3}}
```

`"rewrite": {"Extra": "unchanged"}` means keep that field as it is.

### 3.7 `gate.json`

```json
{"_meta": {…}, "status": "passed", "drafts_sha256": "4be1…", "round": 2,
 "verdicts": {"maintainer": "PASS_WITH_FIXES", "student": "PASS"}, "open_blockers": [],
 "counts": {"cloze": 39, "io": 1, "tiers": {"1": 29, "2": 9, "3": 2}}, "write_suspended": ["n029", "n030"], "reasons": []}
```

### 3.8 `write/`

`batches/01.json` holds exactly the AnkiMCP `add_notes` arguments:

```json
{"deck_name": "Endoplasmic Reticulum, Mitochondria & Golgi Apparatus", "model_name": "ColdRecall Cloze",
 "notes": [{"fields": {"Text": "…", "Extra": "…"}, "tags": ["…"]}]}
```

The other files:
- `updates.json`: `[{"note_id": 1793684734471, "fields": {…}}]`
- `suspend.json`: `{"draft_ids": ["n029", "n030"], "reason": {"n029": "tier3", "n030": "tier3"}}`
- `expected.json`: `{"created": 40, "updated": 0, "suspend_notes": 2, "verify": ["tag:<source_tag>", "tag:<source_tag> -tag:#ColdRecall::!Tier::3 is:suspended"]}`
- `import.txt` (fallback): `#separator:tab`, `#html:true`, `#notetype:…`, `#deck:…`, `#tags column:3`, then `Text⇥Extra⇥tags`. One file per note type.

### 3.9 `report.md` and the usage line

The report is at most 25 lines. Its last line is exactly:

```
Usage: 23 calls · peak 61k · ≈$1.42 (Sonnet 5.5 prices) · waste checks 8/8 pass
```

If a price is unknown, it reads `cost n/a (no price for <model>)`. A failed check reads `waste checks 7/8 — W-4 failed (add_notes payload sent twice)`.

### 3.10 `log.jsonl` (every command run appends one line)

```json
{"ts": "…", "cmd": "cards check", "args": ["--build", "…"], "exit": 1, "ms": 412, "stdout_chars": 388}
```

### 3.11 `meter` outputs

`cost.json`:
- `calls`: one row per call, holding `idx`, `ts`, `model`, `input`, `cache_write`, `cache_read`, `output`, `ctx` and `tools`
- `totals`
- `first_ctx`, `peak_ctx`
- `compactions`: each with `pre` and `post`
- `subagents`: each with `id`, `type`, `is_fork`, `first_ctx`, `calls` and `totals`
- `waste`: one entry per check `W-1`…`W-8`, each `{"pass": bool, "evidence": [...]}`
- `cost`: `{"usd": float|null, "model": str, "unknown_prices": [...]}`

`cost.md` is the same in a readable form.

**Transcript format (Claude Code, verified on the 2–3 Nov L006 session):**
- one JSON object per line, `type ∈ {assistant, user, attachment, system, …}`
- assistant rows carry `message.id`, `message.model` and `message.usage` with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens`
- one API call can span several rows sharing a `message.id`, so count usage once per id
- compactions are `type: system, subtype: compact_boundary` with `compactMetadata.preTokens` and `postTokens`
- subagents live in `<session>/subagents/agent-<id>.jsonl` with a sibling `agent-<id>.meta.json` holding `agentType` and `isFork`
- tool calls are `message.content[].type == "tool_use"` with `name`, `input` and `id`; results are user rows with `tool_result` blocks, and an `image` block marks an image read

This is not a stable interface. The meter must fail loudly (exit 2, naming the missing field) rather than report zeros.

---

## 4. Interfaces

### 4.1 `cards` CLI (every subcommand)

These apply to every subcommand:
- **Common flags:** `--build <dir>` (required except for `state init` and `meter`) and `--help`.
- **Output:** stdout follows §6. Detail goes to files.
- **Caller restrictions:** no subcommand accepts a flag that skips a check, forces a write, or overrides the gate. Unknown flags exit 2.

| Command | Arguments | Writes | Exit 0 / 1 / 2 / 3 |
|---|---|---|---|
| `cards state init` | `<source path>` `--job build` | build folder, `build.json`, `builds/.current` | created or resumed / — / bad path / — |
| `cards state get` | `--build` | — | ok / — / corrupt / — |
| `cards state set` | `--build key=value…` (keys from `facts.*` only) | `build.json` | ok / — / unknown key / — |
| `cards state phase` | `--build <Pn> start\|done` | `build.json` history | ok / — / illegal transition / — |
| `cards state next` | `--build` | — | prints next phase, its entry condition, its command, and the phase file to load |
| `cards extract` | `--build` `[--slides 5-12]` | `source/*` | ok or cache hit / flags present / unreadable, encrypted or no text / — |
| `cards target` | `--build` `[--course --number --title]` `[--subject] [--system]` `--existing-decks <file>` | `target.json` | ok / not confident (prints one question) / bad input / extract not run |
| `cards source` | `--build` one of `--slides`, `--all`, `--grep <term>`, `--figure <id>`, `--page-image <n>` | `source/pages/pNN.png` for page images | ok / — / out of range / not extracted |
| `cards check` | `--build` | `checks/check.json` | clean / findings / malformed JSONL / — |
| `cards render` | `--build` `[--only ids]` `[--per-sheet 8]` `[--anki-html file]` | `renders/*` | ok / — / renderer failure / no drafts |
| `cards figures` | `--build` `--fig <id>` `[--keep 1,2]` `[--mode one\|all]` | figure crops, preview, one IO record appended to `drafts.jsonl` | ok / OCR found nothing (estimate by eye) / bad id / not extracted |
| `cards packets` | `--build` `--round <k>` `[--only ids]` | `review/round<k>/*` | ok / — / missing template / check has blockers |
| `cards apply` | `--build` `--round <k>` `[--decline id:reason …]` | `drafts.jsonl` (previous kept as `drafts.r<k>.jsonl`), `skipped.jsonl`, `apply_log.json` | ok / conflicts need a decision / malformed report / reports missing |
| `cards gate` | `--build` | `gate.json`, `build.json.gate` | passed / failed (reasons) / — / review not run |
| `cards write` | `--build` `[--direct]` | `write/*`; with `--direct`, the Anki writes | ok / — / hash mismatch / gate not passed |
| `cards report` | `--build` | `report.md`; removes `builds/.current` | ok / waste check failed / — / write not done |
| `cards meter` | `--session <id\|path>` or `--latest <project dir>`, `[--build]`, `[--line]`, `--out <dir>` | `cost.json`, `cost.md` | all waste checks pass / some fail / unreadable transcript / — |

### 4.2 Runtime surfaces (Claude Code, in `this repository`)

| Surface | File | Contract |
|---|---|---|
| Skill | `.claude/skills/anki2/SKILL.md` + `phases/*.md` + `templates/review/*` + `assets/coldrecall-cloze/*` | Frontmatter `name: anki2`, `model: claude-sonnet-5-5`, `effort: medium`. Core ≤ 10,000 characters. |
| Reviewer agents | `.claude/agents/anki-maintainer.md`, `anki-student.md` | Exactly as TRD C-7 |
| Runtime hooks | `.claude/hooks/*.py`, wired in `.claude/settings.json` | TRD C-6. Exit 2 with an instruction on stderr to block; exit 0 otherwise. |
| Project settings | `.claude/settings.json` | `model: claude-sonnet-5-5`, the hooks, and the lean-workspace exclusions (FR-25) |

**Hook input fields relied on** (Claude Code PreToolUse stdin): `tool_name`, `tool_input.subagent_type` (Agent), `tool_input.file_path` (Read), `tool_input.command` (Bash), and `cwd`. For the write guard, `$CLAUDE_PROJECT_DIR` is used, falling back to `cwd`.

---

## 5. State transitions

**Build phases** (in `build.json.phase`):

```
P0 Preflight → P1 Extract+target → P2 Draft → P3 Check+render → P4 Review → P5 Gate → P6 Write → P7 Report → done
```

- **Legal:** forward by one step; `P4 → P3` (round 2 re-render); `P5 → P4` (gate failed and a round remains); any phase to itself (resume).
- **Illegal:**
  - skipping forward (e.g. `P2 → P5`), so `cards state phase` exits 2
  - `P6` without `gate.status = passed`
  - anything after `done` except a new `state init`, which reuses the build if the source hash matches
- **Round counter:** starts at 1 at the first `cards packets`. `cards apply` with ≥ 1 change and round < 2 allows round 2. After round 2, `apply` marks remaining blockers `unresolved`.

**Gate status:** `pending → passed | failed`. `passed` goes stale the moment `drafts.jsonl`'s hash differs from `gate.drafts_sha256`; `cards write` and the runtime hook both treat stale as not passed.

**Note status:**
- `draft → fixed`, when a rewrite is applied
- `draft|fixed → dropped`, when rejected, or by Claude with a decline reason
- `draft|fixed → unresolved`, only when a blocker is still open after round 2

`dropped` is terminal and is moved to `skipped.jsonl` with `reason: rejected_in_review`.

---

## 6. Error and refusal semantics

**stdout shape:**
- Line 1 is `OK`, `FINDINGS` or `ERROR`.
- Then ≤ 40 lines and ≤ 2,000 characters of summary.
- Then one `→ <path>` line per file written.
- **Exceptions:** `cards source` prints the requested slice (budget = the slice), and `cards report` prints the report (≤ 25 lines).

**Exit codes:**

| Code | Meaning | Caller action |
|---|---|---|
| 0 | Done | Continue |
| 1 | Findings: a valid result that needs judgement (lint findings, gate failed, conflicts, not confident) | Read the summary, act, re-run |
| 2 | Error: bad input or broken environment | Fix the one thing named; don't retry blindly |
| 3 | Refused: precondition not met (phase not run, gate not passed, drafts changed) | Run the named earlier step |

**Error line format:** `ERROR E<code> <what failed> — <what to do>`, for example `ERROR E21 source not readable: file is cloud-only — make it available offline in Google Drive, then re-run`.

| Range | Area |
|---|---|
| E1x | state |
| E2x | source and extract |
| E3x | target |
| E4x | check |
| E5x | render and figures |
| E6x | review |
| E7x | gate and write |
| E8x | meter |

**Refusals are errors, never silent.** A forbidden or premature action exits 3 or 2 with a message. It is never accepted and ignored. This applies to: write before gate, packets with blockers, drafts changed after gate, an unknown flag, and a `facts` key that isn't allowed.

**Runtime hooks** block with exit 2. Their stderr names the rule and the allowed alternative in ≤ 3 lines. On any internal error (bad JSON, missing file), a hook exits 2 and says the check couldn't run (fail closed). The one exception is the write guard when no active build exists.

---

## 7. Configuration and pinning

- **`cards.toml`** (repo root, committed) holds:
  - `tag_root = "#ColdRecall"`
  - `note_type = "ColdRecall Cloze"`
  - `per_sheet = 8`
  - `student_all_sheets_max_pairs = 6`
  - `max_review_rounds = 2`
  - `self_review_max_changed = 8`
  - `lint` thresholds
  - `stdout_max_lines = 40`, `stdout_max_chars = 2000`
  - `deck_name_max_chars = 100`
  - `anki_url = "http://127.0.0.1:3141/"`, used only by `write/direct.py`
- **`meter/prices.toml`:** USD per million tokens for input, 1h cache write, 5m cache write, cache read and output, per model id.
  - `claude-sonnet-4-6` is set to the values used in the audit (3 / 6 / 3.75 / 0.30 / 15).
  - `claude-sonnet-5-5` is **left blank for the owner to fill** from Anthropic's pricing page. The meter never guesses a price.
- **Recorded with outputs:** the tool version in every file (G-7); `build.json.tools`; the model ids, read from the transcript by the meter.
- **Pinned in code review:** the model ids and effort levels in SKILL.md, the agents and `.claude/settings.json`. A test checks them (P6).
- **Lean workspace (FR-25, D-13).** Project `.claude/settings.json` in `this repository` sets:
  - `disableClaudeAiConnectors: true`, which drops the claude.ai connectors such as Firecrawl and Claude Docs (≈20k tokens per call in L006)
  - `deniedMcpServers` naming every MCP server except `anki` that the L006 session loaded (claude-flow, flow-nexus and the others listed in its `mcp_instructions_delta` / `deferred_tools_delta` rows)
  - `claudeMdExcludes: ["~/.claude/CLAUDE.md"]`, the ruflo text
  - `enabledPlugins: {<plugin>: false}` for plugins the build doesn't use
  Verify each key's exact JSON shape against `code.claude.com/docs/en/settings-reference` before writing it. Items that only user-level settings control go in `docs/lean-workspace.md` for the owner to change by hand: the ruflo hooks in `~/.claude/settings.json` and the ~90 agent definitions under `~/.claude/agents/`.
- **Secrets:** none. AnkiMCP is local and unauthenticated. The AMBOSS add-on token in note templates is stripped by the renderer (NFR-6).

---

## 8. Observability

- `cards state get` prints the phase, round, gate and counts in ≤ 8 lines.
- `builds/<id>/log.jsonl` records every command: exit code, duration and stdout size.
- `report.md` is the human-readable outcome; its last line is the usage line.
- `cards meter --latest this repository` after any session gives cost and waste, with evidence.
- **Build-time:** `bash .codex/tools/gate.sh <N>` prints each check and one final `GATE PASS` or `GATE FAIL`.

---

## 9. Open items

| Item | Forced by | Default if not decided |
|---|---|---|
| Q-1: can a Bash-run script reach AnkiMCP under auto mode with an allow rule? | Phase 0 spike; result recorded in `docs/decisions.md` | Inline writes through `mcp__anki__add_notes`, and `write/direct.py` is not built |
| Q-6: Python or Rust | Only if a subcommand misses G-11 | Python |
| Sonnet 5.5 prices in `prices.toml` | Phase 1 | Usage line shows `cost n/a` |
| AnkiMCP tool names for IO media (`store_media_file`) and suspend (`card_management` vs `card_suspend`) | Phase 5; read them from `list` in a Claude session | Use the names the L006 transcript shows: `mcp__anki__card_suspend` |
