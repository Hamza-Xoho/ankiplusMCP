> Runtime follow-up: use [macos-ocr-retest.md](macos-ocr-retest.md) for the
> repaired51c8e36 packet and narrow source-only retest, including Desktop workflow
> setup and required local-wheel extras. The6e9bcf3 packet below is preserved
> historical evidence; do not use its bare-wheel override for the new retest.

# Revision-pinned Mac acceptance packet

Status: **Linux/T3 implementation and local acceptance complete.** This packet
prepares real Mac testing. It is not a release, deployment, Mac compatibility
pass, prescribed reviewer pass or authorization for real collection operations.

## Exact implementation and artifacts

Primary branch `refactor/student-workflows`: `6e9bcf3bfbb6d2c8ec42d484046ebef9fd774a0b`.
Companion branch `local/collection-identity`: `9fa37516f9987fba6a295bc4915ccb4952248064`.
A later documentation-only primary commit may contain this packet; these exact
revisions identify all runtime source being accepted. Do not use the older
AnkiPlus checkout, historical v0.3.0 registry/Git tag or candidate7523cd0 archives.

Local packet directory:
`.artifacts/mac-acceptance/6e9bcf3/` relative to the primary checkout.
It contains the following actual files, `manifest.json` and `SHA256SUMS`. Transfer
this directory through an owner-approved channel; no publication is required.
No credentials, real collections, private documents or verifier keys are included.
The packet also includes the current handoff documents; their checksums are in
SHA256SUMS alongside the artifacts.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `anki-mcp-server-addon-9fa3751.ankiaddon` | 2730581 | `fb5f44aa91b67aa8f72e060577cff265f7cdba2f8d23bea105024f4019c357c9` |
| `ankiplusmcp-0.3.0-py3-none-any.whl` | 367064 | `a87d15f05bf6bd4d9074a34bd56eda511153a3232f37577c36b9b6c32e5c48da` |
| `ankiplusmcp-6e9bcf3.tgz` | 19763 | `30f261cf0d702613154572382fb12b6fd9bd45eee9d2b86c4ff4d1ec9a3c9409` |
| `linux-main-smoke.py` | 1808 | `b11481440402fdd2852a466f44e1c5edca09ca23b3c562b51960c10483bc0615` |
| `synthetic/diagram.png` | 5044 | `b40db6c05213978ab0ff7520ebd4298e3f7b13c3d1c1b8cf6b72a2bc27e82999` |
| `synthetic/lecture.pdf` | 652502 | `d1d8144e262b7b31894667e94184db1a0399c01cb9c899504f8df876b4130bd6` |
| `synthetic/textbook.md` | 126 | `9bc03ebeea742ed6265600534cfa81e69eaa0214a05b20d8f65a2c998e0d0281` |

The wheel contains the actual connected primary product and bundled review App;
the launcher tarball contains the matching installed workflow skill. Exact source
bytes were compared against the archives. Version metadata remains0.3.0 because
this is an unpublished branch, so filenames alone are not sufficient identity.
Companion dependencies are packaged by its Python3.13 build; primary dependencies
and ext-apps2.0.4 are locked. Native OS/Anki runtime dependencies are recorded in
Linux evidence; their versions do not establish Mac compatibility.

## Prerequisites and authorizations

Record macOS/architecture, exact Claude Desktop/Code and Pro mode, Node/uv/Python,
Anki/Qt, existing add-on revision/name/transport, and actual profile/path before
acceptance. Preserve the working installed add-on, unrelated host configuration,
confirmed preferences, personal guide notes and retained evidence. Do not sync.

This Linux task grants no permission to install/replace the Mac add-on, restart
Anki, switch profiles, change authentication, read real collections or write/sync/
delete data. Each dependent Mac step below needs the owner's explicit bounded
authorization first. Prefer a newly authorized disposable synthetic profile;
never silently substitute a real profile. No automatic destructive rollback.

Choose an absolute persistent acceptance data directory and a dedicated synthetic
source directory; keep both outside installed source. Retain them after testing.
The packet supplies a two-page lecture PDF (physical1/2, printedA-1/B-1; page2 is
image evidence), two text chapters and a synthetic nucleus diagram. No private
fixture is implied by these files.

## Ordered acceptance

1. **Identity and integrity, no collection access.** On the Mac, verify Darwin,
   both exact source revisions if using checkouts, and all transferred archive
   hashes. From the copied packet directory run `shasum -a 256 -c SHA256SUMS`.
   Expected: all listed files match. Stop on any mismatch. Record paths/versions;
   do not rebuild an archive and keep its old recorded hash.

