# Mac OCR, doctor and Desktop workflow retest

Runtime pin: `51c8e36086f6e3a45a920b9994b94cf214bb895c`, existing
`refactor/student-workflows` branch. A documentation-only descendant supplies
this procedure. Companion remains `9fa37516f9987fba6a295bc4915ccb4952248064`;
no add-on replacement, Anki restart/profile/auth/sync or collection operation is
part of this retest. Known independent reviewer-control gates remain unchanged.

New packet: `.artifacts/mac-acceptance/51c8e36/` relative to the primary checkout.
Original packet `.artifacts/mac-acceptance/6e9bcf3/`, its archive and Mac evidence
are retained unchanged. These exact original diagram/PDF bytes failed on Linux
as reported: zero OCR regions; page2 E21 incorrectly suggesting installation.
This was not established as a Mac-specific defect.

| File | SHA-256 |
| --- | --- |
| `ankiplusmcp-0.3.0-py3-none-any.whl` | `b083db4fd1a25440a2b274a16a9e17eaa7035bf8dfae5dddfc961a49e5eb317a` |
| `ankiplusmcp-51c8e36.tgz` | `30f261cf0d702613154572382fb12b6fd9bd45eee9d2b86c4ff4d1ec9a3c9409` |
| `desktop-project-instructions.md` | `683a3d2730ff6e7b6e32e7cb2d5c8d560e3f6aeae7fea4eafc49f55c7c835337` |
| `linux-exact-input.json` | `b3cd7bdba9bf9b5e840801ee1aabeb93e4d7b0d175fcaf31e2e909065a60097b` |
| `synthetic/diagram.png` | `b40db6c05213978ab0ff7520ebd4298e3f7b13c3d1c1b8cf6b72a2bc27e82999` |
| `synthetic/lecture.pdf` | `d1d8144e262b7b31894667e94184db1a0399c01cb9c899504f8df876b4130bd6` |
| `synthetic/textbook.md` | `9bc03ebeea742ed6265600534cfa81e69eaa0214a05b20d8f65a2c998e0d0281` |

## What changed

A successful OCR operation may recognize no text. Standalone image OCR now
reports `no_text` with zero regions and preserves the imported image. The MCP
PDF path retains page/crop evidence, empty text and an honest status: recognized,
no_text, unavailable, failed or timeout. It does not fabricate a quote. Page/crop
status is available from read_source, source evidence and figure metadata; the
source-linked review also displays OCR status. Legacy CLI extraction still
refuses an empty text page. Its empty-success advice no longer implies missing
Tesseract. Thresholds, resolution, scale and PSM passes remain unchanged.

Missing executables are distinct from OCR process failures/timeouts. Citation
substring/version/page checks and all existing quality/authorization gates remain
required. An image-only reference without a quote is image evidence, never proof
of factual accuracy. Maintainer quality packets still include cited PDF images.

Doctor now verifies Python Playwright import and actual headless browser launch.
Chrome presence alone is insufficient. Rendering is an optional Python extra;
a bare local wheel omits Playwright. Use `[all]` explicitly for this packet.

Desktop connector registration does not install a Claude Code filesystem skill.
The launcher has no supported Desktop skill directory. The workflow is now
available from the installed server as `get_guidance(topic="workflow")`, tested
from the actual packaged wheel. Copy `desktop-project-instructions.md` into an
owner-approved Desktop Project's instructions (or use its bootstrap request in
the conversation). This is manual host setup, not automatic skill installation
or evidence that onboarding/quality-runtime milestones passed. Do not invent a
Desktop skill folder or alter unrelated host settings.

## Narrow ordered Mac retest

1. Preserve the original packet, failed workspaces/logs and Mac evidence. Verify
   Darwin and record exact Node/uv/Python/Playwright/browser/Tesseract versions.
   Copy the new packet separately; run `shasum -a 256 -c SHA256SUMS` there. Every
   file must match. Do not replace fixtures, edit goldens or tune OCR settings.
2. Preview only the new AnkiPlus registration. With owner authorization for the
   AnkiPlus MCP update, use the new local launcher and the wheel's `[all]` extra.
   For paths containing spaces, compute a real file URI:

   ```sh
   PACKET="/absolute/copied/new-packet"
   export ANKIPLUSMCP_NPX_REF="$PACKET/ankiplusmcp-51c8e36.tgz"
   export ANKIPLUSMCP_PY_SPEC="$(node --input-type=module -e 'import {pathToFileURL} from "node:url";console.log("ankiplusmcp[all] @ "+pathToFileURL(process.argv[1]).href)' "$PACKET/ankiplusmcp-0.3.0-py3-none-any.whl")"
   ```

   Use init `--print` / `--dry-run` to inspect the concrete diff before any
   owner-approved change. Preserve unrelated settings and backups; no automatic
   `--force`. Only reload the AnkiPlus MCP host connection if authorized. Do not
   touch the Anki add-on, real profile, companion auth or collection.
