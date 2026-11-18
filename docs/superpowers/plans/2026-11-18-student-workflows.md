# AnkiPlus Student Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execution method: native, explicitly selected by the user after design approval. Follow the per-plan progress ledger and completed commits; do not repeat completed work.

**Goal:** Deliver the complete approved student workflow while preserving current card quality and making Anki operations reviewable, recoverable and traceable.

**Architecture:** Retain the shared mechanical engine and thin MCP facade. Add versioned run/configuration records, a narrow adapter to the separate Anki MCP, an approval-enforcing coordinator and a companion interactive review interface. Determine host-specific transport and reviewer execution through an early experiment before specifying those implementations.

**Tech Stack:** Existing Python/Pydantic/MCP server and dependency-free Node launcher; SQLite from Python's standard library for a rebuildable index. UI stack and adapter transport are selected from compatibility evidence, not assumed here.

**Spec:** `../specs/2026-11-18-student-workflows-design.md`

## Global Constraints

- Preserve current card selection, design rules, tiering, tags, rendering and AI reviewer requirements of the owner's actual workflow.
- macOS is the first supported release platform; real Mac access is not immediately available and real Mac acceptance is required before release.
- Target Claude Pro and Claude Desktop; no separate model API subscription.
- First release includes all agreed features and all verified required fixes. Phases are internal checkpoints, not smaller public releases.
- User feedback affects the current run unless explicitly saved as a preference.
- Protect existing premade notes by default; an update requires explicit authorization.
- User approval and automatic mode never bypass existing quality checks.
- Keep notes and cards distinct; suspension/unsuspension uses card IDs.
- Originals remain read-only; private sources, paths, receipts and configuration are not public fixtures.
- Preserve permanent history by default. Cleanup of derived files requires an explicit request and cannot erase required evidence.
- No blind retries of uncertain external writes, no unsupported exactly-once claims.
- Native implementation is authorized; publishing, deployment and live collection changes are not authorized by that choice.

## Review Focus

- Same textbook with different chapter selections: distinct runs, scoped evidence and no accidental document-wide creation (Tasks 4, 6).
- Existing cloze notes with multiple cards and a foreign note ID: correct ID types, explicit updates and no unintended edits (Tasks 6, 8).
- Host dies after Anki accepts a write: uncertain journal entry, reconcile before retry and cumulative results (Tasks 7, 8).
- User edits source/configuration/card fields after approval: only affected proposals invalidate and quality checks rerun (Tasks 5, 9).
- Old workspaces with partial caller receipts: preserve evidence origin and data; never invent confirmation or delete the sole source (Tasks 4, 10).

## Baseline and execution location

The audited source is `b0f4233` (0.3.0). This local checkout's committed HEAD is older and has substantial uncommitted changes. Do not reset, stash, absorb or commit those changes as part of this work. At execution, use the isolation skill to establish the intended baseline in an isolated checkout and verify `git rev-parse --show-toplevel` before edits. Confirm upstream drift by reading the diff, not by assuming all paths here match a newer revision.

The planning handoff originally added only these three documents. Execution now uses a fresh isolated clone at the audited revision and has its own checkpoint report. The documents are portable: copy them together when handing off. Existing frozen tests and hooks remain protected. The approved new adapter supersedes the old no-connection design only within `src/ankiplusmcp/`; update architecture instructions narrowly during implementation rather than bypassing an active hook.

## File and responsibility map

Existing integration points: `src/ankiplusmcp/{server,service,store,jobs,sources,cards,review,payloads,settings,models,doctor}.py`, `launcher/{cli.mjs,lib/init.mjs,lib/hosts.mjs}`, `skills/ankiplusmcp/SKILL.md`, `.github/workflows/ci.yml`, `scripts/check-mcp.sh`.

Proposed new focused units, not implemented yet:

- `run_models.py`: source selection, events, proposals, authorizations and operation identities.
- `runs.py`: durable event publication and immutable proposal snapshots.
- `run_index.py`: rebuildable SQLite index and bounded history queries.
- `configuration.py`: versioned user configuration and explicit change confirmation.
- `evidence.py`: source quotations, page identities and extraction provenance.
- `coverage.py`: collection search evidence and per-concept dispositions, without changing drafting rubrics.
- `anki_adapter.py`: fixed typed collection interface and the experimentally selected companion connection.
- `coordinator.py`: validate/authorize/apply/reconcile, with no model calls.
- `onboarding.py`, `guide.py`: resumable setup milestones and personalised guide rendering.
- `review-ui/`: companion interface; create only after the compatibility gate settles packaging.