2. **Pinned registration preview.** With Node/uv available, extract the launcher
   into a disposable directory. Use the local tarball AND wheel overrides. The
   historical default launcher reference would start the wrong product.

   ```sh
   PACKET="/absolute/copied/packet"
   DATA="/absolute/chosen/AnkiPlus-acceptance-data"
   SOURCE="$PACKET/synthetic"
   LAUNCHER_TMP="$(mktemp -d)"
   tar -xzf "$PACKET/ankiplusmcp-6e9bcf3.tgz" -C "$LAUNCHER_TMP"
   export ANKIPLUSMCP_NPX_REF="$PACKET/ankiplusmcp-6e9bcf3.tgz"
   export ANKIPLUSMCP_PY_SPEC="$PACKET/ankiplusmcp-0.3.0-py3-none-any.whl"
   node "$LAUNCHER_TMP/package/launcher/cli.mjs" init \
     --host claude-desktop --workspace-root "$DATA" --source-root "$SOURCE" --print
   ```

   Expected: only the AnkiPlus entry/skill is proposed; absolute local tarball,
   wheel and resolved uv dependency persist across host restart. `--print` writes
   no registration. Run `--dry-run --no-warmup` for the concrete configuration diff
   if authorized to inspect that host config. Only after explicit authorization,
   apply that reviewed registration; do not add `--force` to bypass an unexplained
   conflict. Retain backups/install manifest and compare unrelated settings.
   Host restart, add-on installation and auth changes remain separately gated.

3. **Source-only resumable setup.** Open the installed skill and call
   `get_student_setup`. Use `propose_student_setup` to choose custom lecture/text
   materials, the actual data folder, readable source folder `$SOURCE`, Basic for the initial synthetic model,
   review enabled, uncertainty pending, and initially no premade deck. Inspect the
   human-readable diff and explicitly `confirm_preferences`. Resume after a
   normal host interruption. Expected: choices/guide personal notes survive;
   storage/guide are verified and missing connection/App/quality checks remain
   visible. Caller booleans cannot complete setup. Ask the guide for its exact
   `Start here — AnkiPlus` path and verify all seven sections. A nontechnical user
   should locate the guide/history and describe the next action without coaching.

4. **Source evidence and draft mechanics, no collection write.** Import the
   supplied lecture and textbook into separate source workspaces; extract only
   selected pages/chapters, inspect text and the original page image/crop, and
   create source-linked basic/cloze/native-IO drafts using unchanged guidance.
   Expected: physical page1 differs from printedA-1; image-only page2 is labelled
   as such/OCR where applicable, no invented quotation, sources stay unchanged.
   Different chapter selections/reruns have distinct run IDs. A revised source
   version does not reuse stale extraction. Missing OCR/browser/permissions get
   specific diagnoses and resumable jobs, not a false completed milestone.

5. **Authorized companion connection/read-only collection checks.** Only after
   explicit profile/add-on/collection-read authorization, confirm the intended
   profile/path and configure the existing loopback MCP endpoint using the
   launcher's `--companion-url`, `--anki-profile`, `--anki-collection-path` and,
   if needed, `--companion-token-file`. Use the actual privately provided endpoint
   and private token file; never inline or log credentials. Review the concrete
   registration diff before changing it. No public endpoint is needed. Verify
   `get_collection_choices` and `advance_student_setup` connection check against
   actual model fields/templates/styles and complete collection identity/session.
   Missing capabilities, auth failures, wrong/partial identity must refuse.
   Confirm selected own/premade decks explicitly; no premade deck remains valid.

6. **Coverage, durable proposals and production App.** Start a run, record
   approved-scope coverage and stage it. Keep complete queries/hits/decisions and
   source refs in history. Use actual existing synthetic note/card IDs, never
   infer one from the other (their numeric values can coincide). Verify active
   coverage unchanged, selected suspended-card reuse, create, explicit update and
   pending dispositions. A semantic hit alone is not verified conceptual coverage.
   Open `open_run_review` through the installed Desktop App resource. Exercise
   keep/exclude/edit-new/choose-existing/defer/explicit-update, source quotes and
   cited PDF image, complete long-field loading, keyboard labels/focus, narrow
   layout, light/dark, reconnect and two stale tabs. Expected: run identity visible;
   unsaved edits block approval/paging/recheck and destructive note switching;
   saved selections survive reconnect; forged/expired/wrong-run sessions refuse.
   Existing text editing defaults to a new draft; explicit update explains sibling
   cards and requires confirmation. Excluded invalid drafts do not block unrelated
   work; selected technical blockers still prevent authorization.

