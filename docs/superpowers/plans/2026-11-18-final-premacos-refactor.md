# Final Pre-macOS Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the architecture review's justified internal refactors, preserve existing card behaviour and history, and deliver a reproducible package for real macOS compatibility testing.

**Architecture:** Concentrate source discovery, artifact publication and authoritative run discovery in focused modules; keep the existing mechanical engine and stdio tool contracts. Measure coverage-record duplication before adopting one journal event per decision batch, retaining old-history readers. Finish with cross-module recovery tests and an isolated, synthetic macOS test packet.

**Tech Stack:** Python >=3.12, existing Pydantic models, filelock, PyMuPDF, Pillow, Playwright/Chromium, Tesseract, SQLite, Node >=18, dependency-free launcher, rootless Docker.

**Spec:** Read both [architecture review](../../refactor/2026-11-18-architecture-review.md) and [approved student workflows design](../specs/2026-11-18-student-workflows-design.md). Also read [implementation checkpoint](../../refactor/implementation-checkpoint.md), [compatibility gate](../../refactor/compatibility.md) and [audit disposition](2026-11-18-audit-disposition.md).

## Global Constraints

- "macOS is the first supported release platform. Immediate Mac access is unavailable."
- "The first release includes all agreed product features and all verified required fixes. Internal phases are not permission to publish an incomplete subset."
- "Preserve the current house style, selection and combination principles, tiering, tag conventions, rendering and AI reviewer requirements of that actual workflow."
- "Automatic mode skips user review, not quality review."
- "Source references stay in the external record; adding fields or tags to existing card output is not necessary for this feature."
- "Suspension/unsuspension must name actual card IDs, not note IDs."
- "Preserve caller-supplied evidence labels when importing old receipts; migration must not manufacture independent verification or missing lecture-to-card relationships."
- "Preserve records indefinitely by default; explicit cleanup may remove reproducible previews/caches but not audit history or the only source copy."
- "Original documents are never annotated in place; use copies or overlays."
- "The implementation plan must stop at the compatibility gate if the target experience cannot preserve the approved constraints, report evidence and present alternatives."
- Python floor stays `>=3.12`; launcher floor stays `>=18`. Add no runtime dependencies for this pass.
- Keep `src/cards/`, frozen contract tests, `.codex/`, `.agents/` and frozen skills unchanged. Run the existing Linux golden comparison; never refresh it to conceal a regression.
- Keep public MCP tool names, schemas and response shapes unchanged. Internal Python constructors may change with all callers updated. Add no Anki transport, network access or collection operations in this pass.
- Use the existing isolated execution clone and configured identity; inspect status first and preserve unrelated changes. No push, package publication, deployment or live Anki mutation.

## Review Focus

1. A chapter selected earlier remains readable after another extraction or restart; partial text never masquerades as completed labels. Own tests: Task 1.
2. Source/media changes or cancellation during slow work leave the prior published output usable; readers remain responsive. Own tests: Tasks 2–3.
3. Damaged historical records and abandoned staging remain preserved without disabling healthy history, including a previously indexed run damaged without an extra event. Own tests: Task 4.
4. Retrying a coverage batch after interruption or a preference change preserves the original decision and configuration version without duplicate records. Own tests: Task 5.
5. A clean installation under paths with spaces and Unicode can restart, reopen citations and rebuild history without touching host settings or the user's collection. Own tests: Task 6.

---

## Scope and readiness definition

This is one internal refactor pass, split into independently reviewable deliverables. Source discovery and artifact publication share workspace semantics; run discovery and coverage recording share durable history. Keep their commits separate rather than creating several competing top-level plans.

The reviewed starting point is `7dcfd1c` on `refactor/student-workflows`; the review itself inspected `2d546e1`. Reconcile any later changes before execution. Previously reproduced chapter-resume, false-coverage and stale-page defects are already fixed; preserve their regressions rather than presenting them as new bugs.

**Completion means ready for a real macOS compatibility investigation, not a complete first-release end-to-end trial.** The interactive Desktop review experience, independent reviewer execution under Desktop/Pro, companion transport/coordinator and full onboarding integration remain gated by the original plan's Task 3. Do not freeze those interfaces from Linux mocks. Tasks 7–10 and remaining audit/release work in the original plan still follow the compatibility experiment. This plan neither cancels those requirements nor declares all original audit findings closed.

No unrelated CLI redesign, rubric trimming, image-quality reduction, package renaming, new hosts, PDFCraft integration or storage-backend abstraction belongs here. Candidate 4 has a measured adoption gate; a documented negative result is a valid disposition.

## File and responsibility map