Keep matching tests under `tests/mcp/`; launcher tests stay under `launcher/test/`. Synthetic/golden fixture files belong under `tests/fixtures/public/`. Do not edit frozen contract files.

## Stage A: Baseline and compatibility evidence

### Task 1: Establish the actual runtime and release checklist

**Files:** Create `docs/refactor/runtime-baseline.md`, `docs/refactor/acceptance.md`; carry `2026-11-18-audit-disposition.md` beside this plan. Read existing `AGENTS.md`, `CLAUDE.md`, skills, hook checks, tests and `docs/verification.md`.

**Interfaces:** Produces the canonical runtime map, required checks and audit dispositions consumed by every later task.

- [ ] Verify source revision, clean isolated checkout and configured Git identity. Preserve all unrelated local work.
- [ ] Trace extraction, drafting, search, AI reviews, gate and writes through code. List external maintainer files as supplied evidence until actually inspected; do not make private files a public dependency.
- [ ] Recheck audit claims against the chosen baseline. Record `confirmed`, `not reproduced`, `superseded` or `needs measurement`, with code/test evidence.
- [ ] Run `./scripts/check-mcp.sh`, `npm test`, `uv lock --check` and the documented hook verifier. Record failures, missing prerequisites and skipped private fixtures separately. Read the verifier path from the checkout before executing it.
- [ ] Commit only the runtime/checklist documents using the configured identity. If identity is absent, leave reviewable changes and report it; never invent identity.

### Task 2: Make regression protection reproducible

**Files:** Modify `tests/tools/cli_baseline.py`, `.github/workflows/ci.yml`, `scripts/check-mcp.sh`; create `tests/fixtures/public/cli-baseline/`, `tests/unit/test_public_baseline.py`, `docs/refactor/quality-baseline.md`.

**Interfaces:** Existing baseline CLI stays `record DIR` / `compare DIR`. Produces a committed normalized baseline and representative quality acceptance rubric.

- [ ] Write failing `test_public_baseline_detects_payload_change`: a changed field, tag, tier or media hash fails comparison; root paths/timestamps alone do not. Add a deterministic OCR fixture/shim that exercises the same subprocess boundary.
- [ ] Run `.venv/bin/python -m pytest -q tests/unit/test_public_baseline.py`; expect the new missing-baseline checks to fail.
- [ ] Record and inspect a public synthetic baseline, never private lecture bytes. Add synthetic column-reading, image-only and objective/reference cases without modifying frozen tests.
- [ ] Add CI baseline comparison, frozen hash verification, existing hook checks, lockfile consistency and Python 3.12 plus existing tested version. Discover package filenames dynamically instead of hard-coding 0.3.0.
- [ ] Run the focused tests and baseline compare, then existing relevant checks. Retain real OCR/render lanes and separately record private fixture availability.
- [ ] Define source-to-card evaluations for selection, combined recall tasks, gaps, tiering, source fidelity and visuals. Pin deterministic contracts; evaluate variable model output with the unchanged rubrics.
- [ ] Commit only baseline/check changes. Never accept a changed baseline without explaining the intended difference.

### Task 3: Run the Desktop and companion compatibility experiment

**Files:** Create `docs/refactor/compatibility.md`; disposable code under ignored project-local `.artifacts/compatibility/`, never production modules.

**Interfaces:** Produces evidence for `anki_adapter.py`, `review-ui/` packaging and reviewer execution. No downstream interface implementation is authorized until these choices are settled.

- [ ] Identify the exact Anki companion/add-on, transport, authentication, tool names, media input, note/card search/readback and duplicate behaviour from official docs plus actual tools. Do not confuse AnkiConnect with an MCP server.
- [ ] Prototype a sample-only embedded review with select/edit/exclude and a returned decision. Check available local MCP App support, resource access and reconnection. Do not infer support from a static browser demo.
- [ ] Determine how the actual independent AI reviewers run under the intended Desktop/Pro host. Do not silently substitute a single self-review or add API credentials.
- [ ] Record local feasibility results now and a concrete Mac procedure for later. A Mac hosted CI runner can test packaging, but cannot stand in for the actual interactive Claude Desktop session.
- [ ] Measure what reaches the model from `content` and `structuredContent` in the supported hosts before removing either. Record actual schema bytes and tokenizer/tool-loading assumptions.
- [ ] Write the chosen transport, supported capabilities and typed errors into the adapter/UI follow-up plan. If constraints cannot be met, stop that branch and present alternatives with evidence; proceed only on unrelated baseline fixes.
- [ ] Commit evidence, excluding secrets and personal documents.

