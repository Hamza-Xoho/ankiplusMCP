---
name: cards-cli-conventions
description: How to add or change a `cards` subcommand in this repository. Covers the stdout contract, exit codes, provenance headers, build-folder paths, log.jsonl and where tests go. Use whenever you create or edit anything under src/cards/.
---

# cards CLI conventions

The reader of every `cards` command is Claude Code at run time, paying per token. Print little; write files.

## Adding a subcommand

1. **One module** under `src/cards/` (see design-spec §2 for the allowed imports). Expose `run(args) -> Result`.
2. **Register** it in `cli.py` only: an argparse subparser plus `dispatch`. No logic in `cli.py`.
3. **Output** goes only through `cards.common.output`:
   - `Result(status, lines, files, exit_code)`, where `status` is `OK | FINDINGS | ERROR`
   - the helper prints `status`, then the lines (truncated to the budget with a final `… N more in <file>`), then `→ <path>` for each file
   - never `print()` directly in a command module
4. **Errors:** raise `CardsError(code="E2x", what=..., remedy=...)`. `cli` turns it into `ERROR E2x <what> — <remedy>` and exit 2. A precondition refusal raises `Refused(...)` and exits 3. Findings return exit 1.
5. **Provenance:** write files with `cards.common.files.write_json/write_jsonl/write_text`, which add `_meta` or the header comment (spec §3). Read JSONL with `read_jsonl`, which skips the `_meta` line.
6. **Paths:** resolve everything from `cards.common.paths.Build(args.build)`. Never build a path outside it, except `meter --out` and `builds/.current` (in `state` and `report` only).
7. **Log:** the dispatcher appends a `log.jsonl` line for every run with `--build`. Don't do it yourself.
8. **Help:** `--help` stays ≤ 20 lines. Unknown flags exit 2 (argparse default + a custom error handler).

## Budgets (spec §6, cards.toml)

| Output | Limit |
|---|---|
| stdout | 40 lines, 2,000 characters |
| `cards source` | exempt: prints the slice asked for |
| `cards report` | exempt: ≤ 25 lines |
| `map.md` | ≤ 2,500 tokens for L006 |
| `PROMPT.md` | ≤ 300 tokens |

Token estimate everywhere: `cards.common.size.tokens(text) = ceil(len(text)/4)`.

## Tests

- `tests/contract/test_p<N>_<area>.py`: the exact names from `docs/test-contract.md`. Write them first, red. Frozen after the gate.
- `tests/unit/`: yours to change freely.
- Run the CLI in tests through `subprocess` (`[sys.executable, "-m", "cards", ...]`), so the real stdout and exit code are tested.
- Private fixtures in `tests/fixtures/private/`: a missing one must **fail** with `missing fixture <name>: see HANDOVER §Setup`. Use the `private_fixture(name)` helper in `tests/conftest.py`.

## Porting v1 scripts

v1 lives in `.claude/skills/anki/scripts/`. Keep the measured choices: OCR binarise at 128, 2× upscale, multi-psm; 4× figure re-render; render at 390 px, night mode, scripts stripped. Change the interfaces to the spec's; don't change what was measured to work.
