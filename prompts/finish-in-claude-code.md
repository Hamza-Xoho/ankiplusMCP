# Finish anki-v2 in Claude Code

You are finishing the anki-v2 build in `<repo>`. This folder is now the main copy and also the live Anki workspace: it replaces `this repository` for everything below. Wherever a doc says `this repository`, use this folder.

Codex built phases 0–6. On this Mac `bash .codex/tools/gate.sh 6` passes (348 tests, hooks 42/42). Nothing is committed and the contract isn't frozen. The checks that need a real Claude Code session were never run.

**Already done before this session started:**
- `.mcp.json` was copied from `this repository`.
- In `.claude/settings.json`, the Anki write tools moved from `ask` to `allow`: add_note(s), update_notes, update_note_fields, create_deck, card_suspend, tag_add and store_media_file. Deletes, tag removal, model edits and deck moves stay under `ask`.
- `Bash(.venv/bin/cards:*)` is allowed.
- `.venv` is a fresh Mac venv.

Read `AGENTS.md`, `docs/test-contract.md` (skim) and `prompts/phase-06-runtime-skill.md` and `prompts/phase-07-acceptance.md` before starting. Use a task list.

## Rules (apply throughout)

1. **Frozen files.** Never edit `tests/contract/**`, `docs/test-contract.md`, `tests/fixtures/**` or `.codex/**`. Code fixes go in `src/` with a new test in `tests/unit/` written first. After any code change, `bash .codex/tools/gate.sh 6` must pass before you commit.
2. **Private material.**
   - Never commit `tests/fixtures/private/`, `builds/` or anything containing the lecture PDFs or session logs.
   - Before every commit, run `git diff --cached --name-only | grep -E 'private|^builds/|\.pdf$|\.zip$'`. It must print nothing.
3. **Read-only.** Leave `.claude/skills/anki/` (v1) unchanged. Never write into the lecture folder or `<your notes vault>`.
4. **Anki.**
   - Reach Anki only through `mcp__anki__*`, never curl or scripts.
   - Never delete notes, decks or note types.
   - Anki must be open with AnkiMCP running. If it isn't reachable, stop and tell the owner.
5. **Deleting files.** Don't delete anything. Move unwanted files to `~/Code/anki-v2-archive/` instead.
6. **When something fails twice, stop.** Report what failed, the evidence and your best diagnosis. Don't work around a hook, a permission refusal or a failing test.

## Part 1: tidy, small fixes, commit, freeze

1. **Clean the repo.**
   - Move these to `~/Code/anki-v2-archive/`: `anki-v2-buildkit/`, `anki-v2-buildkit.zip`, `anki-v2-t3-setup/`, `anki-v2-t3-setup.zip`, `build/`, `usage.json/` and `.venv-from-linux/`.
   - Unstage the kit copies with `git rm -r --cached anki-v2-buildkit anki-v2-buildkit.zip`, plus any other moved path that is staged.
   - Add `.DS_Store` and `.mcp.json.local` to `.gitignore`.
   - `.claude/settings.hooks.json` shows as added then deleted, because its hooks now live in `settings.json`. Unstage it.
2. **Stop P1 fetching the note type (token waste).**
   - `cards render` already falls back to the shipped `.claude/skills/anki2/assets/coldrecall-cloze/` when `<build>/model/` doesn't exist.
   - In `.claude/skills/anki2/SKILL.md`, remove the instruction to save `model_templates`/`model_styling` under `model/` (line ~56), and remove "model HTML/CSS saved under `<build>/model/`" from the P1 row (line ~48).
   - Replace them with one short line: render uses the shipped assets; fetch the live templates only if the owner says the note type changed.
   - Check that no other phase file tells Claude to fetch them. Keep SKILL.md under 10,000 characters.
3. **Fix `CLAUDE.md`.** It says to rebuild the venv with `scripts/setup.sh`, which doesn't exist. Replace that with the README's commands: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`.
4. **Fix the deck-name spacing.**
   - On L006, `cards target` produces "Histology of Endoplasmic reticulum, Mitochondria& Golgi Apparatus". The `&` has lost its space.
   - Find where the slide-1 title is normalised. Add a unit test first: `"Mitochondria& Golgi"` → `"Mitochondria & Golgi"`, and the same for a missing space on either side of `&`. Then fix it.
   - Don't change any other part of the naming.
5. **Run `bash .codex/tools/gate.sh 6`.** It takes about 6 minutes and must pass.
6. **Commit everything that belongs in the repo**, after the rule-2 check:
   - `src`, `tests` (minus private), `docs`, `prompts`, `tools`, `.claude`, `.codex`, `.agents`, `.mcp.json`
   - `AGENTS.md`, `CLAUDE.md`, `README.md`, `pyproject.toml`, `requirements.lock`, `cards.toml`, `.gitignore`
   - Message: `anki-v2: phases 0-6 (Codex build) + Claude Code finishing fixes`.
7. **Freeze.**
   - Run `bash .codex/tools/freeze_contract.sh`, then `bash .codex/tools/gate.sh 6` again. Confirm it now reports the contract as frozen and matching.
   - Commit `.codex/contract.sha256` with the message `freeze test contract`.

## Part 2: live checks in this session

This session started in this folder, so its hooks and the `anki` MCP server are live. Record each result, with the exact block message where there is one, in `docs/phase6-runtime.md` under a new `## Live checks (Claude Code)` heading.

