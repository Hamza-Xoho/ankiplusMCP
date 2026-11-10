# Phase 6: The `/anki2` skill and the runtime guards

> Paste into a **new T3 thread** (GPT-6.1 Sol · High · Auto) on branch `anki-v2`. Self-contained.

## Not in this phase

- Don't touch `.claude/skills/anki/` (v1). `/anki2` sits beside it.
- No HARVEST or REPAIR jobs (v1.1). The skill says so in one line and routes those requests to `/anki`.
- Don't put the rubric, the house-style rules or anecdotes in the SKILL.md core: they live in `templates/` and `phases/`.
- Don't weaken the four runtime guard scripts in `.claude/hooks/`. They already pass `.codex/tools/verify_hooks.py`; you wire them, you don't rewrite them.

## Goal

Claude Code in `this repository` runs `/anki2` + a PDF end to end. It is driven by a small skill core and phase files, with the runtime guards wired in.

## Requirements in scope

- **Brief §4b**: SKILL.md spec, intended outcome and contents (the main input)
- **FR-9**: house style loaded only at drafting
- **C-6**: guards wired
- **ADR-11**: model and effort pins
- **CON-9**

## Read first

- `docs/anki-v2-brief.md` §4b in full, plus §4 (the phase list)
- `docs/design-spec.md` §4.2, §5, §6
- `docs/anki-v2-trd.md`: the orchestration table, C-6, C-7
- `$claude-code-runtime`: Skills, Subagents, Hooks
- `docs/test-contract.md`: the Phase 6 table
- **Source material for the rules worth keeping:** the v1 `.claude/skills/anki/SKILL.md`. Port invariants and house style; drop anecdotes and token-budget prose (the code enforces those now).

## Build

1. **Skill core:** `.claude/skills/anki2/SKILL.md`, ≤ 10,000 characters.
   - Frontmatter: `name: anki2`, `description` (triggers per §4b), `model: claude-sonnet-5-5`, `effort: medium`.
   - Body, in order: purpose, job router, invariants, token discipline, phase map, resume rule, stop conditions.
   - The phase map is a table: phase → entry condition → exact `.venv/bin/cards …` command(s) → what to read → exit condition → phase file to load.
   - P2 says: run `cards source --all` once, read `phases/draft.md`, write `drafts.jsonl` and `skipped.jsonl` in one Write each.
   - P4 says: launch `anki-maintainer` and `anki-student` in one message, each with its `PROMPT.md` path only.
   - P5–P6: `cards gate`, then `cards write`, then the `add_notes` calls straight from each batch file's content (stage 1 inline) or `--direct`, then the suspend and verify searches from `expected.json`.
2. **Phase files:** `.claude/skills/anki2/phases/draft.md` (house style + tiering + draft schema summary), `occlusion.md`, `write.md`.
3. **Wire the guards:** merge `.claude/settings.hooks.json` into `.claude/settings.json`, keeping every existing key, including Phase 1's lean keys. Delete `settings.hooks.json` afterwards.
4. **Runtime rules:** update `CLAUDE.md` (runtime): replace the "Gate before writing … wait for yes" line with "Writes happen without asking once `cards gate` passes (ADR-9)". Point card work to `/anki2`.

Write the Phase 6 contract tests first: they run the shipped hook scripts with payloads, and parse SKILL.md and settings. The guard-script tests may pass at once, because the scripts already exist; the wiring and skill tests must be red first. Then implement.

## Definition of done

1. These pass, and failed before:
   - `test_c6_fork_blocked`, `test_c6_reviewers_allowed`
   - `test_c6_pdf_read_blocked_during_build`, `test_c6_pdf_read_blocked_always_mode`, `test_c6_pdf_read_allowed_without_build`, `test_c6_png_read_allowed`
   - `test_c6_local_http_blocked`, `test_c6_plain_bash_allowed`
   - `test_c6_write_blocked_before_gate`, `test_c6_write_blocked_stale_gate`, `test_c6_write_allowed_after_gate`, `test_c6_write_allowed_without_build`
   - `test_c6_fail_closed`, `test_c6_settings_wiring`
   - `test_skill_core_size`, `test_skill_frontmatter_pins`, `test_skill_core_no_rubric`, `test_skill_phase_map_complete`
   - `test_fr9_house_style_only_in_phase_file`
   - the G-tests re-applied to this phase's new subcommands (see the test-contract header)
   - all earlier phases still pass
2. Run `token_auditor` on `.claude/skills/anki2/` and `contract_auditor` (phase 6); fix their findings.
3. Report: the SKILL.md character count, the phase map table, and the settings diff.

## Gate (the owner runs this)

```
bash .codex/tools/gate.sh 6
```

Then, by hand, in a **fresh Claude Code session** in `this repository`. These prove the hooks are *wired*, not only that the scripts work:

1. `.venv/bin/cards state init "<L006 path>"`, then ask Claude to "Read <the L006 PDF>". It must be blocked, with the `cards source` message.
2. Ask Claude to "launch a fork subagent to summarise this folder". It must be blocked.
3. Ask Claude to "curl http://127.0.0.1:3141/". It must be blocked.
4. Ask Claude to add a test note with `mcp__anki__add_notes` to a scratch deck. It must be blocked (gate not passed).
5. Run `rm builds/.current`, then ask for a normal edit or Read of a markdown file. Nothing should fire.
6. Freeze and commit.

## Stop

Stop at the definition of done and report. Don't begin Phase 7.
