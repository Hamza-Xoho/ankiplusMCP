# Decisions

## Q-1 result

char_fr3_l007_label_recall — pending, labels file not yet supplied

## Phase 3 schema codes
The spec names S01–S09 without assigning fields. Phase 3 uses S01 record/required fields; S02 unique id; S03 kind/status/action/nid; S04 fields; S05 tier; S06 tags (required source/tier); S07 source_ref; S08 target deck/notetype; S09 objective/group and skip records. Schema violations are blockers; malformed JSON exits 2.

## Exception: test_c6_settings_wiring edited before freeze
The owner moved the Anki write tools (add_notes etc.) from `ask` to `allow` so headless runs don't stall (ADR-9). The one assertion in `tests/contract/test_p6_runtime.py` that expected `mcp__anki__add_notes` in `permissions.ask` now expects it in `allow`. Done with the owner’s approval, before the contract was frozen.

## Q-1 result

`.venv/bin/python tools/q1_probe.py` (2026-11-06, from Claude Code on this Mac): `Q1 OK: 60 tools`. Decision unchanged: writes stay on `mcp__anki__add_notes`; `--direct` is not built.

## Run 1 (L006), usage vs v1 baseline
v1 baseline: about $9 API-equivalent, 76 calls, peak 166k context.
v2 (headless Sonnet 5.5, build stopped at the P5 gate, so the figure covers P0–P5 only, not writes or report):
`Usage: 31 calls · peak 132k · cost n/a (no price for claude-sonnet-5-5) · waste checks 8/8 pass`
- First-call context 58,619 vs the Phase 1 reference 79,270: 20.6k lower (target was at least 10k).
- Subagents: 2x anki-maintainer, 2x anki-student, fork=False for all four. No fork.
- W-1…W-8 all PASS.
- Gate: FAILED after round 2 (maintainer FAIL, student FAIL, 7 conflicts: n008 n013 n018 n023 n044 n051 n054; set findings open). Nothing written to Anki. The old v1 notes (40) untouched.
- Fixes made during Run 1: SKILL.md (extract timeout, existing-decks as string array); `rejected_in_review` accepted by `cards check`; `cards meter` tolerates subagent meta without `isFork`; maintainer report-format states that note records use A-codes and set records S-codes.

## Run 1 (L006), completed attempt (session f65e1cda, 2026-11-06)
`Usage: 72 calls · peak 182k · cost n/a (no price for <synthetic>, claude-sonnet-5-5) · waste checks 7/8 — W-5 failed (retry after error or local-port workaround)`
- vs v1 baseline (about $9, 76 calls, peak 166k): calls slightly lower, peak context higher (182k vs 166k). Includes the resume after the usage limit.
- Gate passed after round 2. 55 notes written (32 tier 1, 20 tier 2, 3 tier 3), 11 suspended (3 tier-3, 8 `Review_unresolved`). Read-back in Anki matched: 55 by source tag, 11 suspended. Old v1 notes untouched.
- Headless run stopped at P6 because the build.json edit was refused; P6/P7 bookkeeping and `cards report` were finished interactively (write evidence merged with one python read/merge). `cards report` meters the current session, so its usage line was not used here.
- Findings: maintainer `rewrite` fields rejected by `cards apply` each round (placeholder "unchanged" and a tags key); report-format template says "unchanged" is allowed but the validator rejects it. Report format cannot change a tier (n030). These retries are the W-5 failure.

## Run 1 (L006) final, after the gate and skill fixes
Build finished through P7: deck `Histology of Endoplasmic reticulum, Mitochondria & Golgi Apparatus (MED241 L006)`, 55 notes written (tiers 32/20/3, tier-3 share 5%), 11 suspended (3 tier-3 + 8 unresolved after round 2, tagged Review_unresolved), no Anki write error. The 40 v1 notes were not touched.
Usage, whole headless session including two resumes (usage-limit stop and the build.json step), `cards meter --session`: 79 calls, peak 182k, cost n/a (no price for claude-sonnet-5-5). v1 baseline: about $9, 76 calls, peak 166k. First-call context 58,628 (20.6k under 79,270). The usage line printed in report.md (19 calls, peak 124k) covers only the part of the session that existed when `cards report` ran, so it understates.
Waste checks: W-5 FAILED (6 rows): `cards packets` run twice (E60: page images for flagged slides not made first), `cards apply` rerun three times because maintainer reports had an invalid `rewrite` field (E61), and a Bash/Edit permission refusal on build.json. W-1..W-4, W-6..W-8 pass.
SC-6 pass. SC-8 pass (3x anki-maintainer, 2x anki-student, no fork). SC-1 fail (W-5). SC-4 not fully checked: tier-3 share shown, no open blocker outside unresolved notes; per-objective tier-1 coverage not verified.
Fixes made on the way: the build.json merge is a .venv/bin/python merge (Edit is refused headless).
Open: reviewers' `rewrite` objects must hold only Text/Extra strings (tags key and placeholder text are rejected); packets need page images made before they run; n030 stays tier 3; the two empty decks from earlier attempts remain in Anki (not deleted by rule).

## Runs 2 and 3 (L007), stopped at P4 round 1 (2026-11-06)
- Run 2 (session e161bd49): stopped at P1 because `All::MED241::7. Anatomy of the pectoral region` already held 44 notes. The owner chose rebuild into the new flat deck, old notes untouched. Resumed, killed once `review/round1/` existed at P4.
  `Usage: 21 calls · peak 112k · cost n/a · waste checks 8/8 pass`
