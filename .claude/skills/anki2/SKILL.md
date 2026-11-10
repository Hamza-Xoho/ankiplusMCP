---
name: anki2
description: Use when asked to "card this", "make cards", or /ankiv2 with one lecture PDF, or resume that card build. The `cards` CLI owns the pipeline: run `cards build --pdf <path>`, do exactly what each pause prompt says, then run `cards build --continue`. HARVEST and repair use the separate /anki skill. Not for general Anki questions.
model: claude-sonnet-5-5
effort: medium
---

# Anki2

## Purpose

Make AnKing-quality cards from one lecture's own terms. `cards build` owns the pipeline; the agent acts only at its pauses. Judgement drafts, independent reviewers check, and Anki MCP executes the validated write plan.

## Job router

- **BUILD:** one lecture PDF or slide range. `cards build --pdf "<PDF>"`. Multiple PDFs or a merged/combined PDF: stop — one build per lecture. Never merge PDFs or hand-edit the build.
- **Resume:** same source already has a `build.json`; run `cards build --resume`, then follow the resume rule.
- **HARVEST / REPAIR:** not in v1.0; use the separate `/anki` skill if installed.

**Before the first command**

`cards build --pdf` silently resumes any build whose source has the same hash, so look first (read-only):

1. Run every `cards` command from one folder, the one you were started in. Never `cd` into the skill folder or the `cards` repo; builds go to `./builds` (or `$CARDS_BUILDS`) of the current folder, and `--continue` only finds them from there.
2. `grep -l "<PDF file name>" "${CARDS_BUILDS:-builds}"/*/build.json`. If a build exists, read its `phase`, `gate.status` and whether `write/receipts.json` exists.
3. Resume it only if it is in progress and healthy. If the gate failed, inspect findings and use only legal remaining review work. Reconcile any ambiguous writes before continuing. Ask before moving an existing build aside for a fresh run. Never start over on your own.
4. To inspect a build: `cards state get --build <build>` (`<build>` is the folder named in `<builds>/.current`). There is no `state show`.

## Invariants

- **Runtime-agnostic:** `tools.anki.X` (OpenCode) and `mcp__anki__X` (Claude Code) are the same Anki MCP tools. Call `cards` from PATH; if missing, stop and give the install command. In Codex launch fresh general subagents with no inherited conversation: maintainer at high reasoning effort, student at medium. Each packet defines its role and report format. In other hosts use `anki-maintainer`/`anki-student`. Supply only the packet `PROMPT.md` path; never send author reasoning or summaries.
- Writes happen without asking once `cards gate` passes (ADR-9), except where a write hook is absent and the plan is confirmed once. Both reviews must pass and the drafts hash must match; never bypass a refusal.
- Source comes only through the CLI: `source/slides_summary.json`, `cards source --slides N`, `cards figures --summary`. Never Read a PDF. Inspect extracted figure PNGs when choosing masks, then generated `*_preview.png` files to check them.
- Preserve terms, hedges and scope; add nothing from general knowledge.
- Every tag is under `#ColdRecall::`. Never write into AnKing's tags or note types; propose unsuspends instead of duplicates. Suspend/unsuspend take **card** ids from `notes_info`.
- Never claim a failed write succeeded; never delete notes without an explicit request.
- Draft once as a batch; review changes go through `cards apply --round N`, never note-by-note edits.
- Never edit the skill, the `cards` package, `build.json` or `target.json` to pass an error. Diagnose errors read-only and follow the bounded recovery rules below.
- Keep working files inside the build. Sources, the lecture folder and the vault are read-only.

## Token discipline

- Use pause prompts and command summaries first; inspect the smallest relevant source or diagnostic file when needed.
- Use `cards source --slides N` or `--grep "term"`; never re-read `source --all` after P2.
- Keep artefacts in files; pass paths, never contents, in prompts.
- Use `notes_info` with a field subset and cap `find_notes`; never echo `drafts.jsonl` or `apply_log.json`.
- Batch independent calls; launch both reviewers in one message.

## Phase map

Run `cards build --pdf "<PDF>"`. It runs P0, P1, P3, P5 and P7 itself and stops with a prompt at P2, P4 and P6. Do what the prompt says, then `cards build --continue`. The table records what each phase runs; never run a mechanical phase by hand between pauses.

