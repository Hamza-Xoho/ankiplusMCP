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

Files: `pyproject.toml`, `.dockerignore`, `Dockerfile`, `scripts/check.sh`,
`docs/ARCHITECTURE.md`, `docs/verification.md`.

- [x] Modernise deprecated licence metadata and require its supporting setuptools floor.
- [x] Add one full-check entry point composing existing privacy/version, launcher and Python/build checks.
- [x] Exclude launcher outputs and worktrees from the Docker context.
- [x] Label legacy architecture and historical verification without removing their contents.
- [x] Verify metadata builds, shell syntax, full checks and unchanged frozen/runtime files; commit.

Ruling: container verification exposed a pre-existing Playwright bootstrap failure
(`libatomic.so.1` missing before `install --with-deps` could run). Install
`libatomic1` with Tesseract before invoking Playwright; retain runtime restrictions.
The failing build and corrected build serve as the regression check.

## Task 2: Student README and guides

Files: `README.md`, `docs/tools.md`, `docs/developer-guide.md`, `docs/setup.md`.

- [x] Rewrite the README with plain-language definitions, setup and concrete study requests.
- [x] Preserve detailed installation/configuration instructions in the setup guide.
- [x] Document every tool with inputs/defaults, output shape, prerequisites, example and implementation path.
- [x] Explain architecture, reuse of legacy internals, persistence, jobs, revisions, limits and extension points.
- [x] Check catalogue completeness and local links; exercise documented examples and packaging.

## Task 3: Verification and review

- [x] Run `./scripts/check.sh`, wheel/npm packaging and stdio smoke checks.
- [x] Validate Compose and build a correctly labelled dirty container; do not deploy.
- [x] Obtain one fresh review of the full diff for standards and approved scope; fix material findings.
- [x] Record measured results/limitations, mark plan steps complete, and commit documentation.

## Follow-up: apply lessons from an example conversation

The owner supplied a private flowchart/export bundle and explicitly chose
README/guides improvements only. Analyse it before implementing. Keep raw chat,
lecture content, source paths and collection identifiers out of public files.
Prior authorisation to push this documentation branch remains in effect.

Files: `README.md`, new `docs/study-workflow.md`, `docs/tools.md`,
`docs/setup.md`, `docs/developer-guide.md` and `docs/verification.md`.

- [x] Compare the example's two runs, revisions and recoveries with current source.
- [x] Generalise the reuse-first workflow, explanatory backs, diagram selection,
  complete manual review, external Anki handoff, readbacks and count distinctions.
- [x] Explain source fallback, profile/style mismatch, bounded reads and job/revision
  sequencing without converting the observed flow into a mandatory pipeline.
- [x] Verify source accuracy, all documentation links and the unchanged tool catalogue.
- [x] Run relevant repository checks, review the documentation diff, commit and push.
