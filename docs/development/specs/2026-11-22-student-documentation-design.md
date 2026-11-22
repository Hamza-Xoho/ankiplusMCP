# Student documentation and repository polish

Approved by the owner on 2026-11-22 in this session.

Make AnkiPlus MCP understandable to students while giving developers a complete,
source-backed description of all 33 tools. First polish repository maintenance
and resolve documentation ambiguity, then rewrite the public documentation.

## Approach

The owner chose a student-first README with linked detailed guides over one
large README. The README explains the product, setup, study examples and tool
groups. `docs/tools.md` describes every tool's inputs, outputs, prerequisites,
examples and implementation. `docs/developer-guide.md` explains architecture,
storage, jobs, extension points, checks and container operation.

## Constraints

- Preserve all functionality and public interfaces, including the legacy CLI.
- Do not modify `src/cards/`, frozen contracts, `.codex/`, `.agents/` or existing
  `.claude/` skills.
- Distinguish model judgement, local mechanical helpers and external Anki work.
- Preserve historical architecture content and label it as legacy.
- Keep installation, profiles, supported hosts, configuration, licensing and
  unattended operation discoverable when moving detail out of the README.
- Do not publish a portal, change host registrations or operate an Anki collection.

## Verification

Compare the catalogue with actual MCP methods; check Markdown links and examples;
run Python and launcher tests, privacy/version checks, frozen contract hashes,
wheel/npm packaging, Compose validation and a container build. Report skips and
live-client limitations explicitly. Make focused local commits; no push required.
