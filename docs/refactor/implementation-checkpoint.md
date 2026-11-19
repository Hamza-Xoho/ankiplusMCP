# Native implementation checkpoint

Work is on branch `refactor/student-workflows`, starting at `b0f4233`. The full approved design is not implemented and nothing is released, pushed or deployed. The older local checkout and the user's Anki collection are untouched.

## Implemented and locally verified

- Public deterministic CLI snapshot: 14 real CLI calls and 66 artifacts; fixed external OCR responses, real extraction and Chromium rendering. Image byte hashes catch same-size media changes, and dependency failures cannot be recorded as a good golden baseline.
- CI definitions now include frozen-contract/hook/lockfile checks, a Python 3.12/3.14 test matrix, dynamic wheel/tarball discovery and a Linux golden comparison. Hosted CI execution and cross-platform screenshot equivalence are not verified.
- Separate run/source-selection records, durable append-only events, immutable snapshots and an incremental, rebuildable SQLite index. Invalid identity lists cannot poison history; damaged historical runs remain on disk and appear as explicit index errors while other history remains searchable.
- Non-destructive legacy import preserving source absence, unknown configuration versions, caller evidence and missing draft relationships.
- Versioned configuration with propose/confirm, explicit saved changes, immutable prior versions, concurrent-change refusal and default manual review/uncertain-match pending. This is a backing library, not completed onboarding.
- Derived images/extraction/OCR/previews use an artifact epoch rather than advancing the semantic workspace revision. Native work runs outside long exclusive locks, with bounded BUSY errors and publication checks for stale cards, changed inputs and cancellation.
- Rejected page rendering preserves the prior published page. Rendering snapshots bind the actual input card/media state rather than whatever cards happen to exist when rendering finishes.
- Existing caller-result recording now accumulates batch receipts, deduplicates replayed evidence and retains a sequenced journal. Recovery replays a receipt saved before an interrupted projection update. No independent Anki verification is invented.

## Verification evidence

- Full suite in the repository's existing public-CI mode: **557 passed, 25 skipped**.
- Baseline full local contract mode: **261 passed, 1 failed, 23 errors**, with all 24 affected cases requiring unpublished private lecture/transcript fixtures. These are not waived release checks.
- Launcher: **29 passed**.
- Existing host hook verifier: **42/42 passed**.
- Frozen-contract hashes: **12/12 intact**.
- CLI snapshot comparison: **IDENTICAL, 66 artifacts and 14 commands**, including frozen dependency environment.
- Wheel build, version/privacy checks and lockfile consistency passed during baseline/check verification. The existing setuptools license deprecation warning remains.
- New-file privacy scan and whitespace checks pass.
- Rootless Compose configuration and image build passed after installing the missing `libatomic1` bootstrap dependency. The hardened smoke passed as UID 1000 with real OCR (1 region), real Chromium rendering (1 sheet) and unchanged semantic card revision 1. It used a read-only filesystem, network disabled, dropped capabilities, no-new-privileges and resource limits. The image is labelled `b0f4233-dirty`, accurately identifying the uncommitted build input.

Full command output and RED→GREEN evidence remain in the ignored per-plan execution ledger directory. Tests requiring private fixtures must be rerun with actual inputs before acceptance. No model-driven card-quality acceptance or real collection write has been performed.

## Review and rulings

A fresh reviewer checked this implementation subset, including new untracked files. Two material issues were reproduced with failing tests and fixed: stable cached pages being overwritten before source validation, and malformed identity lists disabling the global index. Corrupt historical records now get explicit per-run index errors. No re-review was substituted for the covering tests and green suite.

Execution rulings, including their costs:

1. Use a fresh isolated clone because the native worktree control targets the unrelated portal project and the existing AnkiPlus checkout is dirty. Cost: extra disk space and an explicit later branch handoff.
2. Do not invent a Git identity. The user subsequently supplied author details and local checkpoint commits were made. Cost while unresolved: commits could not serve as checkpoints; this is now resolved.
3. Invoke non-executable shared skill helpers through Bash or reproduce their bookkeeping locally. Cost: manual ledger bookkeeping must retain task boundaries.
4. Continue transport-independent foundations without claiming the Desktop compatibility gate passed. Cost: these libraries still require later coordinator/onboarding integration.
5. Use content hashes for PNG snapshots and a Linux-only golden lane. Cost: font/renderer or hosted runner drift can cause a comparison failure that must be investigated.
6. Update the four non-frozen MCP tests whose revision inputs counted image imports/rendering. Their behavioural assertions remain; the revision semantic change is intentional and approved. Cost: old clients must use current revision values rather than assume artifact work increments them.
7. Preserve imported legacy configuration as unknown rather than assigning an invented version. Cost: consumers must handle unknown historical preferences.
8. Compare the golden in the frozen environment as well as a freshly resolved environment. Cost: dependency updates may require explicit baseline review.
9. Retain strict hosted baseline checks but do not claim unexecuted GitHub runner equivalence. Cost: remote renderer/font differences remain a CI risk until that job is exercised.