## Stage B: Core correctness, records and configuration

### Task 4: Introduce source/run records and cumulative evidence

**Files:** Create `src/ankiplusmcp/{run_models,runs,run_index}.py`, `tests/mcp/test_runs.py`, `tests/mcp/test_run_migration.py`; modify `store.py`, `payloads.py`.

**Interfaces:** `RunStore.start(workspace: str, selection: SourceSelection, config_version: int) -> Run`; `append(run_id: str, event: RunEvent) -> int`; `read(run_id: str) -> RunSnapshot`; `RunIndex.rebuild() -> int`; `search(query: RunQuery) -> RunPage`.

`SourceSelection` has source hash/version and normalized physical page selection. `RunEvent` has schema version, monotonic sequence, unique event ID, run ID, UTC time, event kind and validated payload. `RunQuery` filters source/run/note/card ID, stage and outcome with offset/limit. Results retain evidence origin.

- [ ] Add tests asserting two chapter selections are separate runs, exact source repeats remain discoverable, and several batches accumulate without replacing earlier receipts. Replay of the same event ID is idempotent; contradictory reuse fails.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_runs.py tests/mcp/test_run_migration.py`; expect missing APIs to fail.
- [ ] Implement append-only, lock-protected event files and immutable proposal snapshots. Publish records atomically with file and directory durability appropriate to the target platform; recover safely from truncated/unpublished writes.
- [ ] Build the index from records. Deleting the index then rebuilding preserves counts and search results. The index is not authoritative.
- [ ] Import old workspaces non-destructively, retaining unknown relationships and `caller_supplied`/`independently_verified: false`. No inferred card mapping becomes verified evidence.
- [ ] Run focused tests and regression checks; commit. Add bounded CLI/search exports separately from review UI.

### Task 5: Version configuration and separate artifacts from card edits

**Files:** Create `configuration.py`, `tests/mcp/test_configuration.py`; modify `settings.py`, `store.py`, `sources.py`, `cards.py`, `jobs.py`, `tests/mcp/test_locking.py`.

**Interfaces:** `ConfigStore.propose(changes: dict, expected_version: int) -> ConfigChange`; `confirm(change_id: str) -> UserConfig`. `UserConfig` includes schema/config/onboarding versions, completion state, selected decks, data root, preserved profile, review mode and uncertain-match policy. Default review is enabled and automatic uncertainty is `pending`.

- [ ] Test that run-only decisions never change config; a confirmed change increments version; concurrent stale confirmation fails; unrelated config does not alter historical records.
- [ ] Test that generating a page image or completing OCR does not stale a card edit; simultaneous real card edits still conflict. Hold a long native operation and assert reads remain available or return bounded retryable BUSY, never hang indefinitely.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_configuration.py tests/mcp/test_locking.py`; verify new assertions fail before changes.
- [ ] Implement typed config migration preserving existing profiles and explicit paths. Keep mutable artifact epoch separate from card revision; migrate existing workspaces rather than resetting counters.
- [ ] Apply snapshot/work/publish to OCR, exports, rendering and occlusions. Publish only if captured preconditions still hold, and do not resurrect cancelled/stale work. Add bounded locking, timestamps and discoverable job listings.
- [ ] Test shutdown and crash recovery with concurrent clients. Recheck B4/B5 before claiming durable transactions; several atomic file replacements are not one transaction.
- [ ] Run focused and existing relevant suites, then commit.

### Task 6: Add source evidence and existing-coverage decisions

**Files:** Create `evidence.py`, `coverage.py`, `tests/mcp/test_evidence.py`, `tests/mcp/test_coverage.py`; modify `models.py`, `cards.py`, `review.py`.

**Interfaces:** `EvidenceRef(source_hash, pdf_page, page_label, quote, extraction_origin, region)`; `evidence.resolve(workspace: str, refs: list[EvidenceRef]) -> list[SourceEvidence]`. `CoverageDecision` contains stable concept/draft key, candidate note/card IDs, evidence refs, disposition and collection snapshot identity. Query/read operations use Task 7's adapter contract; use fixtures until it exists.

