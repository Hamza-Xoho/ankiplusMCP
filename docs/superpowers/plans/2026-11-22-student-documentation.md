# Student Documentation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Polish the repository and explain AnkiPlus MCP clearly for students and developers.
**Architecture:** Preserve runtime code and contracts. Separate student onboarding, complete tool reference, and developer internals; retain historical documents with explicit navigation.
**Tech Stack:** Markdown, Python packaging, POSIX shell, Node launcher, Docker Compose.
**Spec:** `docs/superpowers/specs/2026-11-22-student-documentation-design.md`.

## Global Constraints

Preserve all functionality and interfaces. No edits to `src/cards/`, frozen contracts,
`.codex/`, `.agents/` or existing `.claude/` skills. No publishing or live Anki operations.
The owner approved execution without further design questions; implement inline on
`docs/student-guides`, retaining the existing clean checkout and virtual environment.

## Review Focus

- A student must understand that the host model drafts cards and AnkiPlus does mechanical work.
- Setup instructions must preserve host support, profiles, browser choice and configuration precedence.
- All 33 registered tools must have usage and implementation documentation.
- Revision changes, job completion and full replacement by save_cards must be unambiguous.
- Legacy guarantees must not be presented as current MCP behaviour.

## Task 1: Repository polish

Files: `pyproject.toml`, `.dockerignore`, `scripts/check.sh`,
`docs/ARCHITECTURE.md`, `docs/verification.md`.

- [ ] Modernise deprecated licence metadata and require its supporting setuptools floor.
- [ ] Add one full-check entry point composing existing privacy/version, launcher and Python/build checks.
- [ ] Exclude launcher outputs and worktrees from the Docker context.
- [ ] Label legacy architecture and historical verification without removing their contents.
- [ ] Verify metadata builds, shell syntax, full checks and unchanged frozen/runtime files; commit.

## Task 2: Student README and guides

Files: `README.md`, `docs/tools.md`, `docs/developer-guide.md`, `docs/setup.md`.

- [ ] Rewrite the README with plain-language definitions, setup and concrete study requests.
- [ ] Preserve detailed installation/configuration instructions in the setup guide.
- [ ] Document every tool with inputs/defaults, output shape, prerequisites, example and implementation path.
- [ ] Explain architecture, reuse of legacy internals, persistence, jobs, revisions, limits and extension points.
- [ ] Check catalogue completeness and local links; exercise documented examples and packaging.

## Task 3: Verification and review

- [ ] Run `./scripts/check.sh`, wheel/npm packaging and stdio smoke checks.
- [ ] Validate Compose and build a correctly labelled dirty container; do not deploy.
- [ ] Obtain one fresh review of the full diff for standards and approved scope; fix material findings.
- [ ] Record measured results/limitations, mark plan steps complete, and commit documentation.