| File | Action and responsibility |
| --- | --- |
| `src/ankiplusmcp/source_catalog.py` | Create: source identity, active/retained extraction discovery, partial state, available pages and printed labels. |
| `src/ankiplusmcp/publication.py` | Create: captured input checks, staged replacement, pointer publication and artifact epoch advancement. |
| `src/ankiplusmcp/service.py` | Compose the two modules alongside existing `Store` and `Jobs`. |
| `src/ankiplusmcp/sources.py` | Keep extraction/OCR/figure operations; delegate discovery and publication protocols. |
| `src/ankiplusmcp/evidence.py` | Keep passage matching and evidence formatting; depend on the source catalog instead of the entire `Service`. |
| `src/ankiplusmcp/cards.py`, `review.py`, `server.py` | Consume the focused interfaces without discovering engine paths. |
| `src/ankiplusmcp/store.py` | Keep containment, JSON access and workspace locking; remove `artifact_work` after migrating every caller. |
| `src/ankiplusmcp/run_models.py`, `runs.py` | Add authoritative run-discovery result types and a layout-hiding catalog operation. |
| `src/ankiplusmcp/run_index.py` | Consume that catalog; own SQLite projection and query behaviour only. |
| `src/ankiplusmcp/coverage.py` | If measured gate passes, own shared batch capture, replay and old/new decision reconstruction. |
| `tests/mcp/test_source_catalog.py`, `test_publication.py`, `test_run_discovery.py`, `test_coverage_batches.py`, `test_premacos_workflow.py` | Create focused behavioural and integration regressions; retain existing tests. |
| `tests/tools/coverage_recording_benchmark.py` | Create a disposable-data measurement command; no user history inputs. |
| `scripts/smoke-premacos.py` | Create the isolated synthetic rehearsal and JSON result writer. |
| `docs/refactor/coverage-recording-measurement.md`, `premacos-readiness.md`, `macos-test-packet.md` | Record measurement, exact tested revision/checks and the ordered Mac investigation. |
| `docs/ARCHITECTURE.md`, `README.md`, `docs/refactor/implementation-checkpoint.md`, `acceptance.md` | Update current implementation and honest readiness claims; preserve historical evidence. |

Run tasks sequentially using the user's previously chosen **native** execution method. No implementation is part of writing this plan.

## Task 1: Give the source catalog ownership of extraction discovery

**Files:** Create `source_catalog.py`, `tests/mcp/test_source_catalog.py`; modify `service.py`, `sources.py`, `evidence.py`, `cards.py`, `review.py`, `server.py`, and non-frozen MCP tests that construct `EvidenceResolver`.

**Interfaces:**

- `SourceCatalog(store: Store, jobs: Jobs)`; composition exposes `Service.source_catalog`.
- `SourceCatalog.snapshot(workspace: str) -> SourceSnapshot` acquires one workspace lock. `snapshot_locked(workspace: str) -> SourceSnapshot` is the explicit variant for callers already holding that lock; it never acquires a second workspace lock.
- `SourceDataset` has `prefix: str`, `data: dict`, `labels_pending: bool`. `SourceSnapshot` has `source: dict | None`, `active_prefix: str`, `datasets: tuple[SourceDataset, ...]`, plus read-only `source_hash: str | None`, `source_name: str | None` and `location_kind: Literal['pdf_page', 'text_section'] | None` properties. Evidence formatting uses those properties without inspecting source paths. Treat returned data as a detached read snapshot, not writable storage.
- `SourceSnapshot.current(require_complete: bool = False) -> SourceDataset`, `candidates(page: int, extraction: str | None = None) -> list[tuple[str, dict, bool]]`, `available_pages() -> set[int] | None`, `page_label(page: int) -> str | None`, `labels_pending_for(artifact: str) -> bool`. File discovery, label loading and source-hash validation stay inside `source_catalog.py`.
- `EvidenceResolver(catalog: SourceCatalog).resolve(workspace: str, refs: list[EvidenceRef]) -> list[SourceEvidence]` preserves its return models, 20-reference/24,000-quotation-character limits and whitespace-tolerant exact quotation behaviour.

