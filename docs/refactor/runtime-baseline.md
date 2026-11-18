# Runtime baseline

Reference revision: b0f423398432708feaab7a157ed7dcbe36bf3b1b, version 0.3.0. Execution branch: refactor/student-workflows. This checkout is independent of the older dirty checkout; no old files or live collection were changed.

## Two products share one engine

`src/cards/` is both a legacy CLI and the reusable mechanical engine. The newer `Service` in `src/ankiplusmcp/service.py` composes source, artifact, cards, review and payload mixins over `Store` and `Jobs`. It imports reusable engine functions; the CLI does not import the MCP. Engine edits therefore require both CLI and MCP regression checks.

## Legacy quality workflow

`CLAUDE.md` routes lecture BUILD/resume to `.claude/skills/anki2/SKILL.md`, pasted input/HARVEST/REPAIR and manual suspension to the older `/anki` skill if installed. The `/anki2` flow invokes `cards build`: extraction and target selection, host-authored drafts, check/render, two fresh reviewer packets (maintainer and student), apply, hash-bound gate, host Anki writes and receipts, final report. The skill requires source-grounded wording and existing AnKing coverage searches, separates note IDs from suspension card IDs, and forbids blind retries.

The skill expects pinned reviewer roles; it is not equivalent to one agent reviewing its own drafts. The new portability work must prove reviewer execution rather than assume Desktop runs Claude Code subagents. External maintainer ledgers described by the user are not shipped in this repository; their actual invocation remains user-supplied evidence.

## New MCP workflow

`server.API` exposes independent workspace/source/card/review/payload tools over stdio. The optional `skills/ankiplusmcp/SKILL.md` is not the legacy orchestrator. `Payloads.prepare_write` checks technical blockers and writes artifacts; it explicitly sets `review_required: false` and performs no Anki operations. `record_external_results` stores caller evidence, replacing the old result file; `get_report` counts reported operation records rather than independently verifying notes or semantic coverage. These are confirmed code observations, not conclusions about the owner's actual runtime session.

`Store.edit` increments one workspace revision after every successful edit context. Source/image operations also use it. OCR/render/export hold that context during native work, whereas source extraction mostly works in a fresh folder before publishing. A card-set revision and an artifact epoch are not currently distinct.

## Host guardrails and collection boundary

`.claude/hooks/require_review_before_write.py` guards a selected set of Anki tools against the active legacy build/gate/draft hash. It permits manual tools without an active build. `.codex/tools/verify_hooks.py` also checks Codex mutation/freeze guards; this does not establish a portable equivalent Anki-write gate. Never describe all host hooks as identical.

The checked-in `CLAUDE.md` identifies an AnkiMCP add-on endpoint at loopback port 3141. That is documentation, not proof of a running/installed add-on or its version. No development step may mutate an actual user's collection. The approved adapter belongs outside the network-free `cards` engine.

## Reproducible checks

- `./scripts/check-mcp.sh`: MCP/unit/foundation tests, frozen hashes, wheel build.
- `npm test`: dependency-free launcher tests.
- `.venv/bin/python .codex/tools/verify_hooks.py`: existing 42-case hook verifier.
- `uv lock --check`, `scripts/check_versions.py`, `scripts/check_privacy.py`.
- Full contracts include private lecture fixtures absent in a public clone. Public-CI skipping is an existing documented mode, not full real-lecture acceptance.

Execution evidence and unresolved checks are retained in this plan's ignored `.superpowers/sdd/2026-11-18-student-workflows/` workspace. Passing results are copied into acceptance records once commands complete.
