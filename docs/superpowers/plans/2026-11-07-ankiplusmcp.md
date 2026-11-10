# AnkiPlus MCP Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Deliver the approved independent mechanical MCP toolkit and companion skill.
**Architecture:** A new ankiplusmcp package adapts existing cards operations. Explicit isolated workspaces, typed tools, durable jobs and bounded artifact results replace phase orchestration.
**Tech Stack:** Python 3.12+, official MCP Python SDK, Pydantic, existing OCR/renderer modules.
**Spec:** docs/superpowers/specs/2026-11-07-ankiplusmcp-design.md (approved in conversation).

## Global Constraints
- Official Anki MCP is a separate host dependency; no Anki connection/proxy/writes.
- Preserve src/cards, frozen contracts and old skills; all new mutable artifacts stay inside workspaces.
- Local stdio; no global installation, publication or user configuration changes.
- Model-led optional workflows; no embedded AI, compulsory reviewers or phases.

## Review Focus
- Two server processes modifying one workspace must not lose updates.
- Imported paths, symlinks, oversized images and rendered HTML cannot escape boundaries.
- Existing cards with arbitrary fields work without lecture metadata.
- Restarted/cancelled jobs cannot advertise incomplete results as completed.
- Payloads/external receipts distinguish intentions from actual Anki results.

### Task 1: Workspace store and durable jobs
**Files:** src/ankiplusmcp/{__init__,models,store,jobs}.py; tests/mcp/test_store.py
**Interfaces:** Store(root, source_roots), create/get/mutate/resolve/import operations; Jobs.submit/get/cancel.
- [x] Add failing tests for isolation, revision conflict, cross-process locks, import bounds, job interruption/cancellation.
- [x] Run `.venv/bin/python -m pytest -q tests/mcp/test_store.py`; expect missing package failure.
- [x] Implement typed records, atomic writes and flock locks; persistent jobs with bounded workers.
- [x] Run task tests; expect pass. Commit if author identity available; otherwise record limitation.

### Task 2: Source, figures and artifacts
**Files:** src/ankiplusmcp/{service,sources,artifacts}.py; tests/mcp/test_sources.py
**Interfaces:** Service composes store/jobs; source tools use cards modules via isolated workspace adapters.
- [x] Add failing synthetic PDF/text, OCR, occlusion and bounded artifact/image tests.
- [x] Run task tests and observe missing service operations.
- [x] Implement source extraction/read/search/figures/OCR/occlusion/target adapters and guidance.
- [x] Run task tests; expect pass and source unchanged.

### Task 3: Cards, reviews and payloads
**Files:** src/ankiplusmcp/{cards,review,payloads}.py; tests/mcp/test_cards.py
**Interfaces:** Typed Card/Review records; independent save/check/render/prepare/submit/apply/write/results/report methods.
- [x] Add failing standalone card, render, source coverage, review conflict, stale write, receipt tests.
- [x] Run tests and observe absent operations.
- [x] Implement service operations using legacy lint/render functions, independent review storage and payload serialization.
- [x] Run task tests; expect pass without Anki or fabricated lecture metadata.

### Task 4: MCP protocol, packaging and skill
**Files:** src/ankiplusmcp/{server,__main__}.py; pyproject.toml; requirements.lock; tests/mcp/test_protocol.py; README.md; skills/ankiplusmcp/SKILL.md; scripts/check-mcp.sh; Dockerfile; compose.yaml; .dockerignore; .env.example; docs/capabilities.md
**Interfaces:** ankiplusmcp --workspace-root PATH --source-root PATH; all approved capabilities with typed schemas and MCP results.
- [x] Add failing discovery/call/image/error tests through an actual stdio client.
- [x] Implement server registrations, dependency diagnostics, command and docs; validate companion skill.
- [x] Run all new tests, existing unit suite, wheel isolated installation and synthetic workflow, and applicable container build.
- [x] Fresh reviewer examines full change; fix material findings with regression tests.
- [x] Record verification and limitations; preserve branch without publishing or global installation.
