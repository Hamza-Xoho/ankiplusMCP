# Phase 0: Foundations and the Anki-access spike

> Paste into a **new T3 thread** (Codex · GPT-6.1 Sol · reasoning High · permission mode **Auto**), on branch `anki-v2`. Self-contained: assume no memory of anything else.

## Not in this phase (read this first)

- No subcommand except `cards state`. No extract, check, render or meter.
- Don't port any v1 script yet.
- Don't touch `.claude/` (the runtime) or `.claude/skills/anki/` (v1, still in use).
- No network code in `src/cards/` (INV-2). The Q-1 probe lives in `tools/`, outside the package.

## Goal

A working `cards` package with the shared CLI contract and `cards state`, plus a probe that tells us whether a script can reach AnkiMCP.

## Requirements in scope

- **G-1…G-11**: global CLI rules (TRD §G)
- **FR-2**: build folder, `build.json`, resume, `builds/.current`
- **INV-2**: no network imports in the package
- **Q-1**: spike for direct Anki access

## Read first

- `docs/design-spec.md`:
  - §1 (D-3, D-4, D-16, D-17, D-18)
  - §2
  - §3.1 and §3.10
  - §5 (the build-phase part)
  - §6
  - §7 (`cards.toml` only)
- `docs/anki-v2-trd.md` §G, D-1, T-1
- `docs/test-contract.md`: the Phase 0 table
- `$cards-cli-conventions`

## Build

1. **Packaging and config:**
   - `pyproject.toml`: package `cards`, Python ≥ 3.12, console script `cards`, `dev` extra with pytest.
   - `cards.toml` with the keys in spec §7.
   - `.gitignore` contains `builds/`, `tests/fixtures/private/` and `.venv/` (setup added them; tidy duplicates).
2. **Common helpers:** `src/cards/common/`:
   - output contract (`Result`, budgets, truncation note)
   - `CardsError` / `Refused`
   - provenance writers and readers
   - `Build` paths
   - `sha256_file`
   - `tokens()`
   - `log.jsonl` appender
3. **Dispatcher:** `src/cards/cli.py` + `__main__.py`, so `python -m cards` works. Unknown flags exit 2.
4. **`cards state`:** `src/cards/state.py` with `init | get | set | phase | next`, exactly as spec §4.1 and §5. `init` writes `builds/.current`.
5. **Test helper:** `tests/conftest.py` with `private_fixture(name)`. It **fails** if the fixture is missing.
6. **Q-1 probe:** `tools/q1_probe.py`, standalone and outside the package.
   - It posts an MCP `initialize` then `tools/list` JSON-RPC request to `http://127.0.0.1:3141/`, with headers `Content-Type: application/json` and `Accept: application/json, text/event-stream`, and handles an SSE reply.
   - It prints `Q1 OK: <n> tools` or `Q1 FAIL: <reason>`.
   - Also write `docs/decisions.md` with an empty `## Q-1 result` section.

Write the Phase 0 contract tests first (`tests/contract/test_p0_foundations.py`), run them, and show they fail. Then implement.

## Definition of done

1. These pass, and failed before the implementation:
   - `test_g3_status_line_first`, `test_g3_stdout_budget`
   - `test_g4_exit_codes_mapped`, `test_g4_unknown_flag_exit2`
   - `test_g5_rerun_identical`, `test_g6_no_writes_outside_build`
   - `test_g7_provenance_present`, `test_g8_errors_name_file_line_field`, `test_g9_spaces_and_unicode_paths`
   - `test_g10_help_short`, `test_g10_log_line_per_run`
   - `test_fr2_init_creates_state_and_pointer`, `test_fr2_init_same_source_resumes`, `test_fr2_next_after_interrupt`
   - `test_fr2_illegal_phase_transition_exit2`, `test_fr2_set_rejects_unknown_key`, `test_fr2_corrupt_state_backed_up`
   - `test_inv2_no_network_imports`
   Later phases re-apply the same G-tests to their own new subcommands.
2. Run `contract_auditor` for phase 0 as a subagent and fix what it finds.
3. Report: files created, test output summary, auditor verdict. Report too that you can't run `tools/q1_probe.py` yourself, because the sandbox has no network.

## Gate (the owner runs this; don't report that it passed)

```
bash .codex/tools/gate.sh 0
```

Then, by hand:

1. `.venv/bin/cards state init "<path to the L006 PDF>"`. Check the stdout shape, that `builds/<date>_MED241-L006/build.json` exists, and that `cards state next --build builds/<that>` names P0.
2. With Anki open, run `.venv/bin/python tools/q1_probe.py` in a terminal.
3. If step 2 printed `Q1 OK`, run it again inside Claude Code in `this repository`, with `"Bash(.venv/bin/python tools/q1_probe.py)"` added to `permissions.allow` in `.claude/settings.local.json`, under auto mode.
4. Write both results under `## Q-1 result` in `docs/decisions.md`.
5. If both pass, a later phase builds `--direct` writing. Otherwise writes go through `mcp__anki__add_notes`.
6. Then run `bash .codex/tools/freeze_contract.sh` and commit.

## Stop

When the definition of done is met, stop and report. Don't begin Phase 1. If something can't be done, report it rather than working around it.