7. **Local enforcement and actual App evidence.** Missing/failed/stale quality
   evidence cannot authorize. Edits to fields/actions/targets/source/media/relevant
   configuration invalidate approval and affected quality. Delayed old reviewer
   results refuse. Saved preferences show a diff/confirmation; run-only changes do
   not become future defaults. Revoke a source folder and restart the same persisted
   command: it remains revoked. Stage contradictions, shorten/change valid citations,
   and rerun: they remain pending until explicit resolution. Capture actual App
   initialize/tool/readback/reconnect observations with exact installed resource
   hash and session-token hash; the trusted operator imports that real export with
   `verify-host-evidence --kind interactive-review`. Do not fabricate observations.

8. **Known prescribed-reviewer gate: stop dependent work here.** The observed Mac
   host lacks supported launch-level cumulative turn/tool controls; same-reviewer
   continuation under six cumulative student turns remains unproven. A new alias
   alone does not solve it. Do not repeat the exploratory host-control check or
   launch a reviewer to discover controls. Retain the existing observed evidence.
   Expected in this host state: quality-runtime onboarding stays incomplete;
   authorization/application cannot be obtained by clicking approval or importing
   a PASS assertion. This is a genuine external acceptance gate, not missing local
   implementation. No Linux author review, weaker blind recall or paid API substitute.

9. **Only when actual host support is independently established and authorized.**
   Execute the unchanged prescribed maintainer (Sonnet5.5/high, max14 cumulative
   turns) and independent student (Sonnet5.5/medium, max6 cumulative turns) with
   isolated author context and the exact per-role tool allowlists in the issued
   packet. Use `prepare_run_quality` for both roles. Student reads fronts once,
   commits every tile answer/don't-know through `release_review_backs`, then reads
   released backs once in the SAME reviewer continuation and TOTAL six-turn
   budget. Capture actual launch controls, agent identities, ordered reads/hashes,
   turns and report. Operator `verify-host-evidence --kind quality --run-id ...
   --content-digest ... --observed-execution ...` attests only real observed export.
   The importer cannot supply absent controls. Never copy signed Linux synthetic
   receipts or test keys into acceptance. Failed findings require affected edits,
   re-stage and fresh reviews. Onboarding completes only with all genuinely
   verified preferences/storage/connection/App/quality-runtime/guide checks.

10. **Bounded application, separately authorized.** After genuine quality and
    exact user authorization, operate only on the explicitly named fresh synthetic
    profile: at most5 created notes,20 generated cards and2MiB supplied PNG media
    across this acceptance. Existing-note updates/unsuspension must name synthetic
    targets in the reviewed proposal. No sync/deletion/auth changes. Check create,
    canonical mixed Basic/native IO, full-field explicit update, exact media bytes,
    tier3 generated-card suspension, and reuse unsuspension. Already-target states
    are unchanged; mixed selections count only actually changed card IDs. Expected:
    durable intent before every send, exact conditional request/state, durable ack,
    independent field/model/tag/deck/media/suspension readback and separate per-item
    confirmed/unchanged/failed/conflict/uncertain outcomes. Existing tags/tier
    behavior remain preserved. User approval and saved automatic configuration
    authorization are distinct events; automatic mode never skips quality.

11. **Repeat, partial failure and restart.** Under explicit synthetic fault-test
    authorization, repeat source/overlapping topics and observe verified mapping
    reuse. Change a target/profile/session during review and expect conflict, no
    silent overwrite. Offline Anki leaves a resumable run. Interrupt after known
    acceptance before result: restart and `reconcile_run` read-only by known IDs.
    An unknown create ack stays uncertain and blocks blind new creates; do not
    resend it or retry the whole batch. Keep confirmed portions and uncertainty
    separately. Inconclusive evidence is a stop, not permission to manufacture
    success. Never destructive rollback or cleanup of retained records.

