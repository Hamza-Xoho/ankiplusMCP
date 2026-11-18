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

- Full suite in the repository's existing public-CI mode: **517 passed, 25 skipped**.
- Full local contract mode: **261 passed, 1 failed, 23 errors**, with all 24 affected cases requiring unpublished private lecture/transcript fixtures. These are not waived release checks.
- Launcher: **28 passed**.
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

The new run/configuration libraries are not yet connected to the full user workflow. Source-quote review, existing-coverage decisions, the companion coordinator, exact user approval, interactive review, onboarding/guide and several audit repairs remain outstanding.

The approved design requires proving the actual local Desktop UI + independent maintainer/student reviewers + Anki companion combination before freezing transport/UI implementation. No real Mac/Desktop session or isolated live Anki is available here. Public documentation suggests routes to investigate, but it cannot establish that the complete combination meets the Pro subscription and quality-preservation constraints. See `compatibility.md` for the actual test procedure.

The container's mechanical-only `network_mode: none` is retained. A future companion connection needs its own explicitly tested execution topology; this checkpoint does not weaken the current container isolation as a workaround.

## Local commits

- `00aa08c`: reproducible CLI regression checks.
- `a780dee`: durable run history and explicit preferences.
- `d0250f8`: artifact revision isolation and cumulative receipt preservation.

Container and documentation checkpoints follow these commits. No commit has been pushed.