- [ ] **Step 1: Write failing catalog tests.** Use synthetic two-chapter text/PDFs as in `test_evidence.py`. Assert current extraction comes first; retained matching extractions remain selectable by prefix; wrong-hash and escaping-symlink extractions are excluded; cards-only snapshots return `available_pages() is None`. A live partial marker yields `labels_pending is True`, with figure `ocr_labels` and `repeated_labels` equal to `None`; `current(require_complete=True)` raises `LABELS_PENDING`. An interrupted marker cannot supply partial text. PDF page `1` with Roman printed label returns `page_label(1) == 'vii'`. Changing copied source bytes produces `SOURCE_CHANGED`, not an invented quotation. Close every service in `finally`.

  Name these `test_retained_chapter_catalog`, `test_catalog_excludes_foreign_or_escaping_extractions`, `test_cards_only_catalog`, `test_live_partial_labels`, `test_interrupted_partial_is_not_current`, `test_physical_and_printed_page_labels`, and `test_changed_source_refuses_catalog`. The retained-chapter test uses the existing helpers:

  ```python
  def test_retained_chapter_catalog(tmp_path):
      s, workspace, _ = setup_source(tmp_path)  # from test_evidence
      try:
          wait(s, workspace, s.extract_source(workspace, '1'))
          first = s.source_catalog.snapshot(workspace).current()
          wait(s, workspace, s.extract_source(workspace, '2'))
          snapshot = s.source_catalog.snapshot(workspace)
          assert snapshot.current().prefix != first.prefix
          assert snapshot.candidates(1, first.prefix)[0][0] == first.prefix
          assert snapshot.available_pages() == {1, 2}
      finally:
          s.close()
  ```
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_source_catalog.py`; expect missing catalog/interface failures, not missing native dependencies.
- [ ] **Step 3: Implement the catalog and migrate consumers.** Move active/retained/partial discovery from `Sources` and `EvidenceResolver`. Preserve the legacy `engine` fallback, valid extraction-prefix pattern, published-over-partial precedence and retained source-hash matching. Keep existing internal `Sources.engine/source_data/require_extraction` methods only where existing callers still require them; delegate them to the catalog. Update evidence construction in server/tests. Card checks and review bundles use the catalog under their existing lock; they must not reacquire it. Coverage objectives must still require a completed current extraction. Page-image selection must not import `EvidenceResolver`.
- [ ] **Step 4: Verify GREEN and the deletion test.** Run `.venv/bin/python -m pytest -q tests/mcp/test_source_catalog.py tests/mcp/test_evidence.py tests/mcp/test_sources.py tests/mcp/test_cards.py tests/mcp/test_review_regressions.py tests/mcp/test_protocol.py`. Expect all selected tests to pass. Inspect `evidence.py`, `cards.py` and `review.py`: no retained-extraction globbing or `engine/source/...` discovery remains there. Existing quote/page response fields must be unchanged.
- [ ] **Step 5: Commit.** Stage only this task's production/tests; `git commit -m "refactor: centralize source extraction discovery"`.

## Task 2: Centralize captured-input checks and safe publication

**Files:** Create `publication.py`, `tests/mcp/test_publication.py`; modify `service.py`, `cards.py`, `sources.py`; retain `tests/mcp/test_artifact_revisions.py` coverage.

**Interfaces:**

- `ArtifactPublisher(store: Store)`; composition exposes `Service.publisher`.
- `capture(workspace: str, *, inputs: dict[str, str] | None = None, expected_revision: int | None = None, bind_source: bool = True) -> ArtifactTicket`. Input keys are workspace artifact paths; values are the error code on changed/missing input, e.g. `MEDIA_CHANGED`. `capture_locked(...) -> ArtifactTicket` has the same arguments but requires the caller's workspace lock.
- `ArtifactTicket` contains the workspace, detached manifest, optional expected revision, captured input hashes/error codes and whether source identity/content is bound. No caller mutates the ticket. Capture computes and retains fingerprints; publication never recaptures them.
- `temporary(workspace: str, target: str) -> Iterator[str]` is a context manager yielding a unique workspace-relative temporary path beside its target and deleting only that temporary on exit.
- `publish(ticket: ArtifactTicket, *, replacements: dict[str, str] | None = None, json_records: dict[str, object] | None = None, manifest_changes: dict[str, object] | None = None, cancel: Callable[[], bool] | None = None) -> None`. Replacements map staged workspace-relative paths to final paths. Validate everything under one short workspace lock before replacements, then publish JSON pointers and the manifest/artifact epoch. It performs no operation-specific rendering/OCR callbacks.
- `manifest_changes` permits only `source_engine` in this pass. The publisher owns `revision`, `artifact_revision` and `updated`; callers cannot override them. All file destinations must pass containment checks and must not be under `input/`.

- [ ] **Step 1: Write failing publication tests.** Assert cancellation/source mutation/input mutation/revision mismatch reject before any replacement or pointer update, retain the original target bytes and leave both revisions unchanged. Successful publication advances `artifact_revision` once and preserves semantic `revision`. Use `threading.Event` barriers around slow work and `future.result(timeout=.5)` to prove `get_cards` remains readable. When media changes without card revision advancing, expect `MEDIA_CHANGED`. A publication failure before replacement cleans its temporary; an exception after one of several renames must not be described as a transaction or delete historical outputs. Reject absolute paths, traversal and symlinks through existing `Store.path` checks, and refuse any replacement/JSON destination under `input/`.

  Name the cases `test_publication_rejects_changed_dependencies` (parameterized cancellation/source/media/revision), `test_success_advances_artifact_epoch_only`, `test_work_does_not_block_reads`, `test_temporary_cleanup_preserves_target`, `test_partial_publish_failure_preserves_history`, and `test_publication_path_containment`. Include this changed-media assertion without requiring valid image bytes or native rendering:

  ```python
  def test_changed_media_cannot_publish_pointer(tmp_path):
      s = Service(tmp_path / 'data', [tmp_path])
      try:
          workspace = s.store.create('cards')['id']
          s.store.write_json(workspace, 'media/input.json', {'value': 1})
          ticket = s.publisher.capture(workspace, inputs={'media/input.json': 'MEDIA_CHANGED'})
          s.store.write_json(workspace, 'media/input.json', {'value': 2})
          with pytest.raises(DomainError, match='MEDIA_CHANGED'):
              s.publisher.publish(ticket, json_records={'latest-test.json': {'ready': True}})
          assert not s.store.path(workspace, 'latest-test.json').exists()
          assert s.store.get(workspace).get('artifact_revision', 0) == 0
      finally:
          s.close()
  ```
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_publication.py`; expect the new interface tests to fail.
- [ ] **Step 3: Implement publication and migrate rendering/page images.** Render captures selected cards, card revision, `cards.json` and selected media fingerprints under the same initial lock, before queueing native work. Use `bind_source=False` for card-only rendering to retain its existing dependencies. Publish `latest-preview.json` through the publisher, preserving preview metadata and `_committed` handling. Page rendering captures source identity and uses `temporary` plus a replacement, so rejected work cannot overwrite an earlier page. Publication owns validation order, cancellation checks and artifact epoch changes; callers own their output formats.
- [ ] **Step 4: Verify GREEN.** Run `.venv/bin/python -m pytest -q tests/mcp/test_publication.py tests/mcp/test_artifact_revisions.py tests/mcp/test_cards.py tests/mcp/test_review_regressions.py tests/mcp/test_evidence.py`. Expect all selected tests to pass, including the existing rejected-page and stale-render regressions. No rendering/template/PNG-quality change is permitted.
- [ ] **Step 5: Commit.** `git add src/ankiplusmcp/publication.py src/ankiplusmcp/service.py src/ankiplusmcp/cards.py src/ankiplusmcp/sources.py tests/mcp/test_publication.py`; `git commit -m "refactor: centralize artifact publication checks"`.