3. In a fresh disposable source-only data root/workspaces, allow only the copied
   synthetic source folder. Run doctor using this exact wheel spec. A detected
   Chrome with missing Playwright or a failed driver launch must report the
   optional browser check missing; a usable driver/browser must launch and close
   successfully. Doctor does not install/download anything or prove onboarding
   complete. Record the browser check's detail, not only overall core `ok`.
4. Read `get_guidance(topic="workflow")`; verify it describes durable staging,
   quality, exact approval and reconciliation. Confirm Project instructions are
   actually loaded in the intended Desktop conversation. No collection tools,
   connection milestone or reviewer launch is needed for this source-only retest.
5. Import the unchanged `synthetic/diagram.png` and run OCR at the original
   defaults. Linux observes zero regions with `extraction_status=no_text`.
   Verify the original image remains inspectable. Zero regions must not claim
   Tesseract is missing. Record any real version-dependent recognized output
   honestly; do not add a fabricated label to make a test pass.
6. Import/extract unchanged `synthetic/lecture.pdf`. Expect two retained pages;
   physical1/2 retain printed A-1/B-1. Linux page1 text contains “Fibroblasts make
   collagen.”; page2 completes with empty text and `no_text`. Get/inspect page2
   using get_page_image/get_image. It must not fail E21 with installation advice.
   If actual OCR recognizes text on this Mac, status/quote must reflect only that
   retained recognized text. Empty text cannot validate “Nucleus” or any invented
   quotation. A page2 image reference without a quote remains possible.
7. Verify the real page1 quotation resolves exactly, an invented page2 quotation
   fails, and image evidence never waives independent quality or exact approval.
   Missing Tesseract / failed process / timeout are covered by deterministic Linux
   regressions; do not uninstall/change Mac tools to simulate them. If naturally
   encountered, record the distinct error/status and inspect retained evidence.
8. Save source hashes, read_source/evidence/status output, job errors, doctor
   report, workflow/Project setup observations and image captures alongside the
   original evidence. Stop on hash mismatch, inaccessible evidence, fabricated
   quote acceptance, misleading dependency success, unexpected collection call
   or any attempt to bypass quality. Do not retry writes: none are authorized.

This retest makes no claim that actual prescribed reviewers/cumulative controls,
Mac embedding/lifecycle or private card-quality acceptance have passed. Do not
repeat the blocked reviewer-control experiment or substitute an alias/API.

## Linux evidence

- Failed-first six initial cases reproduced; additional workflow and strict
  legacy empty-page regressions also failed before repair. Final focus24passed.
- Full public suite827passed/25existing skips. check-mcp594passed/1existing skip;
  frozen12/12, hooks42/42, CLI golden66artifacts/14commands IDENTICAL.
- Launcher44/44. No source fixture, golden or frozen file changed.
- Actual original image/PDF bytes reproduced failure in the old6e9bcf3 image.
  New51c8e36 nonroot/read-only/network-none/no-mount/resource-limited image
  preserves page2 PNG and no_text, rejects an invented quotation, accepts the
  exact page1 quote, launches the actual Playwright browser and reads the packaged
  Desktop workflow. The shipping wheel is also installed offline into tmpfs and
  tested against the same bytes; `[all]` dependency resolution is checked offline.
- Raw evidence: primary `.artifacts/mac-findings/` (red/green/full/check/launcher,
  original-exact, container-exact, shipping-wheel-exact, build/identity and exit
  logs). No real Mac configuration/add-on/profile/collection was accessed.

Reproduce the exact shipping-wheel source-only container check with the included
JSON payload and inspected hardened limits, using image ankiplusmcp:51c8e36:

```sh
docker run --rm -i --pull never --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1.5 --memory 1536m \
  --pids-limit 128 --tmpfs /tmp:rw,nosuid,size=384m,uid=1000,gid=1000 \
  --entrypoint python ankiplusmcp:51c8e36 \
  -c 'import json,sys;payload=json.load(sys.stdin);exec(payload["script"])' \
  < linux-exact-input.json
```