12. **History, private quality and final acceptance.** Inspect cumulative run
    results and permanent history from MCP and the independent history CLI, with
    bounded pages and full exact record slices. Search by source/run/note/card/
    status; retained exports must not overwrite existing files. Exercise only
    explicit preview+digest-confirmed derived cleanup; protected source/media/
    reviews/quality/history remain. With the owner, run the unchanged representative
    private selection/combination/tier/source-fidelity/visual evaluations and
    actual production note types. The25 existing public-mode skips are not waived.
    Record novice onboarding and actual host lifecycle results. Real support or
    release approval requires resolving these gates; this packet itself is not
    that approval. Windows and other hosts need their own acceptance.

## Stop conditions and evidence

Stop dependent operations on wrong profile/path/session, auth changes, unsupported
capabilities/model/filter/CSS resources/IO variants, missing source/media,
stale/forged review or quality evidence, failed quality findings, a packet/image
limit, unexpected readback, any uncertain send or out-of-envelope target. Narrow
or repair a refused selection, never silently omit it. Do not bypass shell/hooks
or substitute a different tool to defeat a rejection.

Record exact source/archive hashes, host/runtime/dependency versions and commands,
source hashes/pages/labels/origins, actual scoped queries/hits, run/proposal/config/
quality digests, original ordered reviewer exports, source-linked App captures,
explicit authorizations, durable intent/acks and per-item note/card/media/state
readback, restart/reconciliation evidence and final stop reason. Keep raw/private
exports locally ignored; commit only sanitized assessments. Preserve the existing
Linux ledgers, ignored evidence, Mac artifacts and working installed add-on.

## Linux verification and handoff

Final immutable runtime source is6e9bcf3 (full pin above), companion9fa3751.
All final checks/builds started from the clean committed source. Runtime files
remained unchanged until checks and both installed acceptances completed. Final
handoff edits are documentation-only descendants; the wheel/image source pin
remains the exact runtime revision above.

| Verification | Result | Preserved raw evidence, relative to its repository |
| --- | --- | --- |
| Full primary public mode (`CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q tests/mcp tests/unit tests/contract`) |818passed,25existing skips;395.45s | primary `.artifacts/6e9bcf3-public-suite.log` |
| `CARDS_PUBLIC_CI=1 ./scripts/check-mcp.sh` |585passed,1existing skip;292.17s; all later checks passed | primary `.artifacts/6e9bcf3-check-mcp.log` |
| Frozen hashes/hooks/CLI golden |12/12,42/42;66artifacts/14commands IDENTICAL | same check-mcp log; no golden/frozen changes |
| Launcher `npm test` |44/44 | primary `.artifacts/6e9bcf3-launcher.log` |
| Lock/version/privacy/whitespace | passed; uv resolved55locked packages | check-mcp plus final handoff checks |
| Reviewer templates |8source templates unchanged from b0f4233; available frozen copies identical | `.artifacts/cb65c0c-template-consistency.json`; unchanged in6e9bcf3 |
| Companion `.venv/bin/python -m pytest -q tests/unit` |891passed,0skips after final companion code | companion `.artifacts/student-production/material-fix-final-unit.log` |
| Final material regressions |19passed; related coverage/coordinator/concurrency32passed after deterministic RED | primary `.artifacts/final-complete-bounds-focus.log`, `.artifacts/coverage-contention-{red,green}.log`; all included in final full checks |
| Standard Docker image build and hardened smoke | passed; nonroot uid1000, actual OCR1region/render1sheet | primary `.artifacts/6e9bcf3-main-{build,smoke}.log`, smoke exit0 |
| Installed primary+actual Anki/aqt26.9.2, textual `addon` | passed;9intent-before-send assertions,2mixed Basic/nativeIO notes, actual media/update/unsuspend, unknown-ack restart with no resend, OCR1region | `.artifacts/6e9bcf3-acceptance-textual.log`, exit0 |
| Same installed path, numeric `124672614` | passed; same assertions and outcomes | `.artifacts/6e9bcf3-acceptance-numeric.log`, exit0 |
| Installed source identity | both images' quality/coverage/coordinator/App hashes exactly match committed source | `.artifacts/6e9bcf3-{main,isolated}-source-hashes.json` |
| Actual SDK UI/accessibility | source-linked edits/apply/reconnect/stale refusal/dirty protection, responsive/light/dark/focus/contrast tests pass in final suite | `tests/mcp/test_review_app.py`, source-image/session/protocol suites; `.artifacts/review-ui/` captures |

These reviewer/host acceptance fixtures are explicitly signed **synthetic**
fixtures. Their passing enforcement does not constitute actual independent card
quality, real Mac host support or private-fixture acceptance. The25existing skips
are retained, not waived. No release/platform claim is inferred from test counts.