## Task 3: Migrate the remaining native operations to publication

**Files:** Modify `sources.py`, `store.py`, `source_catalog.py`, `tests/mcp/test_publication.py`, `tests/mcp/test_source_catalog.py`, `tests/mcp/test_artifact_revisions.py`; extend `tests/mcp/test_adapters.py` only where necessary to assert existing outputs.

**Interfaces:** Consume Task 1's source snapshots and Task 2's publisher. Existing `extract_source`, `ocr_image`, `export_figures`, `build_occlusion` and `measure_usage` signatures/results remain unchanged. Remove `Store.artifact_work` only after its final caller is migrated.

- [ ] **Step 1: Write failing cross-operation tests.** Parameterize delayed OCR/export/occlusion work: change a captured input or cancel before publication; assert no new current pointer or successful job result, unchanged semantic revision and unchanged prior artifacts. Cancellation applies to existing asynchronous jobs; synchronous occlusion tests changed inputs without adding a new cancellation parameter. Extraction must retain the early map/summary and pending-label signals during a live job, preserve current extraction on cancellation, reuse the same valid cached extraction without another artifact epoch, and expose complete labels only after success. While two extractions overlap, finishing one must not remove the other's partial marker. Assert native exceptions clean only operation-owned temporary files, never retained extraction folders or run history.

  Name these `test_native_operation_rejects_changed_dependency`, `test_native_operation_cancel_preserves_prior_artifacts`, `test_overlapping_extractions_keep_other_partial_marker`, and `test_native_failure_preserves_retained_history`. Retain existing `test_map_and_figures_while_labels_pending`; add the cache epoch case using `lecture`/`wait` from `test_sources`:

  ```python
  def test_cached_extraction_keeps_artifact_epoch(tmp_path):
      s, workspace = lecture(tmp_path)
      try:
          wait(s, workspace, s.extract_source(workspace))
          epoch = s.store.get(workspace)['artifact_revision']
          cached = wait(s, workspace, s.extract_source(workspace))
          assert cached['cached'] is True
          assert s.store.get(workspace)['artifact_revision'] == epoch
      finally:
          s.close()
  ```
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_publication.py tests/mcp/test_source_catalog.py tests/mcp/test_artifact_revisions.py`. At least the newly missing migration/marker behaviour must fail; retain the failure output.
- [ ] **Step 3: Migrate native operations.** Extraction still writes into a fresh `extractions/<uuid>/engine` directory; OCR/export/occlusion/usage keep their existing unique output names. These directories are unpublished outputs until their result/current pointer is committed, rather than a reason to redesign paths. Use the publisher for captured dependencies, final cancellation, manifest changes and epoch advancement. Preserve extraction progress/cache rules and `_committed` semantics. Update the partial marker under the workspace lock, comparing its prefix before removal; do no slow native work while holding that lock. Leave abandoned unique output recoverable; no automatic pruning is introduced. Remove callback dictionaries and duplicate publication checks now owned by `publication.py`.
- [ ] **Step 4: Verify GREEN and the deletion test.** Run `.venv/bin/python -m pytest -q tests/mcp/test_publication.py tests/mcp/test_source_catalog.py tests/mcp/test_artifact_revisions.py tests/mcp/test_sources.py tests/mcp/test_adapters.py tests/mcp/test_review_regressions.py`. Expect all selected tests to pass. Run `rg 'artifact_work' src/ankiplusmcp`; expect no matches. Inspect that expensive functions run outside the workspace lock and operation modules no longer perform their own final fingerprint/revision/epoch protocol.
- [ ] **Step 5: Commit.** Stage this task's changed files; `git commit -m "refactor: unify native artifact publication"`.

## Task 4: Hide authoritative journal layout from the index

**Files:** Modify `run_models.py`, `runs.py`, `run_index.py`; create `tests/mcp/test_run_discovery.py`; retain existing run/migration/history CLI tests.

**Interfaces:**

- Add `RunProjection(snapshot: RunSnapshot, token: str)` and `RunCatalog(changed: list[RunProjection], unchanged_ids: list[str], errors: dict[str, str])` to `run_models.py`.
- `RunStore.catalog(known: dict[str, str] | None = None) -> RunCatalog` owns directory enumeration, hidden/staging exclusions, path checks, per-run locking, freshness and error containment. Returned collections are sorted by run ID. Capture the token and changed snapshot under the same run lock.
- Freshness tokens fingerprint event filename/size/`mtime_ns` metadata; this is a cache invalidation mechanism, not an integrity/independent-verification claim. Unknown tokens force validated reads. Do not parse unchanged event JSON on ordinary repeated searches. File content validation still uses existing `_records` when a token changes and during a full rebuild.
- `RunIndex.search(RunQuery) -> RunPage` and `rebuild() -> int` stay unchanged. Add a nullable SQLite `journal_token` column using `PRAGMA table_info` plus a one-time `ALTER TABLE`; existing rows with no token refresh normally. Use explicit INSERT column lists.

- [ ] **Step 1: Write failing discovery tests.** Create healthy, corrupt, staged and symlinked synthetic run directories. Assert healthy runs remain searchable, corrupt/symlinked runs produce per-run errors, hidden staging is excluded and every original file remains. After indexing, corrupt an existing event without adding an event; force a distinct `mtime_ns` and assert the next search removes its stale projection and reports `RUN_CORRUPT`. Repaired history must reappear and clear its error. With identical tokens assert no event JSON is reparsed. A paused append/discovery pair must yield either complete old or complete new history, never a partial event. An old SQLite schema without `journal_token` must upgrade without losing healthy results.

  Name these `test_catalog_contains_bad_run_errors`, `test_index_detects_changed_existing_event`, `test_repaired_run_reappears`, `test_unchanged_catalog_does_not_reparse`, `test_catalog_and_append_take_consistent_snapshot`, and `test_old_index_schema_upgrades`. The catalog's unchanged-data contract is pinned directly:

  ```python
  def test_catalog_returns_unchanged_run_ids(tmp_path):
      store = RunStore(tmp_path)
      run = store.start('lecture1', SourceSelection(label='Cells'), 1)
      first = store.catalog()
      assert [item.snapshot.id for item in first.changed] == [run.id]
      known = {item.snapshot.id: item.token for item in first.changed}
      again = store.catalog(known)
      assert again.changed == []
      assert again.unchanged_ids == [run.id]
      assert again.errors == {}
  ```
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_run_discovery.py`; expect missing catalog and unchanged-sequence corruption cases to fail.
- [ ] **Step 3: Implement discovery and migrate indexing.** Move run-layout/freshness knowledge into `RunStore.catalog`. `_sync` passes known tokens, updates changed projections, retains unchanged rows and removes stale projections for missing/error runs; remove corresponding lookups/errors when appropriate. Keep SQLite transactions, positive note/card identity distinction, recency pagination and bounded error output. Translate a per-run lock timeout into retryable `BUSY` evidence without terminating healthy discovery. Do not delete authoritative files.
- [ ] **Step 4: Verify GREEN and the deletion test.** Run `.venv/bin/python -m pytest -q tests/mcp/test_run_discovery.py tests/mcp/test_runs.py tests/mcp/test_run_migration.py tests/mcp/test_history_cli.py`. Expect all selected tests to pass. `run_index.py` must no longer access `store.directory`, `store._path`, event filename patterns or staging-directory conventions.
- [ ] **Step 5: Commit.** Stage this task's four files; `git commit -m "refactor: hide run journal layout from indexing"`.

