# Phase 7: Acceptance (the owner, in Claude Code; Codex only fixes what fails)

This phase is mostly yours. Codex threads are used only to fix a failure, one thread per failure, each pasting this file plus the failure.

## Run 1: L006

1. Make a fresh Claude Code session in `this repository` on the `anki-v2` branch.
2. Send `/anki2` with the L006 PDF attached. Don't reply unless it asks the one filename question.
3. When it finishes, run:
   ```
   .venv/bin/cards meter --latest this repository --out builds/<L006>/meter
   ```
4. Check:

| Check | Pass when |
|---|---|
| SC-1 | `cost.md`: W-1 to W-8 all pass |
| SC-4 | `report.md`: every objective has a tier-1 note, tier-3 share shown, no active note with an open blocker |
| SC-5 | In Anki, compare the new flat L006 deck with the v1 `All::MED241::6. …` deck. No category is worse: fidelity, ambiguity, formatting, coverage. |
| SC-6 | No Anki write error in the session. The deck was created in P1. |
| SC-8 | The transcript shows `anki-maintainer` and `anki-student` and no fork |

Note the usage line from the report next to the v1 baseline (≈$9 API-equivalent, 76 calls, peak 166k) in `docs/decisions.md`.

## Run 2: resume (SC-7)

1. Start `/anki2` on L007.
2. Stop the session once it reaches P4 (the packets exist).
3. Open a new chat and send `/anki2` with the same PDF.
4. It must continue from `build.json`. The meter must show no `cards source --all` and no drafting in the second session.

## Run 3: L007 (Definition of Done)

Finish the L007 build. All SC rows must pass, including occlusions.

## When everything passes

1. In `.claude/settings.json`, set `"env": {"CARDS_PDF_GUARD": "always"}`.
2. Make `/anki2` answer to `/anki`. The folder stays `anki2`, so the frozen tests keep pointing at the right files.
   - `git mv .claude/skills/anki .claude/skills/anki-v1`, and set its frontmatter `name: anki-v1`
   - in `.claude/skills/anki2/SKILL.md`, set `name: anki`
   - update `CLAUDE.md` to match
3. Run `bash .codex/tools/gate.sh 6` once more, then merge `anki-v2` into `main`.
4. Bump the brief to v1.0, with a changelog row and the measured result.

## If a check fails

Don't patch by hand. Open a T3 thread and paste:
- this file
- the failing check
- the `cost.md` waste section, or the relevant report lines

Ask Codex to find which phase's code is wrong. The fix goes through that phase's tests and gate (`bash .codex/tools/gate.sh <that phase>`, then 6) before you re-run acceptance.
