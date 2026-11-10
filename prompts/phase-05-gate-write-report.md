# Phase 5: Automatic gate, write plan, report (`cards gate`, `cards write`, `cards report`)

> Paste into a **new T3 thread** (GPT-6.1 Sol · High · Auto) on branch `anki-v2`. Self-contained.

## Not in this phase

- **No human approval step anywhere** (ADR-9). Equally, nothing may skip the automatic gate: no flag, env var or config key.
- Build `write/direct.py` **only if** `docs/decisions.md` → "Q-1 result" says both probes passed. Otherwise don't create the file at all.
- No SKILL.md or runtime hooks yet (Phase 6).

## Goal

A build that passed review is written exactly as reviewed, or not at all. The report ends with the usage line.

## Requirements in scope

- **FR-17**: gate
- **FR-18**: write plan
- **FR-19**: direct mode, only if Q-1 passed
- **FR-20**: import file
- **FR-21**: report
- **FR-27**: usage line
- **CON-9**

## Read first

- `docs/anki-v2-trd.md` T-9, T-10, T-12, D-12, D-13, D-14
- `docs/design-spec.md` §3.7, §3.8, §3.9, §4.1 (`gate`, `write`, `report` rows), §5 (gate status, staleness), §6 (refusals)
- `docs/decisions.md` (Q-1 result)
- `$claude-code-runtime`: the AnkiMCP section, for the `add_notes` argument shape and limits
- `docs/test-contract.md`: the Phase 5 table

## Build

1. **Gate:** `src/cards/gate.py` and `cards gate`.
2. **Write plan:** `src/cards/write/plan.py`, `importfile.py`, and `cards write`. If Q-1 passed, also `direct.py` and `--direct` (the only network module; `127.0.0.1:3141` only).
3. **Report:** `src/cards/report.py` and `cards report`. It calls the meter on the current session for the usage line, then removes `builds/.current`.

Write the Phase 5 contract tests first, show red, then implement.

## Definition of done

1. These pass, and failed before:
   - `test_fr17_gate_passes`, `test_fr17_gate_fails_on_fail_verdict`, `test_fr17_gate_fails_on_open_blocker`, `test_fr17_gate_no_bypass`
   - `test_fr18_write_refused_before_gate`, `test_fr18_write_refused_after_drafts_change`
   - `test_fr18_batches_shape`, `test_fr18_suspend_list`, `test_fr18_expected_counts`
   - `test_fr20_import_file_format`
   - `test_fr21_report_short`, `test_fr27_report_usage_line`
   - the G-tests re-applied to this phase's new subcommands (see the test-contract header)
   - all earlier phases still pass
2. Run `contract_auditor` (phase 5), `boundary_auditor` (gate-integrity check especially) and `token_auditor`; fix their findings.
3. Report: the `cards write` plan for the converted v1 L006 drafts (counts, batch files), and a sample `report.md`.

## Gate (the owner runs this)

```
bash .codex/tools/gate.sh 5
```

Then, by hand:

1. Import `write/import.txt` for the converted L006 drafts into a **scratch Anki profile** (File → Switch Profile → Add) with File → Import. It must need no settings (`char_fr20_imports_into_anki`).
2. If `--direct` exists, run it against the scratch profile too.
3. Freeze and commit.

## Stop

Stop at the definition of done and report. Don't begin Phase 6.