## Task 5: Measure coverage duplication and adopt batch capture only if justified

**Files:** Create `tests/tools/coverage_recording_benchmark.py`, `docs/refactor/coverage-recording-measurement.md`; conditionally create `tests/mcp/test_coverage_batches.py` and modify `coverage.py`, `tests/mcp/test_coverage.py`. Do not rewrite stored history.

**Interfaces:**

- Measurement command: `.venv/bin/python tests/tools/coverage_recording_benchmark.py --output .artifacts/premacos/coverage-before.json`; synthetic cases use 1/10/100 distinct concepts and 0/20/500 existing notes. Each invocation owns a `TemporaryDirectory` and closes every service. Record case sizes, journal bytes, repeated snapshot bytes, event count, history reads, write/search elapsed time and Python/platform/revision metadata. Timing is informational, not a flaky CI assertion.
- Adoption gate (engineering choice): implement the batch format only if repeated collection snapshots consume at least **25% of journal bytes** for a synthetic 100-decision case with 20 or 500 notes. Otherwise retain current storage and record why this candidate is deferred. This threshold is not a user requirement or a claim about real workload frequency.
- If adopted: `CoverageStore.record(run_id: str, snapshot: CollectionSnapshot, decisions: list[CoverageDecision], *, batch_id: str | None = None) -> list[CoverageDecision]`. Existing positional calls still work. A supplied batch ID uses `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`; absent IDs get a fresh UUID.
- Store one `coverage_batch` event with `payload_version: 1`, batch ID, canonical request digest, one collection snapshot, actual `config_version`, normalized decisions with their evidence, aggregate positive `note_ids`/`card_ids`, `evidence_origin: caller_supplied` and `independently_verified: false`. The event ID is `coverage-<batch_id>`.
- `latest(run_id: str) -> list[CoverageDecision]` reads both old `coverage_decision` and new `coverage_batch` events in sequence; later decisions win per concept. Raw history/export retains original event shapes. Aggregate IDs keep existing index searches working.