1. **Q-1.**
   - Run `.venv/bin/python tools/q1_probe.py` and write its output under `## Q-1 result` in `docs/decisions.md`.
   - Whatever it says, writes stay on `mcp__anki__add_notes`. Don't build `--direct`.
2. **The hook checks** from the phase-06 gate. Each one must be blocked by the hook, not by a permission prompt:
   1. Run `.venv/bin/cards state init "tests/fixtures/private/MED241_L006_2026-09-13_endoplasmic-reticulum-mitochondria-and-golgi-apparatus.pdf"`, then try to Read that PDF with the Read tool. It must be blocked with the `cards source` message.
   2. Try to launch a fork subagent to summarise `docs/`. It must be blocked.
   3. Try `curl http://127.0.0.1:3141/`. It must be blocked.
   4. Try `mcp__anki__add_notes` with one ColdRecall Cloze note to the deck `ZZ hook test`. It must be blocked, because the gate hasn't passed.
      - If it is **not** blocked and a note is written, stop. Tell the owner the note id, and don't delete it.
   5. Run `rm builds/.current`, then Read `README.md`. Nothing should fire.
3. **Remove the test build.** Move the build folder that step 1 created (`builds/2026-11-*_MED241-L006`) to the archive. Otherwise the acceptance run would resume it instead of starting fresh.
4. **Commit** the doc updates.

## Part 3: acceptance runs, headless

Each run is a separate headless Claude Code session, so it measures like a real fresh chat and runs unattended. That is the point: nothing may ask for permission.

**How to launch a run:**
```
ID=$(uuidgen | tr A-Z a-z)
env -u CLAUDECODE claude -p "/anki2 <absolute path to PDF>" --session-id "$ID" \
  --output-format stream-json --verbose > "builds/_runs/$ID.jsonl" 2>&1
```
- Run it with `run_in_background`. Make `builds/_runs/` first; `builds/` is gitignored.
- Use the settings' default model (Sonnet 5.5). Don't pass `--model` or a permission mode.
- Poll every few minutes: check that the process is still alive, and read the build's `build.json` phase with `.venv/bin/cards state get --build <build>`.
- Don't read the stream file in full. Use `tail -c 2000` on it if you need to see the end.
- If the run ends by asking the one target question (course, number, title), answer it from the filename with `claude -p --resume "$ID" "<answer>"`, the same way.
- If it stops on a permission refusal, record which tool and which command. Add an allow rule only if the skill legitimately needs that command, then re-run.

**After each run, meter it with its own session:**
`.venv/bin/cards meter --session "$ID" --build <build> --out <build>/meter`. Don't use `--latest`: this session's transcript is in the same project folder.

### Run 1: L006
- Run `/anki2` on `tests/fixtures/private/MED241_L006_…golgi-apparatus.pdf`, using its absolute path.
- Check the rows from `prompts/phase-07-acceptance.md`:
  - **SC-1:** W-1…W-8 all pass in `cost.md`.
  - **SC-4:** in `report.md`, every objective has a tier-1 note, the tier-3 share is shown, and no active note has an open blocker.
  - **SC-6:** no Anki write error; the deck was created in P1.
  - **SC-8:** the transcript shows `anki-maintainer` and `anki-student` and no fork. This also covers the phase-04 manual check.
  - **The phase-01 check:** the first-call context, which should be at least 10k below 79,270.
- Write the usage line next to the v1 baseline (≈ $9 API-equivalent, 76 calls, peak 166k context) in `docs/decisions.md`.
- **If a check fails:**
  - Find the cause in `src/` or the skill files, and fix it under the rules (unit test first, gate 6).
  - Then commit and re-run.
  - At most two attempts in total, then stop and report.

### Run 2: resume (SC-7), on L007
- Start `/anki2` on the L007 PDF in the background.
- When `builds/<L007>/review/round1/` exists (the packets are written), kill that process.
- Start a new headless session with a new `ID` and the same command.
- Meter that second session. It must show no `cards source --all` and no drafting, and it must carry on from `build.json`.

### Run 3: L007 to the end
- Let the Run 2 resume session finish the build. All SC rows must pass, including that the occlusion notes were written.
- `char_fr3_l007_label_recall` stays pending (no labels file yet), so say so; don't fake it.

Commit the doc updates after the runs. Never commit `builds/`.

## Part 4: stop and report

**Don't do Phase 7's final step:**
- no `CARDS_PDF_GUARD=always`
- no rename to `/anki`
- no merge to `main`

Those wait for the owner’s SC-5 comparison in Anki.

**Report in at most 25 lines:**
- commits made
- gate result and freeze status
- Q-1 result
- the five hook checks (pass/fail)
- for each run: pass or fail per SC row, the usage line against the v1 baseline, and the deck name
- anything you fixed, and anything still open

**Then list what the owner does himself:**
1. **SC-5:** in Anki, compare the new flat L006 deck with v1's `All::MED241::6. …` deck on fidelity, ambiguity, formatting and coverage.
2. Decide which of the duplicate L006 sets to suspend. Don't delete either.
3. Sync Anki.
4. If SC-5 passes, say "do the Phase 7 final step", and you'll do the rename, gate and merge.