## Remaining implementation and external gates

The backing libraries are not yet connected to the full user workflow. Live collection coverage searches, the companion coordinator, exact user approval, the interactive review interface, completed onboarding and several audit repairs remain outstanding. Source evidence, coverage decision recording, separate history access and guide generation are now implemented as described below; their existence is not a claim that the entire workflow is integrated.

The approved design requires proving the actual local Desktop UI + independent maintainer/student reviewers + Anki companion combination before freezing transport/UI implementation. No real Mac/Desktop session or isolated live Anki is available here. Public documentation suggests routes to investigate, but it cannot establish that the complete combination meets the Pro subscription and quality-preservation constraints. See `compatibility.md` for the actual test procedure.

The container's mechanical-only `network_mode: none` is retained. A future companion connection needs its own explicitly tested execution topology; this checkpoint does not weaken the current container isolation as a workaround.

## Local commits

- `00aa08c`: reproducible CLI regression checks.
- `a780dee`: durable run history and explicit preferences.
- `d0250f8`: artifact revision isolation and cumulative receipt preservation.

Container and documentation checkpoints follow these commits. No commit has been pushed.

## Continued native implementation

The next locally verified batch adds:

- Exact stored source quotes through `get_source_evidence`, with OCR labels, physical PDF pages and printed page labels. Citations retain extraction identity and can resolve earlier chapters after later selections replace the active extraction. Original page images can likewise be reopened. Source-reference checking uses retained matching source versions.
- Coverage decision records tied to source selection and supplied collection snapshots. Actual note/card ownership is checked. Uncertain matches follow explicitly saved preferences; disagreements stay pending. Missing selected card IDs never manufacture active coverage. Caller data remains labelled unverified. These records do not execute collection operations.
- Separate `history` CLI list/search/show/export/rebuild/import commands. Exports cannot overwrite existing files; JSON list results are bounded summaries, and detailed history can be explicitly inspected or exported.
- `patch_cards` edits one or more drafts without resending the full set, preserving untouched data, invalidating stale cached HTML and refusing stale or malformed updates. Concurrent real edits survive a stale patch attempt; no-op patches preserve revision.
- Workspace labels, honest creation/activity timestamps, recency pagination and bounded `list_jobs` discovery. Unknown dates in old workspaces stay unknown.
- Personalised seven-section beginner guide generation, including reasons and workflow-appropriate prompts. Personal notes survive regeneration; other user edits or unrelated existing documents are preserved by refusal. Setup is never presented as verified when supplied capabilities are incomplete. Host onboarding integration is still pending.
- The Windows Desktop APPDATA configuration-path defect is fixed in platform-simulated launcher tests. This does not establish actual Windows support.
- Legacy P6 write counts are checked before recording success/completing the phase, leaving mismatches recoverable. Concurrent `build --continue` attempts use a nonblocking per-build lock. Existing report/count semantics and successful CLI artifact output remain unchanged.

Fresh whole-checkpoint review found the earlier-chapter and false-coverage issues above; failing regressions reproduced them, and the fix pass plus full suite passed. No claim is made about untested Mac/Windows host behaviour, live collection writes, independent host reviewers or unavailable private fixtures.

Latest verification: 557 passed and 25 skipped in public-CI mode; 29 launcher tests; 42 hook checks; intact frozen hashes; wheel build; identical 66-artifact/14-command CLI baseline. The reviewed image `fdf008b-dirty` passed the non-root/read-only/network-disabled real OCR/Chromium smoke. Hosted CI runner behaviour remains unverified until a separately authorised push runs it.

Additional execution rulings:

10. Use generic citation `page` plus explicit `location_kind`, rather than calling text sections PDF pages. Cost: callers must use the new typed evidence shape.
11. Apply explicitly saved preferences to later decisions in the same run, recording the actual configuration version per event. Cost: later authorization must bind relevant current preferences rather than only the initial run version.
12. Retain source-hash-matching extraction identity/history for chapter citations. Cost: derived-artifact cleanup must respect historical citation dependencies.
13. Require usable selected card IDs before declaring active coverage. Cost: incomplete caller snapshots stay pending instead of being treated as successful matches.

## Final pre-macOS architecture pass

