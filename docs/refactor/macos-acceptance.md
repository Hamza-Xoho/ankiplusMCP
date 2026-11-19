# Mac acceptance status and bounded packet

Status: **not ready for Mac acceptance**. This continuation does not satisfy the
requested Ready For Mac Testing criterion. Independent T3 implementation remains;
this is not a Mac/private-environment blocker. Do not install this branch over the
working Mac add-on or start collection operations from this document.

## Pinned code under review

- Primary: `81615af77686d0b7ee5b9fa102e6cb2ab580fa2b`, branch
  `refactor/student-workflows`.
- Companion: `0fa5075612f54f65ca9c59d6b6a7c689f6578a07`, branch
  `local/collection-identity`.
- This document may receive a documentation-only follow-up commit; code revisions
  above identify the implementation being tested, not a claim of release readiness.

## Remaining T3 work before real Mac product acceptance

1. Connect approved-scope collection coverage and prior verified mappings to runs
   and immutable proposals. Reconcile earlier uncertain writes first.
2. Implement stage/authorize/apply/reconcile with exact quality/config/source/media
   digests, durable per-item intent, actual readback and cumulative outcomes.
3. Connect source-linked production review to the proven SDK bridge packaging;
   bind session/run/workspace/revision, reject stale decisions and late reviews,
   preserve selections, and verify responsive accessibility.
4. Connect resumable onboarding to verified health milestones, preferences and
   launcher registration. A generated guide is not completed onboarding.
5. Close remaining original audit dispositions against the connected product and
   run the full local end-to-end acceptance scenarios.

Adapter writes are low-level conditional primitives. They do not establish user
approval, quality authorization, collection uniqueness or a distributed transaction.
No current MCP product tool exposes these new write methods as approved application.

## Permitted Linux verification

Use disposable synthetic inputs only. Primary commands:

```sh
CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract
./scripts/check-mcp.sh
npm test
.venv/bin/uv lock --check
```

Companion: `.venv/bin/python -m pytest -q tests/unit`, then the inspected standalone
`tests/isolated/compose.yaml` procedure in its README. Do not use upstream make
E2E targets or overrides. Its runtime has no network, host mounts or published
ports, runs non-root/read-only/cap-drop/resource-limited, and creates only temporary
synthetic collections. Both textual and numeric add-on names must pass.

Raw primary evidence: ignored `.superpowers/sdd/2026-11-19-production-integration/`.
Companion evidence: ignored `.artifacts/student-production/`. Earlier evidence and
ledgers remain intact. No Linux synthetic evidence establishes Mac HTTP/Qt behavior.

## Subsequent real Mac acceptance prerequisites

After the T3 requirements above pass, replace this status packet with a complete
revision-pinned executable product packet. Record OS, Desktop/Code, companion,
Python, OCR/browser and actual reviewer runtime versions. Use a disposable profile
only under separate explicit authorization. Installation/replacement, Anki restart,
profile changes, authentication changes, sync and collection cleanup are not
currently authorized. Retained data must remain untouched.

Ordered required scenarios, all currently **not run on this new product**:

1. Clean novice installation/resume, preserving unrelated host settings and saved
   choices; verify required health checks and all seven tailored guide sections.
2. Lecture, selected textbook chapter and custom source; no-premade and existing
   overlapping deck setups; inspect exact physical-page/OCR evidence and coverage.
3. Review keep/exclude/edit-new/choose-existing/defer/explicit-update; verify stale
   sessions, edits and relevant preference changes invalidate approval/quality.
4. Explicitly authorized bounded synthetic create/media/update/suspend/unsuspend;
   record actual note and card IDs, exact fields/media bytes and queue readback.
5. Repeat/overlap, contradictions, automatic pending policy, offlining, profile
   changes, process death after send, restart and per-item reconciliation; require
   no blind create resend, no batch replay and inspectable permanent history.
6. Prescribed independent source/card quality and visual reviews, representative
   private fixtures, novice acceptance and preserved house style/tiering/tags.

Stop on any profile/source/revision mismatch, unsupported capability, missing or
stale quality evidence, uncertain external write, or proposed operation outside
the explicitly authorized operation list. Preserve evidence; never manufacture
success or use destructive rollback to make the result look clean.

The staged reviewer gate remains blocked by unsupported launch-level cumulative
turn/tool controls and unproven same-reviewer continuation within six total turns.
Do not repeat host-control probes or exploratory reviewer launches, create another
alias as a purported solution, substitute weaker recall, or buy a separate API.
This gate does not excuse any unfinished independent T3 work above.


## Verified results for this continuation

- Primary commits: `8fe8c34` explicit adapter writes/model validation;
  `81615af` malformed-create acknowledgement repair.
- Companion commit: `0fa5075` conditional suspension/full-field updates.
- Primary final public-mode suite: **677 passed, 25 existing skips**.
- Final check-mcp: **444 passed, one existing skip**; frozen hashes **12/12**,
  hooks **42/42**, version/privacy/wheel checks pass and CLI golden remains
  **identical, 66 artifacts/14 commands**.
- Launcher **42/42**; lockfile and whitespace checks pass.
- Companion **882 passed, no skips**. Packaged Linux Anki26.9.2 memory-stream
  synthetic checks pass for textual/numeric package names, including conditional
  suspension, complete update, changed-state refusal and duplicate-create refusal.
- One fresh engineering reviewer independently passed **37 primary/57 companion**
  focused tests, found one new Important defect and no Critical/Minor. Six
  malformed-create cases reproduced it RED, then passed GREEN; the final full
  suite above includes the fix. No second review or product-quality pass claimed.
- Initial clean `8fe8c34` rootless image build and no-network/no-mount/nonroot/
  read-only/cap-drop/resource-limited OCR/Chromium/history/preferences/guide smoke
  passed. Its image excludes the later acknowledgement fix; final rebuild evidence
  is recorded separately when available. An early run attempted before image
  availability failed without starting a container; the successful run used
  `--pull never`. Both logs are retained; no real companion was contacted.

The companion image label `7f051c6-dirty` accurately records build-start source
subsequently committed as `0fa5075`; archive checksum and rendered configuration
are retained in `.artifacts/student-production/`.

Rulings: add only fixed guarded suspension to meet the original contract (cost:
one additional primitive); preserve all ledgers and label this packet not ready
(cost: no completed acceptance-packet claim); leave Mac/private execution
unaccepted (cost: no platform/quality pass). No deferred Minor review findings.