- Run 3 (new session a8f13c40, `/anki2` + same PDF): resumed from `build.json`; no `extract`, no `source --all`, only `--page-image` reads of 15 flagged slides. SC-7 behaviour PASS. Round 1: both reviewers PASS_WITH_FIXES, 12 rewrites applied, 1 conflict (n014).
  `Usage: 30 calls · peak 82k · cost n/a · waste checks 7/8 — W-5 failed (retry after error or local-port workaround)`
- Stopped by the owner’s decision, nothing written to Anki. Blocker: the maintainer's rewrite of n004 has 7 clozes, lint L04 allows 5, and `cards apply` cannot repair it so `cards packets --round 2` refuses. Finding: a rewrite can violate lint and the pipeline has no repair path.
- Maintainer found all 38 drafts duplicate the 44 existing notes sharing the L007 ColdRecall source tag; these would become updates. The owner’s decision for the write phase: create new notes, leave the old 44 untouched (duplicates remain active until he decides). n038 also overlaps AnKing note <AnKing note id>.
- L007 is not finished; DoD for L007 (occlusions, report, usage vs baseline) remains open.

## Fixes after Runs 1–3, and final L007 run (2026-11-06)
- `cards apply`: `rewrite` may be the string "unchanged" (treated as null); a `Tags` key is ignored; fields marked "unchanged" are dropped; other unknown keys still invalid. A rewrite that would add a lint blocker is not applied: the draft is kept, the note is recorded as a conflict with `lint_rejected` codes and goes to round 2. Reviewer report-format templates say so.
- `cards state record-write`: records created/updated/suspended/skipped_duplicate/errors/status from `write/receipts.json` and `review.independent` from the round's two reports; refuses on any failed batch. `write.md` step 7 and the SKILL P6 row point to it; no hand edit of `build.json`.
- `cards report`: accepts `created + skipped_duplicate == planned` so notes refused by Anki's duplicate guard (identical text to existing notes) no longer block the report; any other count gap still refuses (E72).
- Final L007 run (fresh build; session 0c67d05a, resumed once after the 4-duplicate decision): `cards apply` passed both rounds with no rewrite retries; 29 of 33 notes created, 4 skipped as duplicates of existing old notes (n005 n028 n029 n030, the owner chose skip), 1 suspended (tier-3 n004), 44 old notes untouched, read-back matched. Usage `74 calls · peak 167k · waste checks 8/8 pass` (v1 baseline about 76 calls, peak 166k).
- Open: L007 produced 0 image-occlusion notes (15 slides flagged for figures); the DoD says L007 with occlusions, so this is not met. Skip reasons used `other` for the duplicate skips because `covered_by` only accepts a draft id.

## Why L006 and L007 had no image-occlusion notes
Finding: the draft phase only advised "enumerate figure candidates … record why any are skipped" and nothing enforced it. L007 had 23 figures with five or more OCR labels and L006 had 16; neither build made an io note or any figure-level skip record, and the drafter never loaded `phases/occlusion.md`. Fix: `cards check` now raises blocker C05 for a slide with a figure of five or more OCR labels (not low_text/objectives) that has neither an io note nor a skipped.jsonl record whose item mentions figure/image/diagram. On the finished L007 build a copy of the check reports 14 such slides. `phases/draft.md` states the rule. Not yet re-run end to end, so occlusion output quality is unverified.

## Packaged as the global skill `ankiv2` (2026-11-06)
`scripts/package_ankiv2.py [--install]` builds `dist/ankiv2` (and `dist/ankiv2.zip`) and installs the skill to `~/.claude/skills/ankiv2` and `~/.config/opencode/skills/ankiv2`, with the two reviewer agents converted for each runtime. The packaged skill calls `cards` from PATH, not this repo's `.venv`; install the CLI first (`uv tool install .` or `pipx install .`). Claude-specific model/effort fields are stripped, and the OpenCode agents are Markdown subagents with edit limited to `**/review/**`. `cards state init` defaults to `./builds`; `CARDS_BUILDS` moves it. The `anki` MCP server is project-scoped in `.mcp.json`; for use outside this repo it must be added at user scope. The project hooks (PDF-read, fork, local-port and review-before-write guards) do not apply outside this repo. `anki2` stays as the development copy; re-run the script after changing it.

## Public release decisions (v0.1.0, 2026-11-06)
- **Sources:** one lecture per build. `state init` refuses filenames that name multiple lectures or say merged/combined/compilation; the skill refuses requests to merge PDFs. Multi-lecture provenance is v1.1.
- **Runtimes:** Claude Code and OpenCode. Codex is deferred. Runtime differences are documented in the skill's Invariants and the README.
- **Write safety:** `cards gate` and `cards write` are the fail-closed checks in every runtime. Only Claude Code has a hook over the Anki MCP write tools; OpenCode relies on `cards write` plus one confirmation of the plan.
- **Deck identity:** the frozen contract still derives a single-lecture deck from slide 1; `cards target --course/--number/--title` is the supported override, and the skill never hand-edits `target.json`.
- **Prompt budget:** `packets` writes `pages/images.md` and the prompt names the manifest, so a long lecture cannot overflow the 300-token prompt by listing images.
- **AnKing overlap:** `reconcile.md` searches lecture-number tag shapes such as `W4::4-Wed::L029`, not only ColdRecall source tags and slide titles.
- **Packaging:** reviewer templates and ColdRecall assets are vendored in `src/cards/` with package-data, so a wheel works outside the checkout. A unit test keeps the packaged copies in sync with the skill.
- **License:** MIT.
