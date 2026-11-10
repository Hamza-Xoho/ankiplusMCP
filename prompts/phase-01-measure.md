# Phase 1: Measurement (`cards meter`) and the lean Cards workspace

> Paste into a **new T3 thread** (GPT-6.1 Sol · High · Auto) on branch `anki-v2`. Self-contained.

## Not in this phase

- No report integration. `cards report` comes in Phase 5; here `meter --line` only prints the line.
- No runtime hooks, skill, or agents in `.claude/`. The **only** `.claude/` file you may touch is `.claude/settings.json`, for the lean keys.
- Don't modify transcript fixtures.
- Don't fill in prices you don't have: `claude-sonnet-5-5` stays blank (spec §7).

## Goal

`cards meter` reads a Claude Code session (main transcript + subagents). It reproduces the L006 audit numbers, judges waste checks W-1 to W-8 with evidence, and prints a one-line summary. The Cards workspace stops loading what `/anki2` doesn't need.

## Requirements in scope

- **FR-24**: the meter
- **FR-27**: line mode only
- **FR-25**: lean workspace
- **ADR-10**: waste checks, not cost targets (brief §6 has the W table)

## Read first

- `docs/anki-v2-brief.md` §6 (the waste-check table)
- `docs/anki-v2-trd.md` T-13
- `docs/design-spec.md` §3.9, §3.11, §7 (prices, lean workspace)
- `$claude-code-runtime`: "Session transcripts" and its L006 baseline list
- `docs/test-contract.md`: the Phase 1 table

## Build

1. **Meter package:** `src/cards/meter/`:
   - `transcript.py`: parse; one usage per `message.id`; find subagents; fail loudly on a missing field
   - `waste.py`: W-1 to W-8, each a pure function returning `(pass, evidence[])`
   - `prices.py` + `prices.toml`
2. **Command:** `cards meter` per spec §4.1. Session from `--session` or `--latest <project dir>`. Writes `cost.json` and `cost.md`. `--line` mode.
3. **Synthetic fixtures:** `tests/fixtures/transcripts/` holds `clean.jsonl` plus one file per waste pattern, each minimal and hand-written.
4. **Lean workspace:**
   - Read the L006 transcript's attachment rows (`mcp_instructions_delta`, `deferred_tools_delta`, `skill_listing`, `agent_listing_delta`) to list what loaded.
   - Write the lean keys into `this repository/.claude/settings.json`, keeping every existing key.
   - Write `docs/lean-workspace.md` listing what only user-level settings can remove, with the exact files and lines for the owner.

Write the Phase 1 contract tests first (`tests/contract/test_p1_meter.py`, `test_p1_workspace.py`), show red, then implement.

## Definition of done

1. These pass, and failed before:
   - `test_fr24_usage_counted_once_per_message_id`
   - `test_fr24_reproduces_l006_baseline`
   - `test_fr24_l006_fails_every_waste_check`
   - `test_fr24_clean_session_passes`
   - `test_fr24_waste_check_detects[W-1..W-8]`
   - `test_fr24_unknown_price_not_guessed`
   - `test_fr24_missing_field_exit2`
   - `test_fr27_line_mode_one_line`
   - `test_fr25_cards_settings_lean`
   - the G-tests re-applied to `meter` (see the test-contract header)
   - all Phase 0 tests still pass
2. Run `contract_auditor` (phase 1) and `boundary_auditor` as subagents; fix their findings.
3. Report: the meter's output on the L006 fixture (the `cost.md` summary, ≤ 20 lines) and the lean-workspace changes.

## Gate (the owner runs this)

```
bash .codex/tools/gate.sh 1
```

Then, by hand:

1. Fill in `claude-sonnet-5-5` prices in `src/cards/meter/prices.toml` from Anthropic's pricing page.
2. Open a fresh Claude Code session in `this repository`, say "hi", close it.
3. Run `.venv/bin/cards meter --latest this repository --out /tmp/m`. Record its first-call context in `docs/decisions.md` (`char_fr25_first_call_drop`: ≥ 10k below 79k).
4. Do the user-level steps in `docs/lean-workspace.md` that you're happy with.
5. Freeze and commit.

## Stop

Stop at the definition of done and report. Don't begin Phase 2.