Final images (no publication):

- `ankiplusmcp:6e9bcf3` = `sha256:3d608177de09a4077c1158282c41c5b8efa38ea85d1850b7315f541983d719f4`.
- `ankiplus-student-isolated:6e9bcf3` = `sha256:4f76f1f26e0c7d0d50148dfa361b0796a62af2102abec683005f3a156d3ae2b7`.

Labels identify6e9bcf3 and companion9fa3751. Image metadata, installed dependency
freezes and rendered Compose are retained in `.artifacts/6e9bcf3-images.jsonl`,
`6e9bcf3-{main,isolated}-pip-freeze.txt` and `6e9bcf3-*-compose*.json`.
The standard Compose was **build only**. Its smoke used direct `docker run` with
no mounts/network/ports, nonroot/read-only/cap-drop/no-new-privileges and
1.5CPU/1536MiB/128PIDs. Combined acceptance used the inspected standalone
`tests/isolated/compose.yaml`: no mounts/network/ports, nonroot/read-only,
1.5CPU/2048MiB/192PIDs. No real Anki data, home directories, credentials or Mac configuration was
mounted, no real companion contacted, and no unrelated service/data was changed.

Reproduce the combined lane from the pinned checkouts using the explicit packaged
archive input described in `tests/isolated/README.md`, then inspect rendered
Compose before running:

```sh
ANKIPLUS_REVISION=6e9bcf3 COMPANION_REVISION=9fa3751 \
  docker compose -f tests/isolated/compose.yaml config --format json
ANKIPLUS_REVISION=6e9bcf3 COMPANION_REVISION=9fa3751 \
  docker compose -f tests/isolated/compose.yaml build
ANKIPLUS_REVISION=6e9bcf3 COMPANION_REVISION=9fa3751 \
  docker compose -f tests/isolated/compose.yaml run --pull never --rm --no-deps acceptance
ANKIPLUS_REVISION=6e9bcf3 COMPANION_REVISION=9fa3751 \
  docker compose -f tests/isolated/compose.yaml run --pull never --rm --no-deps \
    acceptance python /artifact/product_workflow.py 124672614
```

Implementation commits preserved on the existing primary branch:
9bcc213 (durable proposals/authorization/application), e6c4c4d (production App and
verified setup), d13cd5b (coverage/quality/recovery hardening), e4bd907 (connected
acceptance/audit repair),7523cd0 (cited source/approval),0fef80e (material review
fixes),121e219 (strict template metadata/trace),fc46cca (native phone containment),
deb837e (public path privacy),cb65c0c (complete embedded/mask bounds),6e9bcf3
(coverage retry race). Companionacdff93 binds media bytes;9fa3751 refuses CSS
resource dependencies. No prior commit/evidence/ledger was removed.

The single final fresh whole-branch engineering review covered the completed
product at7523cd0/acdff93, found8material defects and was followed by one root-only
RED/GREEN material fix pass, including the regression repairs above. No second
engineering review was run. Separate impeccable UI finish review found3issues;
all were fixed and scored resolved by the same UI reviewer. It is not prescribed
Anki quality acceptance. Reports and declined-to-judge rulings are preserved in
[final-production-review.md](final-production-review.md) and the existing
`.superpowers/sdd/2026-11-19-production-integration/` ledger/evidence. Intermediate
source/dirty builds remain diagnostics; only the final pins above describe this
packet. Original student/compatibility ledgers and Mac evidence are retained.

After the documentation-only handoff commit, fast-forward push/verify the two
existing branches. No force push, history rewrite, merge, PR, package publication
or deployment. The preserved ledger records the actual final remote-head check;
operators should also compare `git rev-parse HEAD` / `git ls-remote` and verify
that any primary descendant of the runtime pin changes handoff documents only.

There is no remaining independently executable T3 subsystem assigned to a Mac
blocker. Remaining gates are precisely steps8–12's real host cumulative reviewer
controls/execution, Mac embedding/lifecycle/HTTP/Qt, private/production note-type
and representative source-quality evaluation, novice acceptance and explicitly
authorized synthetic collection operations. Windows/alternative-host acceptance
and publishing/deployment remain outside this handoff.

Implementation trace: [original requirement matrix](t3-requirement-evidence.md),
[audit dispositions](audit-closure.md), [final review/fix pass](final-production-review.md),
[connected workflow](student-workflow.md). Historical checkpoint/Mac action docs
remain evidence and are superseded by this packet's ordered steps.