- [ ] **Step 1: Measure current storage.** Implement the measurement command, run it, verify the byte fraction calculation against generated files, and record results/threshold outcome. No network or actual collection snapshots. If the gate fails, commit the measurement/report and skip Steps 2–5 explicitly; proceed to Task 6 with candidate 4 deferred.
- [ ] **Step 2: Write failing batch tests if the gate passes.** Assert 100 decisions persist one snapshot/event, invalid final decisions write nothing, and old/new mixed history reconstructs the same latest decisions. Inject failure before the event rename; assert no batch is visible, then retry with the same ID and assert one complete batch. Repeating the same ID/input must not append; changed input with the same ID raises `CONFLICT`. Change saved preferences after the first success and retry: original normalized dispositions/config version must remain. A fresh batch uses new preferences. Concurrent identical retries return the recorded winner once. Assert `note_id` and `card_id` searches still distinguish their units and caller evidence remains unverified. Reject out-of-range batch IDs and 0/101 decisions without writing anything.

  Name these `test_batch_stores_snapshot_once`, `test_invalid_batch_records_nothing`, `test_mixed_coverage_history`, `test_interrupted_batch_retries_once`, `test_conflicting_batch_id_is_refused`, `test_batch_retry_keeps_original_preferences`, `test_concurrent_batch_retry_has_one_winner`, `test_batch_search_keeps_note_card_units`, and `test_batch_limits`. Use `setup`/`decision` from `test_coverage` for the preference case:

  ```python
  def test_batch_retry_keeps_original_preferences(tmp_path):
      s, coverage, run, snapshot, sha = setup(tmp_path)
      try:
          inputs = [decision(sha, uncertain=True)]
          first = coverage.record(run.id, snapshot, inputs, batch_id='retry1')
          change = coverage.config.propose({'review_mode': 'automatic', 'uncertain_match': 'create'}, 1)
          coverage.config.confirm(change.id)
          retry = coverage.record(run.id, snapshot, inputs, batch_id='retry1')
          assert first == retry
          assert retry[0].disposition == 'pending'
          events = coverage.runs.read(run.id).events
          assert len(events) == 2
          assert events[-1].payload['config_version'] == 1
          assert coverage.record(run.id, snapshot, inputs, batch_id='next1')[0].disposition == 'propose_create'
      finally:
          s.close()
  ```