| Phase | Entry condition | Exact commands / actions | What to read | Exit condition | Phase file to load |
|---|---|---|---|---|---|
| P0 Preflight | Source supplied | `.venv/bin/cards state init "<PDF>"`; the build prints the MCP checks and `.venv/bin/cards state set` line | `build.json` first | Anki reachable; Cloze model exists | None |
| P1 Extract + target | P0 complete | `.venv/bin/cards extract`; `.venv/bin/cards target`; MCP `create_deck` if missing | `source/map.md`, `target.json` | Confident flat target deck | None |
| P2 Draft | Paused at P2 | `.venv/bin/cards source --build <build> --all` once; `drafts.jsonl` and `skipped.jsonl` in one Write each; `cards figures --summary` | `slides_summary.json`, `phases/draft.md` | Objectives covered; omissions recorded | `phases/draft.md`; `phases/occlusion.md` for images |
| P3 Check + render | Drafts ready | `.venv/bin/cards check`; `.venv/bin/cards render` | Findings summary | No blockers; renders exist | None |
| P4 Review | Renders ready | `.venv/bin/cards packets`; `.venv/bin/cards apply`; launch `anki-maintainer` and `anki-student` in one message with a `PROMPT.md` path only | Apply summary only | Both Markdown reports applied; conflicts resolved | None |
| P5 Gate | Review applied | `.venv/bin/cards gate`; failure stops with exit 1 and no writes | Gate summary | Gate passed on current drafts; continue without asking | `phases/write.md` |
| P6 Write + verify | Gate passed | `.venv/bin/cards write`; `tools.anki.add_notes` per batch; media, updates, suspend and verify per expected.json | `write/expected.json` | Counts and verify match expected; receipts | `phases/write.md` |
| P7 Report | P6 done | `cards build --continue` (internally runs `.venv/bin/cards report` and closes; internal terminal transition: `.venv/bin/cards state phase --build <build> done start`; never run manually) | Report once | Report delivered; build closed | `phases/write.md` |

## Resume rule

Read `build.json` first, before any phase file. `cards build --resume` or the same `--pdf` restores the active build and continues from its phase; inspect `phase`, the last `history` entry, `review`, `gate` and `write`. Never replay a completed build.

Never replay extraction, `source --all`, or `phases/draft.md` past P2; in interrupted P2 use existing drafts and targeted slices. In P4 reuse finished reports and launch only missing reviewers. In P6 reconcile receipts before retrying: never resend a successful batch; stop if success is ambiguous.

## Stop conditions

- Exit 0: continue. Exit 1: address findings within the review limit. Exit 2: diagnose read-only; retry once only for a demonstrably non-mutating argument/lookup error, using verified arguments. If the retry fails, stop. Never blindly retry.
- Unknown figure (E23): obtain exact `fig_id` values from `source/slides.json` for that slide (or `cards figures --build <build> --summary`); retry the lookup once with the returned ID. Never derive IDs from slide numbers. If no figure exists, inspect the slide PNG and make a source-grounded drafting decision; do not invent a figure.
- Report format error (E61): use the reviewer-repair procedure below, not the lookup retry. A refusal (exit 3) requires its named prerequisite; continue only if it can be satisfied within the legal phase and existing authorization. Never bypass a gate or conflicting-figure refusal.
- For failed/ambiguous Anki writes, permissions, unreadable sources, or unexplained tool failures: stop, preserve evidence, and report the command, error, absolute build path, phase, and confirmed write counts. Ask the student only for information or action they can actually provide; internal IDs and phase commands are the agent's responsibility.
- Failed gate: no writes. Report the reasons and artefact paths; return to review only if the CLI allows another round.
- Usage limit or interruption: keep state, drafts, reports and receipts; report build path, last completed phase and next action; resume with `cards build --resume`.
- Unreadable or cloud-only source: stop and ask for an offline copy. Permission error: report it; never claim completion or switch transports.

**Review recovery**

If `cards apply` returns E61, send the exact error and the existing packet path
back to the same reviewer to repair only its report. Preserve all findings and
committed answers. Retry after that repair; if it fails again, stop with the
error. The author must never delete findings or rewrite reviewer reports.
This formatting repair does not consume another review round.

At P6 load `phases/write.md` before any Anki operation. Pass generated batch
contents directly to the MCP tool. Persist actual tool responses immediately;
never infer IDs from ranges. Do not change fields after the gate. If Anki
renames media, stop before adding affected notes and report the mismatch.
Finish with `cards build --continue`; never manually advance phases.