The approved six-task supplement centralizes source discovery and native publication, hides run layout from indexing and adopts shared coverage batches after synthetic measurement met its 25% duplication gate. Historical event readers remain; no old history was rewritten. See `premacos-readiness.md` for revision-specific verification and `macos-test-packet.md` for the unpassed real-host gate. Earlier checkpoint evidence above is retained. Full product integration and private acceptance are still outstanding.

Final source `290b246` passed 615 public-CI tests with the existing 25 skips, 382 check-mcp tests/one system-Chrome skip, all frozen hashes/42 hooks, unchanged 66-file/14-command golden, five synthetic rehearsal scenarios and source/evidence/history recovery regressions. Launcher remains 29/29. The single fresh review produced three material findings, all fixed with RED→GREEN tests. Exact logs and container outcome are in `premacos-readiness.md`; the real Mac/private acceptance gates are still open.

## Inline continuation after 9e6cfb0

The 2026-11-19 Linux resumption verified the clean isolated branch and fetched
origin with no drift. Mac reviewer transcripts and active-companion
registration/serverInfo/schema evidence remain unavailable from this host. The
subsequent supplied report describes the gate instructions, not their execution;
it establishes no new reviewer or companion result. Raw private evidence should
remain in ignored Mac artifact locations; return sanitized findings with original
paths/hashes rather than committing host configuration or private transcripts.
The existing user-reported UI passes and earlier limitations remain as recorded
in `compatibility.md`. No profile changes or collection operations were performed.

Independent audit work repairs damaged-job discovery: malformed records no longer
hide valid jobs, invalid owner identities are refused before probing leases, and
original records remain intact. `list_jobs` retains its clean response shape;
on damage it additionally returns bounded `errors` and `error_total`. The existing
`offset`/`limit` page valid summaries and error summaries independently, with
`next_offset` until both are exhausted; `total` still counts valid filtered jobs.
This is partial A7/B3/E2 progress, not completion of those audit items or Task 12.
Exact RED/GREEN and final verification evidence remain in the original plan ledger.
Adapter/coordinator/UI/onboarding integration, further audit work and all required
external acceptance remain incomplete. A complete payload-specific isolated-profile
proposal requires the actual companion schemas before requesting authorization.

### Fresh engineering review and receipt recovery

The single fresh whole-branch engineering review covered `b0f4233..758dd18`
(including the version-test repair), independently ran 113 focused tests, and
reported one Important finding, no Critical findings and no deferred Minors.
A durable caller receipt could be omitted from reports and legacy history imports
after interruption between journal publication and projection publication.

Fix `510c1e4` adds shared read-only projection/journal folding to recording,
reporting and import. Four restart regressions failed first for both absent and
older projections, then passed without another recording call. A fifth failed-first
regression preserves the exact old projection wrapper and therefore its import
fingerprint. Reports lock the workspace for consistent reads. Import/report reads
retain original JSON bytes and semantic revisions. All recovered results retain
caller-supplied provenance; no external readback or Anki success is manufactured.
The affected result/history/card suite passed 33 tests with one existing browser
skip. No second review was substituted for the regression fix pass.

Fresh checks after the fix:

- `CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q`: **634 passed, 25 existing skips**.
- `./scripts/check-mcp.sh`: **401 passed, one existing skip**; all frozen hashes,
  wheel/version/privacy checks, **42/42 hooks**, CLI golden **IDENTICAL
  (66 files, 14 commands)**.
- `npm test`: **42/42** after the test-only G8 repair; launcher runtime is unchanged.
- `.venv/bin/uv lock --check` and `git diff --check`: passed.

Raw review, failed-first tests, complete logs and image identities remain under
ignored `.superpowers/sdd/2026-11-18-student-workflows/`. The full-suite skips
remain 24 private-fixture cases and one system-Chrome case; they are not waived
acceptance. The entire original plan and its ledger remain open. Active companion
attribution/schemas, exact isolated-profile proposal, real reviewer provenance and
blind recall must be settled before specifying the production integrations.
Further audit repair, protected derived cleanup, full onboarding and end-to-end
acceptance remain outstanding. Successful local caller-receipt recovery does not
prove interrupted collection-write recovery or normal-user readiness.

Final container verification: Compose validation, image build and non-root,
read-only, network-disabled real OCR/Chromium smoke passed at
`510c1e4-dirty`. The dirty marker records the then-uncommitted audit/checkpoint
documents; runtime source is commit `510c1e4`. Image inspection and complete
build/smoke logs are retained in the same ignored workspace. Pinned-download
retries recovered without changing requirements or isolation. No public service,
profile switch, Anki endpoint or collection operation was introduced.