- [ ] Test quotations are actual source substrings after documented whitespace normalization, page references exist, multiple references survive, and OCR/image-only evidence is honestly labelled.
- [ ] Test same-document/different-chapter selections, missing objectives, revised PDFs and one existing note serving several sources. Do not force invented slide references on source-free existing-card workspaces.
- [ ] Test already-active coverage is unchanged; suspended suitable cards are candidates; unresolved matches/contradictions remain pending in automatic mode; successful prior mappings prevent automatic recreation.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_evidence.py tests/mcp/test_coverage.py`; verify failures before implementation.
- [ ] Implement evidence and decision records without changing existing drafting/rubric/tag conventions. Keep semantic judgement in the host model; the server validates records, not factual truth.
- [ ] Display review-rejected omissions separately from genuine coverage and surface reviewer set findings. Preserve legacy warning/blocker policy until a proposed change is explicitly approved.
- [ ] Verify quality baseline, source constraints and tests; commit.

## Stage C: Collection adapter and exact approval

### Task 7: Implement the verified companion adapter

**Files:** Create `anki_adapter.py`, `tests/mcp/test_anki_adapter.py`; create `tests/mcp/fakes/anki_companion.py` if needed. Update architecture instructions narrowly for the approved adapter.

**Interfaces:** Typed `AnkiAdapter` exposes `capabilities()`, `collection_identity()`, `search_notes(query)`, `read_notes(note_ids)`, `read_cards(card_ids)`, `read_note_type(name)`, `store_media(media)`, `create_notes(batch)`, `update_note(change)`, `set_suspended(card_ids, suspended)`. Exact transport and companion payload mapping come from Task 3; do not implement arbitrary tool forwarding.

- [ ] Write fake-companion tests for missing capability, unavailable Anki, multiple cloze cards per note, foreign note ID, transport authentication failure and partial responses. No tokens/credentials in logs.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_anki_adapter.py`; verify missing adapter failures.
- [ ] Implement only experimentally established operations; return typed transport/unsupported/conflict errors. Keep network/MCP client imports outside `src/cards/`.
- [ ] Add boundary tests proving the mechanical engine cannot reach collection mutation code and the adapter cannot issue arbitrary MCP calls.
- [ ] Run protocol, boundary and focused tests. Real collection writes wait for isolated-profile acceptance. Commit.

### Task 8: Enforce approval and recover uncertain writes

**Files:** Create `coordinator.py`, `tests/mcp/test_coordinator.py`, `tests/mcp/test_reconciliation.py`; modify `payloads.py`, `server.py`.

**Interfaces:** `Coordinator.stage(run_id: str) -> Proposal`; `authorize(run_id: str, proposal_digest: str, mode: Literal['user','config']) -> Authorization`; `apply(run_id: str, proposal_digest: str) -> ApplyResult`; `reconcile(run_id: str) -> ReconciliationResult`.

`Proposal` digests canonical fields/actions/targets/media hashes/source/config dependency values and AI-review evidence. `ApplyResult` reports per-operation `confirmed`, `failed`, `unchanged`, `uncertain` or `conflict`, with actual note/card IDs and verification origin.

