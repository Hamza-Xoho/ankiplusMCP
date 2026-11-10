# AnkiPlus MCP development

The new product is `ankiplusmcp`, implemented in `src/ankiplusmcp/`.
Run `./scripts/check-mcp.sh`; use `python -m ankiplusmcp` for stdio.
The official Anki MCP is a separate host dependency. Do not add Anki connection,
proxy or collection mutation code. Keep the host model in control of workflows.
Use `tests/mcp/` for new MCP tests. Keep `src/cards/`, frozen contract tests,
`.codex/`, `.agents/` and existing `.claude/` skills unchanged.
The historical phase-building instructions below apply to the legacy CLI,
not the new independent MCP workspace/API. Approved migration design:
`docs/superpowers/specs/2026-11-07-ankiplusmcp-design.md`.

---

# Lecture2Cards: building /anki v2 (the `cards` CLI and the `/anki2` skill)

You are building tools that a *different* agent (Claude Code) runs to make Anki cards. Its tokens are the cost being cut. Every byte a `cards` command prints is a byte that Claude reads.

## Commands

```
.venv/bin/pip install -e '.[dev]'               # install the package (once, after pyproject changes)
.venv/bin/python -m pytest -q tests/contract/test_pN_*.py tests/unit   # this phase's tests
.venv/bin/cards <subcommand> --help             # the CLI
```

## Invariants (hook-enforced; if a hook blocks you, your change is wrong, so do not route around it)

- **INV-1** Contract tests listed in `.codex/contract.sha256` are frozen: never edit, delete, move, skip or xfail them. `.codex/` and `.agents/` are not yours to change.
- **INV-2** No network import in `src/cards/` except `src/cards/write/direct.py`.
- Every subcommand: stdout line 1 `OK|FINDINGS|ERROR`, then ≤ 40 lines / 2,000 chars, then `→ <path>` lines. Exit 0 ok, 1 findings, 2 error, 3 refused (spec §6).
- Never write outside the `--build` folder. Never open the lecture source for writing.
- Nothing may let `cards gate` or `cards write` skip their checks: no flag, no env var, no config key.

## Boundaries

- `common` imports nothing from `cards`. `cli` holds no logic. Dependency directions: `docs/design-spec.md` §2.
- `.claude/` is the runtime (Claude Code). Edit it only in the phases that say so (1 settings, 4–7). Never touch `.claude/skills/anki/` (v1, still in use).
- Lecture PDFs, `<your notes vault>` and the lecture folder are read-only.

## How to work

- **One phase per thread.** Read the phase prompt you were given, then only the spec sections it names.
- Write that phase's contract tests first, with the exact names from `docs/test-contract.md`. Run them and show they fail. Then implement.
- Before reporting, run the auditors the phase prompt names (`contract_auditor`, `boundary_auditor`, `token_auditor`) as subagents, and fix what they find.
- Stop at the phase's definition of done. Report: what you built, test results, auditor verdicts, anything you couldn't do. **Do not start the next phase.** the owner runs the gate.
- A private fixture missing (`tests/fixtures/private/…`) is a stop-and-ask, not a reason to skip a test.

## Where things are

- Why/what: `docs/anki-v2-brief.md` · Tool requirements: `docs/anki-v2-trd.md`
- How (names, schemas, errors): `docs/design-spec.md` · Named tests: `docs/test-contract.md`
- Repo conventions, on demand: `$cards-cli-conventions`, `$claude-code-runtime`
- Code to port: `.claude/skills/anki/scripts/` (v1: deck_name, extract_figures, ocr_regions, build_occlusion, render_cards)
