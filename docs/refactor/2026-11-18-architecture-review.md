# AnkiPlus MCP architecture review

- Date: 2026-11-18
- Repository: `Hamza-Xoho/ankiplusMCP`
- Reviewed branch: `refactor/student-workflows`
- Reviewed revision: `2d546e1`
- Scope: recently changed source, extraction, artifact publication, run history and coverage recording modules.
- Status: findings retained for reference. The user chose not to explore a candidate at this time. These proposals are not an approved implementation plan.

This review identifies opportunities to deepen modules: simpler interfaces that hide more implementation knowledge. It preserves the approved card-design rules, tool choices and existing output guarantees. No repository glossary or `docs/adr/` directory was found; the approved design and freeze constraints informed the review.

## Candidates

| Candidate | Strength | Dependency category | Main opportunity |
| --- | --- | --- | --- |
| Source workspace ownership | Strong | In-process | Keep extraction discovery and source state in one module. |
| Artifact publication | Strong | In-process | Own staging, input checks and publication sequencing once. |
| Run-history storage | Strong | In-process | Hide journal layout from the SQLite index. |
| Coverage recording | Worth exploring | In-process | Capture shared observations once per decision batch. |

Line references below refer to the reviewed revision. Files are under `src/ankiplusmcp/`.

## 1. Concentrate extraction ownership

**Files:** `sources.py:13–49`, `evidence.py:41–79`, `cards.py:89–113`, `review.py:28`.

**Problem:** Knowledge about active, retained and partial extractions crosses several module seams. The source module tracks active extraction and partial state, while evidence resolution knows retained paths and source-hash matching. Draft checks and review preparation also participate in selecting the available extraction.

**Current arrangement:** source state ↔ retained-extraction discovery → draft checks and review packets.

**Proposed arrangement:** one source workspace module owns source identity, extraction selection, active and retained extractions, and page availability. Citation matching concentrates on passages; draft checks and review use the source interface.

**Deletion test:** callers must lose knowledge of extraction paths and publication state. Adding a forwarding module without removing that knowledge adds no depth.

Benefits:

- Locality: extraction rules live together.
- Leverage: one source test surface.
- The interface hides retained paths.

Preserve source hashes, OCR behaviour, independent tool choice, existing PDF/text adapters, and physical versus printed page numbering. The recent chapter-resume correction demonstrates the friction; that defect is already fixed. Tests at the source seam should cover retained chapters, partial visibility and source changes.

## 2. Own staged publication once

**Files:** `store.py:104–129`, `sources.py:57–114,133–149`, `cards.py:127–181`.

**Problem:** Operation modules still carry sequencing needed to reject stale or cancelled output safely. Extraction, card rendering and page-image generation each manage variants of snapshotting inputs, doing work, checking inputs again and publishing output. `Store.artifact_work` already handles part of this protocol.

**Current arrangement:** extraction, rendering and page-image operations each coordinate their own publication sequence.

**Proposed arrangement:** an artifact publication module owns staging, input checks, cancellation, publication and artifact epochs. Each operation retains knowledge of which inputs its output depends on.

**Deletion test:** callers must lose sequencing and bookkeeping. Moving callbacks into a helper while leaving callers responsible for publication order does not add depth.

Benefits:

- Locality: failure handling lives together.
- Leverage: shared interruption tests.
- The interface hides publication order.

Keep semantic revisions separate from artifact epochs. Preserve output and cancellation behaviour. This does not require a new storage adapter or an OCR/rendering rewrite. Shared failure-injection tests should exercise stale inputs, cancellation and interrupted publication.

## 3. Hide journal layout from indexing

**Files:** `run_index.py:54–65`, `runs.py:58–83,153–178`, `history_cli.py`.

**Problem:** The disposable index understands event filenames, staging-directory conventions and a private run-path method. `RunIndex._sync` traverses storage owned by `RunStore`, duplicating knowledge of the journal layout.

**Current arrangement:** the index discovers run records through private paths, event-name rules and staging conventions.

**Proposed arrangement:** the authoritative run module owns discovery, freshness, readable records and corruption reporting. The SQLite index adapter owns its projection and bounded queries.

**Deletion test:** the index must lose filesystem-protocol knowledge, rather than call a relocated directory scan while retaining the same assumptions.

Benefits:

- Locality: journal rules live together.
- Leverage: discovery is tested once.
- The interface survives layout changes.

Keep files authoritative and SQLite rebuildable. These are complementary roles, not interchangeable adapters. This finding identifies observed coupling and inferred change friction; no current search failure was reproduced. Test corrupt and staged records at the run seam, and projection/query behaviour at the index seam.

## 4. Capture observations once per batch

**Files:** `coverage.py:67,87,117–124`, `runs.py:153–165`, `evidence.py`.

**Problem:** Each coverage decision embeds the entire shared collection observation and appends separately to the journal. Each append rereads history, and evidence resolution also happens per decision. The resulting storage and replay costs have not been measured.

**Current arrangement:** repeated collection observation → individual decisions → separate append/replay steps.

**Proposed arrangement:** capture one immutable observation and record a coherent decision batch through a coverage recording module that owns source evidence, configuration-version references and recovery.

**Deletion test:** shared capture and durable recording sequencing must disappear from coverage callers. Callers should not have to coordinate snapshot references themselves.

Benefits:

- Locality: retry rules live together.
- Leverage: batch reconstruction tests.
- Depth: less caller sequencing.

Measure representative runs before choosing this change. Preserve caller-supplied evidence labels and the configuration version actually used. Do not claim atomic recording or independent verification without proof. Test observation reuse, interrupted recording, retries and reconstruction.

## Recommendation and disposition

Source workspace ownership was the strongest candidate to explore first: it addresses demonstrated source-selection friction before interactive review depends on it, while preserving the working card-design implementation.

The user declined further exploration and requested this Markdown record. No exact interfaces were designed and none of these refactors was implemented as part of this review. The earlier HTML report was a presentation of the same candidates; this document retains the findings in the repository.

This review does not replace the broader architecture audit or the existing implementation plan, and it makes no new claim that release acceptance checks have passed.