- [ ] Test card/media/source/relevant-config changes invalidate authorization; approval cannot bypass quality blockers. Automatic authorization requires matching explicit config and never claims a human click.
- [ ] Test changed/missing/foreign notes, switched collection identity and already-unsuspended cards. Require explicit existing-note updates; do not overwrite on stale snapshots.
- [ ] Test interruption before send, after acceptance before receipt, partial batch acceptance and repeated receipt replay. Ambiguous writes are reconciled or stay pending; no blind second create occurs.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_coordinator.py tests/mcp/test_reconciliation.py`; verify new cases fail.
- [ ] Implement durable intent-before-send journaling, batch/draft/operation identities, readback and cumulative events. Match observed companion duplicate semantics, not assumed first-field guarantees.
- [ ] Resolve generated card IDs before suspension and verify final suspension state. Counts name their units and only verified results claim success.
- [ ] Expose narrow coordinator tools, retain/deprecate older APIs explicitly and prevent the new workflow bypassing approval through its own old write path. State external-tool bypass limitations plainly.
- [ ] Run focused, protocol and baseline tests; commit.

## Stage D: User experience and installation

### Task 9: Build source-linked interactive review

**Files:** Create `review-ui/` using the packaging selected in Task 3; create `tests/mcp/test_review_session.py`; modify `server.py`, `review.py`.

**Interfaces:** `ReviewSession.read(run_id: str) -> ReviewPage`; `decide(run_id: str, expected_proposal_digest: str, decisions: list[ReviewDecision]) -> Proposal`; final approval calls Task 8's authorization interface. `ReviewDecision` supports keep/exclude/edit-new/choose-existing/defer/explicit-update; it cannot directly write Anki or silently save preferences.

- [ ] Test bounded card text pages, existing-card candidates, source quotations/images, already-covered entries and pending contradictions. Use synthetic source files only.
- [ ] Test stale tabs and simultaneous reviewers cannot approve an unseen revision. User edits rerun affected quality checks; late AI results cannot approve a newer draft.
- [ ] Implement keep/edit/exclude and explicit update controls with distinct notes/cards wording and clear pending/failed states. Preserve draft selection through host reconnection.
- [ ] Bind UI requests to an explicit workspace/run/session; reject forged/stale decisions and untrusted source content as instructions. Serve only the selected source/artifacts, not arbitrary local paths.
- [ ] Run protocol/session tests and actual supported-host acceptance from Task 3. Apply frontend/accessibility skills at implementation time; interactive browser verification requires the appropriate user-authorized browser task.
- [ ] Commit UI/server changes with recorded host/version evidence. A static mockup is not a compatibility pass.

### Task 10: Add resumable onboarding and the personalised guide

**Files:** Create `onboarding.py`, `guide.py`, `tests/mcp/test_onboarding.py`, `tests/mcp/test_guide.py`; modify `launcher/cli.mjs`, `launcher/lib/init.mjs`, `launcher/lib/hosts.mjs`, `doctor.py`, `skills/ankiplusmcp/SKILL.md`; add focused launcher tests.

**Interfaces:** `Onboarding.status() -> SetupStatus`; `advance(step: SetupStep, evidence: SetupEvidence) -> SetupStatus`; `Guide.render(config: UserConfig, capabilities: VerifiedCapabilities) -> str`. Onboarding completion requires connection, storage, quality-runtime and guide checks; it must not require paid API credentials.

- [ ] Test lecture/textbook/custom-source setups, no premade decks, existing overlapping decks, paths with spaces and interrupted setup. Do not reduce user types to two fixed presets.
- [ ] Test a missing app, permission denial or failed connection keeps onboarding incomplete; reruns preserve existing host config and explicit preferences.
- [ ] Test guide has all seven specified sections, relevant examples and reasons, actual chosen paths, and no unsupported capability claims. Store generated sections separately from user notes so regeneration preserves notes.
- [ ] Implement plain-language setup/interview, recommended review with uncertainty pending, explicit config diff confirmation and per-run override. Offer folder selection where supported and a safe default otherwise; do not assume a folder picker exists in every host.
- [ ] Help install Anki and supported dependencies; explain OS interactions setup cannot automate. Verify checks before writing completion flags and report the saved guide's exact path.
- [ ] Run `.venv/bin/python -m pytest -q tests/mcp/test_onboarding.py tests/mcp/test_guide.py` and `npm test`; include failed-first evidence for new behaviour. Commit.

## Stage E: Audit closure, measured efficiency and release

### Task 11: Repair verified legacy failure paths

**Files:** Modify only confirmed necessary paths among `src/cards/{build,state,report,target}.py`; add `tests/unit/test_write_recovery.py`, `tests/unit/test_build_lock.py`; update runtime docs.

**Interfaces:** Preserve existing CLI command names and successful output. Existing write completion checks receipts against expectations before completing P6. A build lock refuses simultaneous mutation with the established refusal exit code.

- [ ] Reproduce A1/A4/A6/D2 with synthetic inputs and verify which remain relevant to the canonical workflow. Test count mismatch leaves a recoverable phase and concurrent continue refuses rather than races.
- [ ] Add per-batch statuses and a tested reconcile/retry path that does not resend acknowledged notes. Do not invent a passing receipt to unblock a build.
- [ ] Check preflight input timing and deck collision detection. If changing a pause alters documented output, isolate and approve that compatibility change instead of labelling it byte-neutral.
- [ ] Run `.venv/bin/python -m pytest -q tests/unit/test_write_recovery.py tests/unit/test_build_lock.py`, committed baseline comparison and relevant frozen contracts. Commit focused fixes separately.

### Task 12: Reduce measured waste without changing quality

**Files:** Modify `cards.py`, `server.py`, `sources.py`, `jobs.py`; create `tests/mcp/test_card_patch.py`, `tests/mcp/test_response_budget.py`; optional shared OCR cache changes only after baseline evidence.

**Interfaces:** `patch_cards(workspace: str, expected_revision: int, patches: list[CardPatch]) -> CardPatchResult`; patches identify stable local draft IDs, preserve unspecified fields and reject duplicate/conflicting patch keys. Results include changed IDs and new card revision.

- [ ] Test one-card patches preserve every untouched card; stale versions reject; response pagination returns bounded results with continuation instead of discarding all data.
- [ ] Record schema size, request/response token estimates and real extraction/render times. Treat chars/4 as an estimate, not tokenizer output.
- [ ] Implement patching and measured empty-default reduction with compatibility tests for null/default meaning. Keep structured results unless host evidence supports a change.
- [ ] Share OCR caching only with complete cache identity and unchanged labels. Do not change OCR resolution/passes, preview image quality, summary format/tiering suggestions or reviewer wording without a separate A/B result and approval.
- [ ] Add explicit derived-artifact cleanup with protected-source/history tests, job discovery and source labels/recency. Preserve history during uninstall; data deletion is a separate explicit action.
- [ ] Run focused performance/correctness tests and quality baseline, record before/after evidence, commit.

### Task 13: Close audit findings and package the supported product

**Files:** Update audit disposition, `README.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, CI, package/version metadata and Docker checks as justified.

