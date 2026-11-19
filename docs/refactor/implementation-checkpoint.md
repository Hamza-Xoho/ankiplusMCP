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

## Evidence intake after f795b56

The owner supplied seven Mac artifacts. Four original checksums, nine repository
originals and two reviewer bodies match locally; raw transcripts/live handshake
are not attached. Received bytes and audit receipt are retained only in ignored
`.artifacts/compatibility-received/20261119/`. No runtime code, public schema,
frozen file, card-quality instruction or original artifact was modified.

The [new assessment](macos-evidence-assessment.md) advances reviewer provenance and
stock-Cloze A–D evidence with explicit limits. The
[follow-up plan](../superpowers/plans/2026-11-19-compatibility-follow-up.md) prepares
read-only metadata completion, an approval-gated disposable staged-image protocol,
local fault tests and an explicitly blocked live recovery envelope. Profile path
alone, filename-only media readback and reconstructed schemas do not establish
required production guarantees. No collection authorization is requested around
unknown identity or transport operations.

Checks in this intake are evidence JSON/hash/source-template validation, link and
whitespace checks, and privacy checks. Historical runtime results remain 634/25
(public-CI tests/skips), 401/1 (MCP tests/skip), 42 launcher tests and the recorded
hardened container smoke at 510c1e4-dirty. Runtime/container suites were not rerun
for documentation-only changes; no fresh behavioral success is claimed.

## Native integration continuation after aab80b8

New primary code connects an explicit opt-in local MCP companion adapter to
`search_collection_coverage`, with bounded complete search, full note reads,
actual card ownership and suspension state. Missing capabilities, excerpts,
foreign/missing records, changed sessions and inconsistent fields/siblings refuse
results. The native transport requires explicit endpoint/profile/path; it does
not discover, launch or reconfigure Anki. The default and container remain
unconnected. Existing public tool contracts are preserved; new tools are additive.

`get_student_setup`, `propose_preferences`, `confirm_preferences` connect versioned
preferences and guide generation to MCP. Confirmation is explicit and repeatable;
notes survive guide regeneration. Setup remains incomplete rather than claiming
that saving preferences verifies UI/quality/collection capabilities.

The companion branch now provides fixed conditional student operation state and
dispatch. It checks complete profile/session/request/target state synchronously in
one main-thread request, without arbitrary tool forwarding. Full-card backend
serialization binds scheduling state. Creation uses actual Anki26.9.2 fields_check;
media requires exact returned filename and exact byte readback. Renaming or lost
verification is uncertain. Conditional suspension is not implemented. These
capabilities are not installed on the Mac or authorized for real collections.

One fresh engineering review of the whole branches and new implementation found
four Important defects: incomplete scheduling state, mixed note/card coverage
snapshots, unverified renamed media, and transport lifecycle exception leakage.
All four were reproduced RED and fixed in one pass. No second review or product
quality reviewer substitution occurred. The ignored follow-up ledger contains the
report, original failures, final logs and rulings.

Fresh verification: full primary public-mode **664 passed, 25 existing skips**
(baseline644/25); check-mcp **431 passed, one existing skip** (baseline411/1),
frozen12/hooks42/wheel/version/privacy and unchanged66-file14-command CLI golden.
Launcher42/42 and lockfile/whitespace checks pass. Companion **880 passed, no
skips** (baseline867), with packaged Linux Anki/aqt26.9.2 memory-stream checks
passing textual and numeric add-on package names. No HTTP authentication/Qt/Mac
acceptance is inferred. Container outcome is appended after completion below.

This does **not** fulfill the requested full remaining product. The production
coordinator, digest-bound staging/authorization, durable intent-before-send,
per-item application/readback, uncertain-write reconciliation, production
source-linked interactive review, complete verified onboarding and remaining
audit/acceptance work are still required. The adapter is not an authorization
system, and retrieved coverage is not proof of semantic completeness. No apply
workflow is advertised. Source-derived boundary tests do not close real host or
private quality gates. No weaker blind-recall gate was adopted. The known Mac
host limitation remains precise; another repetitive reviewer launch/control check
is unnecessary. Independent implementation remains the implementer's work, not an
external action requested from the owner.

Post-fix primary Compose validation/build and no-network/no-host-mount smoke
passed for image `5841347-dirty` (source changes now committed as `2b00ddf`):
non-root/read-only/cap-drop/no-new-privileges/resource limits, real OCR/Chromium,
history migration/search and explicit preference/guide integration. The dirty
label accurately records the uncommitted fixes at build start. No real companion,
collection, registration or public endpoint was touched. Raw image identity and
logs remain in the ignored follow-up workspace. Companion commits bc0d15d,
4d15b1f and 7f051c6 are pushed to the authorized existing branch.

## 2026-11-19 guarded adapter continuation

Code revisions: primary `81615af77686d0b7ee5b9fa102e6cb2ab580fa2b`, companion
`0fa5075612f54f65ca9c59d6b6a7c689f6578a07`. Conditional suspension and full-field
updates now share the synchronous exact-state guard. The primary exposes fixed
adapter write methods, validates note-type/template/style metadata, retains batch
acknowledgements and stops on missing/invalid create identities. Final Linux public
suite:677passed/25existing skips; check-mcp444passed/1existing skip; companion882passed.
One fresh engineering review found the malformed-create acknowledgement defect;
six RED→GREEN regressions and the full suite verify its repair. No product-quality
review pass is implied.

The requested full student product remains incomplete. Coordinator authorization,
quality-bound proposals, durable intent/application/readback/reconciliation,
production interactive review, verified resumable onboarding and remaining audit
closure are unfinished T3 scope. They are not Mac/private-environment blockers.
See [current acceptance status](macos-acceptance.md), which explicitly records
that the product is not ready for Mac acceptance. All previous ledgers and ignored
evidence remain retained. No Mac installation, collection operation, deployment,
publication or PR was performed.
