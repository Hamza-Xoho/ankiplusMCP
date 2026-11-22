# AnkiPlus MCP verification

## Documentation organisation: 2026-11-22

Moved 24 documents into legacy usage and development-record directories while
keeping maintained public guides at `docs/`. Added audience indexes and updated
active links, contributor pointers and phase prompts. Four original specification
paths remain compatibility symlinks to byte-identical targets for frozen tooling.
The privacy checker's existing plan exemption follows that plan's new path.

`./scripts/check.sh` passed: 28 launcher tests, 250 Python tests, one system-Chrome
skip, frozen checksums, privacy/version checks and wheel build. Documentation
link/anchor checks, all 33 tool entries/examples, retained-document checks and
frozen-tool documentation pointers passed. Independent review found one legacy
navigation mismatch, corrected before committing. Runtime source, existing
skills, frozen hooks and test files were unchanged.


## Example-run documentation follow-up: 2026-11-22

Starting from `8a0035f`, analysed a user-supplied private flowchart/export bundle,
then updated only the README and guides as requested. Public examples generalise
study content and identifiers; the source bundle and private evidence notes are
not included in Git. No source scripts from the bundle were executed.

- Added a worked reuse-first study workflow and README flowchart, plus recovery
  guidance for unreadable PDF text, bounded reads, style/profile mismatches,
  revision changes, connection interruptions and companion deck constraints.
- Checked the guidance against current source, including the default create
  action on preview snapshots, workspace-local coverage, optional checks, caller
  evidence and distinct note/card counts.
- `./scripts/check.sh` passed: 28 launcher tests, 250 Python tests, one skipped
  system-Chrome test, frozen contract checksums, privacy/version checks and wheel
  build. `npm pack --dry-run --json` also passed.
- All 33 tool sections still match the API/README; all 33 existing example input
  sets validate against actual annotations. Local Markdown links/anchors resolve.
- A fresh documentation review found no material issues. Clarified that existing
  card IDs are available before a write, while new-card IDs require creation and
  readback.

This follow-up changes no runtime code and makes no live Anki calls. It does not
re-run the private conversation, establish medical accuracy or prove a user sync.
The container results below belong to the earlier repository-polish verification;
a new container build was not needed for these guide-only changes.


## Documentation and repository polish: 2026-11-22

Verified on Linux/Python 3.14 on `docs/student-guides`, starting from release
commit `b0f4233`. The container tested below is labelled `dd66bf6-dirty`:
verification included uncommitted documentation and the container bootstrap fix,
so it is deliberately not presented as a clean-revision build.

- `./scripts/check.sh`: 28 launcher tests passed; 250 Python tests passed, with
  one explicit skip because system Google Chrome was not installed. The real
  Chromium path was exercised. Privacy/version checks, all frozen contract
  checksums and wheel build passed.
- Catalogue validation: all 33 tool sections exactly match the public API and
  README index. All 33 example argument sets validate against actual typed
  inputs. Local documentation links and anchors resolve.
- `npm pack --dry-run` passed. The wheel installed into a disposable target
  outside the checkout; imports, packaged templates/assets and SPDX MIT metadata
  were verified there.
- SDK stdio smoke checks passed from the source checkout, the isolated wheel
  install and the container: 33 tools, source extraction, saved cards, technical
  checks, rendered MCP image content and payload preparation, with zero Anki
  operations.
- `docker compose -p ankiplusmcp config --quiet` and image build passed. The first
  build exposed a pre-existing missing `libatomic.so.1` for Playwright's bundled
  Node. Installing `libatomic1` before Playwright resolved it. The resulting image
  ran as UID/GID 1000 with no network, a read-only filesystem, dropped capabilities,
  no-new-privileges and bounded resources during the smoke check. Disposable
  tmpfs workspaces avoided changing persistent user data.
- A fresh reviewer checked standards, source accuracy, all tools, content
  relocation, packaging and the Dockerfile fix; no material findings remained.
  Two minor wording issues about administrative flags and PDF page limits were
  corrected.
- Runtime Python/JavaScript source, legacy CLI source, existing skills and frozen
  tests were not changed. Repository maintenance changes are the combined check
  entry point, Docker context exclusions, package licence metadata and the Docker
  bootstrap dependency order.

Limits: the default suite does not run all private-lecture contract tests. No
live Anki collection, interactive host registration, Windows client or real
student lecture was exercised. Typed example validation does not establish the
factual accuracy of sample study material. Historical results below remain a
separate record.

Reproduce using the [developer check commands](../developer-guide.md#checks-and-verification)
and [container build instructions](../developer-guide.md#optional-stdio-container).

## Historical implementation snapshot: 2026-11-07

> The following results describe 2026-11-07, not the current checkout or release.

Verified locally on 2026-11-07, Python 3.14/Linux. Source branch:
`feat/ankiplusmcp`, based on upstream `5bb2530`; implementation is uncommitted
because Git author identity is not configured. Container builds are labelled
`5bb2530-dirty`, not a clean upstream revision.

- 177 tests passed: 27 new MCP/service/regression tests, 122 original unit tests,
  and 28 synthetic foundational contract tests.
- Every frozen contract checksum in `.codex/contract.sha256` passed. Existing
  `src/cards/`, `.claude/`, `.agents/`, `.codex/` and contract tests are unchanged.
- Real SDK stdio discovery and calls exercised 33 tools, source extraction,
  structured cards/checks, rendering, MCP image content, domain errors and payloads.
- The same synthetic smoke workflow passed from a separately installed wheel
  outside the checkout and inside the non-root/read-only/network-disabled Compose
  container. The image built successfully and Compose configuration validated.
- The companion skill passed the skill-creator validator.
- An independent reviewer identified six material issues. Regression tests first
  reproduced them; fixes now cover supplied-HTML invalidation, staged/cancel-safe
  extraction, pre-allocation PDF raster bounds, media-filename conflicts,
  duplicate-note update conflicts, and every cloze/native occlusion mask.
- Additional tests cover multi-process locking, revision/snapshot consistency,
  live job ownership vs interrupted jobs, source caching and source-root symlinks.

Reproduce with `./scripts/check-mcp.sh` and
`.venv/bin/python scripts/smoke-mcp.py`. For a built image use
`.venv/bin/python scripts/smoke-mcp.py --command ./scripts/run-container.sh REVISION`.
The container wrapper requires an existing image and never builds on MCP stdout.

Limits: private lecture fixtures were unavailable, so the remaining private-data
contract cases were not run. No live Anki collection or interactive Codex,
Claude Code or OpenCode client was used. The independent reviewer did not judge
factual accuracy, live Anki execution, client UX, or non-Linux support; these
remain explicit limits, not implicit success claims. AnkiPlus performs no Anki
network calls. Windows needs POSIX support through WSL or the Linux container.