**Interfaces:** Release checklist maps each accepted requirement and required audit ID to a passing test/manual acceptance artifact or an explicit unresolved blocker.

- [ ] Correct current-vs-history documentation without deleting historical rationale. Test duplicated template consistency before consolidating copies; preserve reviewer content.
- [ ] Fix diagnosed packaging/version/path faults; verify declared Python compatibility, reproducible install and rootless container build/smoke where applicable. Preserve the dependency-free launcher unless a demonstrated need is approved.
- [ ] Assess package publishing, namespace changes, new host adapters and hash-pinned dependency strategy against actual release needs. Publishing requires separate authorization; unavailable registry work is not silently marked done.
- [ ] Close each audit finding with evidence, justified deferral/out-of-scope status or release blocker. No “confirmed” status based solely on the supplied report.
- [ ] Run the full documented checks, baseline compare, hook/hash/lockfile/version/privacy checks and applicable container build. Record exact source revision including a dirty marker when relevant.
- [ ] Commit focused closure/docs changes with configured identity.

### Task 14: Complete real Mac acceptance and handoff

**Files:** Create `docs/refactor/macos-acceptance.md`; update acceptance/checklist and support claims.

**Interfaces:** Produces a release decision with host/OS/app/companion versions, source SHA and scenario outcomes. No release until every required scenario passes.

- [ ] On a real Mac with Claude Pro Desktop and the chosen companion, follow the pasted setup prompt from a clean user configuration. Preserve unrelated settings.
- [ ] In an isolated Anki profile, process synthetic lecture and textbook chapter cases with and without existing decks, inspect source-linked drafts, edit/exclude, approve and verify actual note/card IDs and suspension states.
- [ ] Repeat sources and overlapping topics, resolve pending matches, change configuration explicitly, test source contradictions, and confirm prior history is immutable and searchable outside the review interface.
- [ ] Test host restart, offline Anki, changed collection during review, and interrupted batch recovery. Record uncertainty rather than claiming success where actual reconciliation cannot establish it.
- [ ] Check the actual existing AI quality/visual reviewers run, and compare representative outputs against the preserved baseline. Complete required private-fixture acceptance with the owner; synthetic-only success does not replace it.
- [ ] Have a nontechnical user follow their generated guide and confirm they can locate it and their records. Fix observed onboarding problems within the agreed scope.
- [ ] Hand back evidence and remaining limitations. Do not publish automatically. Windows remains unverified until its own equivalent acceptance passes.

## Dependency order and completion

Tasks 1–3 establish the baseline and feasibility. Tasks 4–6 establish durable state, configuration and evidence. Tasks 7–8 depend on the proven adapter contract; Task 9 depends on exact authorization and proven UI packaging. Task 10 connects the experience. Tasks 11–13 close verified defects and optimise measured costs; Task 14 is the real release gate.

Independent defect fixes may occur earlier after Task 2, but no change to quality-sensitive contracts is bundled as incidental cleanup. If the spike changes a contract, update this plan with concrete transport/UI files and tests before executing the affected tasks. Do not leave an implementer guessing at an unproven host API.

Self-review completed: approved requirements map to Tasks 1–14; all five Review Focus cases have owning tests; adapter/UI uncertainty is an explicit execution gate; no implementation success or real-platform test is claimed by this document.