- [ ] **Step 3: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_coverage_batches.py`; expect missing batch-ID/format/replay behaviour to fail.
- [ ] **Step 4: Implement batch recording and mixed replay.** Canonical request digest covers run ID plus the supplied snapshot/decisions; exclude newly read preferences so an exact retry can recover the original committed answer. Look up an existing batch before reevaluation; compare digest and return its recorded decisions. Validate/resolve all decisions and capture one configuration version before a single `RunStore.append`. If concurrent append reports conflicting event reuse, reread the winner and return it only when its request digest matches. Do not change ownership checks, uncertainty policies, source-selection checks or contradiction handling. One event's atomic publication does not imply a transaction with configuration/source files or Anki. Distinct batches remain separate history.
- [ ] **Step 5: Verify GREEN and compare measurements.** Run `.venv/bin/python -m pytest -q tests/mcp/test_coverage_batches.py tests/mcp/test_coverage.py tests/mcp/test_runs.py tests/mcp/test_history_cli.py`; expect all selected tests to pass. Rerun the benchmark to `.artifacts/premacos/coverage-after.json`; compare the same synthetic cases, record bytes/event/read counts and informational timing. Require one shared snapshot/event for the 100-decision batch and unchanged reconstructed decisions; investigate any regression rather than inventing real-user performance claims. Commit production/tests/measurement/report with `git commit -m "refactor: record shared coverage batches"`.

## Task 6: Prove the refactor together and prepare the Mac investigation

**Files:** Create `scripts/smoke-premacos.py`, `tests/mcp/test_premacos_workflow.py`, `docs/refactor/premacos-readiness.md`, `docs/refactor/macos-test-packet.md`; modify `docs/ARCHITECTURE.md`, `README.md`, `docs/refactor/implementation-checkpoint.md`, `docs/refactor/acceptance.md`. Retain `compatibility.md` as the unpassed real-host gate.

**Interfaces:**

- `.venv/bin/python scripts/smoke-premacos.py --output .artifacts/premacos/smoke.json` creates only temporary synthetic inputs/data and writes the explicitly selected result file without overwriting an existing file. It never connects to Anki or registers host configuration.
- The script exposes `run_scenarios(data_root: Path) -> dict[str, dict]` and `main(argv: list[str] | None = None) -> int`. Its temporary root uses the prefix `Study notes — اختبار `; create the output parent if needed and open the result file exclusively. Scenario keys are `chapter_resume`, `draft_render`, `coverage_history`, `real_ocr` and `stdio`; each has `status: 'passed' | 'failed'` and an error message only on failure. `stdio` invokes the existing `scripts/smoke-mcp.py` in the same disposable environment.
- Results contain `schema_version: 1`, source revision plus dirty status, platform/Python/tool versions, named scenario outcomes and `performed_anki_operations: 0`. Top-level `status` is `local_refactor_verified` only when every scenario passes, otherwise `failed`. Exit `0` means every local scenario passed; exit `1` means a scenario failed; CLI misuse/existing output returns `2`. Missing Tesseract/Chromium is a named failure, never a pass/skip.
- A local result is labelled `local_refactor_verified`; `desktop_compatibility`, `independent_reviewers`, `companion_write_recovery`, `onboarding_integration` and `private_quality_acceptance` remain `not_run` until actual evidence exists.

- [ ] **Step 1: Write failing workflow tests.** Run a two-chapter synthetic PDF under a temporary directory named `Study notes — اختبار`. Extract chapter 1, resolve/store its citation, extract chapter 2, patch a draft, render it, and assert semantic revision is unchanged by rendering. Close/reopen `Service`/`RunStore`, reopen chapter-1 evidence/page, rebuild the deleted SQLite index and find a coverage decision by actual test note/card IDs. Assert source-copy hashes and old event bytes remain unchanged. Add script-subprocess tests for an existing output file, missing native dependency, and a failing scenario; assert exit codes/output statuses and no writes to host config. Fake native failure only in the error-path test; the successful rehearsal uses real extraction, OCR and Chromium.

  Name these `test_unicode_path_rehearsal`, `test_smoke_refuses_existing_output`, `test_smoke_missing_dependency_fails`, and `test_smoke_failed_scenario_exits_one`. For the successful subprocess case, assert these exact report fields:

  ```python
  assert completed.returncode == 0, completed.stderr
  report = json.loads(output.read_text())
  assert report['schema_version'] == 1
  assert report['performed_anki_operations'] == 0
  assert report['status'] == 'local_refactor_verified'
  assert report['scenarios']['chapter_resume']['status'] == 'passed'
  assert report['scenarios']['coverage_history']['status'] == 'passed'
  assert report['desktop_compatibility'] == 'not_run'
  ```
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest -q tests/mcp/test_premacos_workflow.py`; expect missing rehearsal-script/report behaviour to fail.
- [ ] **Step 3: Implement the rehearsal and documentation.** Generate the PDF and a high-contrast `FIBROBLAST` image in the script, use existing service tools for real OCR/rendering, and reuse the tested scenario helper from the script in the integration tests. Use fresh disposable roots and no external private inputs. Add an MCP architecture section describing the new modules, lock order, file authority/SQLite projection, partial labels and evidence limits; label legacy-only architecture claims clearly without rewriting historical decisions. Append new checkpoint evidence rather than overwriting earlier results. The readiness document maps all four review candidates to commits/tests or the measured deferral and lists remaining original-plan/audit work honestly.
- [ ] **Step 4: Run all local gates once against the final source.** Run `uv sync --frozen --extra dev`, `uv lock --check`, then `CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract`. Run `./scripts/check-mcp.sh`, `npm test`, and the new rehearsal command. Expect exit 0 for all; the Linux golden must report `IDENTICAL` for the existing 66 artifacts/14 commands. Retain counts/skips and exact commands in ignored `.artifacts/premacos/`; 24 unavailable private-fixture cases remain unresolved acceptance, not waived. Investigate new skips or count changes. Existing hook/hash/version/privacy and wheel checks in `check-mcp.sh` must all pass. Do not claim hosted CI passed without running it through a separately authorized push.
- [ ] **Step 5: Build and check the hardened container.** Read the host container-infrastructure README referenced by the user's AGENTS instructions for current host limits. Derive `ANKIPLUS_REVISION` from `git rev-parse --short HEAD` and append `-dirty` if tracked or untracked source changes are present. Run `docker compose -p ankiplusmcp config --quiet` and `docker compose -p ankiplusmcp build` with that environment. Run `docker compose -p ankiplusmcp run --rm --no-deps --entrypoint python mcp -c 'import os,tempfile; from pathlib import Path; from PIL import Image,ImageDraw,ImageFont; from ankiplusmcp.service import Service; from cards.extract.ocr import extract; from cards.render import render_rows; assert os.getuid()!=0; d=tempfile.TemporaryDirectory(dir="/tmp"); p=Path(d.name); im=Image.new("RGB",(800,160),"white"); ImageDraw.Draw(im).text((20,30),"FIBROBLAST",font=ImageFont.load_default(size=48),fill="black"); im.save(p/"ocr.png"); assert extract(p/"ocr.png")["regions"]; s=Service(p/"data",[p]); w=s.store.create("cards")["id"]; s.save_cards(w,[{"id":"smoke","fields":{"Text":"{{c1::Fibroblast}}"}}],0); assert render_rows([{"id":"smoke","question":"Fibroblast?","answer":"Fibroblast"}],p/"render"); assert s.store.get(w)["revision"]==1; s.close(); print("PASS: nonroot real OCR/render; no Anki operations")'`. Expect exit 0 under the existing read-only/network-disabled/cap-drop limits. Do not relax them. Record the exact image revision and outcome; no public route is involved.
- [ ] **Step 6: Write the ordered Mac packet.** Include prerequisite versions to record, a local build/install from this exact reviewed revision (use the built wheel/npm tarball via existing `ANKIPLUSMCP_PY_SPEC`, not the remote `v0.3.0` default), clean installation/restart/path tests, and the rehearsal command. Explain that macOS uses real OCR/render checks rather than Linux PNG byte identity. Then give the compatibility experiment from `compatibility.md`: local embedded review prototype, fresh maintainer/student contexts under Pro, exact companion capability discovery in an isolated Anki profile, note/card IDs, partial outcomes and interrupted writes. Mark companion mutations as awaiting an explicitly authorized isolated-profile session. Record `blocked` with versions/evidence when a combination fails; do not replace reviewers or require an API key. Full first-release scenarios follow only after the resulting original-plan integration tasks are implemented. Keep guide/onboarding and private-quality acceptance visibly outstanding.
- [ ] **Step 7: Review, record and commit the handoff.** Using the preserved native method, obtain one fresh whole-branch review after the tasks and checks; do not start per-task implementation agents. Have the reviewer inspect deletion tests, old-data compatibility, stale publication, replay and claimed Mac readiness. Fix material findings and rerun affected checks. Record final source SHA/dirty status, commands/outcomes, actual skips, measured deferrals and outstanding gates in `premacos-readiness.md`. Commit the focused handoff files. Documentation-only follow-up commits do not require rerunning unchanged native checks; identify which source revision those results cover. Do not push or claim release readiness.

## Completion checklist

- [ ] Source-path/extraction discovery is owned by the source catalog; consumers lose that implementation knowledge.
- [ ] Native operations use one publication protocol; stale/cancelled work preserves usable prior output.
- [ ] The index consumes authoritative discovery without knowing journal layout, and old indexes/history still work.
- [ ] Coverage has a measured disposition; if adopted, old/new records replay correctly and batch retries preserve prior answers.
- [ ] Cross-module restart tests, public suite, launcher, Linux golden, packaging/guards and hardened container smoke pass with exact revision evidence.
- [ ] Mac packet distinguishes local verification, the real-host compatibility experiment and later complete-product acceptance.
- [ ] Required original audit/product work remains tracked, not implicitly closed by this refactor.
- [ ] A fresh final review is resolved; no code is pushed, published or applied to a live collection.

## Plan self-review

All four architecture candidates map to Tasks 1–5, and every Review Focus condition has an owning test. Task 6 owns combined verification and the Mac handoff. Interfaces above use existing domain models; task dependencies are 1 → 2 → 3, then 4 → 5, followed by 6. The preserved native execution preference applies after plan review. This is a bounded supplement to the approved product plan, not a replacement for its remaining gated features or release acceptance.
