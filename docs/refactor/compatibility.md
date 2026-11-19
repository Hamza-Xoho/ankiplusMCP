# Desktop compatibility investigation

Status, 2026-11-19: the user reported passing Mac installer/stdio/lifecycle tests;
see [host evidence](macos-host-lifecycle.md). The remaining UI/reviewer/companion
experiment now has a [reproducible Desktop packet](desktop-compatibility-experiment.md)
and locally tested disposable probe. The combined compatibility gate remains open.
The 2026-11-18 investigation below is retained as history, not a completed spike.

## Established locally

The existing product is a stdio MCP server. No internal sampling/create-message implementation was found in `src/`. Two independent reviewer definitions exist in `.claude/agents/`, and the legacy skill requires the host to launch them. Installing the newer MCP in Desktop alone does not establish those reviewers will execute.

The owner's documented add-on is AnkiMCP on local port 3141. The first-party tool reference documents collection search/read, note creation/update, templates/CSS and media operations. It distinguishes partial batch success. No live companion connection was opened and no collection was mutated.

## Primary documentation

- MCP Apps testing: https://apps.extensions.modelcontextprotocol.io/api/documents/testing-mcp-apps.html — reference-host and actual conversational-host testing are separate; local stdio is listed as a supported connection route.
- AnkiMCP tool reference: https://ankimcp.ai/docs/reference/addon/tools/ — use actual capabilities/version to map operations rather than assume AnkiConnect semantics.
- Add-on source: https://github.com/ankimcp/anki-mcp-server-addon — identify transport/version/authentication and inspect actual result schemas before writing an adapter.
- Claude connector networking: https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp — remote connectors originate from the cloud; local stdio connections are separate. Local-device Cowork and cloud Cowork must not be treated as equivalent.
- Cowork plugin guide: https://claude.com/resources/guides/claude-cowork-product-guide/extending-claude-cowork-with-plugins — plugin subagents have distinct contexts. This is evidence for an investigation route, not proof that the current reviewers and embedded UI work together locally.

Documentation can change; record the installed host/add-on versions in actual acceptance evidence.

## Required real-host experiment

1. On a Mac, use the supported Pro Desktop mode; record exact Chat/Cowork/Code surface and local/cloud execution.
2. Connect sample stdio MCP App and demonstrate select/edit/exclude followed by a server-side decision. Reconnect and confirm the same proposal version survives.
3. Run fresh maintainer/student contexts with the existing packet rules, check/render artifacts and no author conversation inheritance. Verify neither separate API credentials nor an unapproved weaker review are needed.
4. In an isolated Anki profile, discover companion capabilities, create synthetic notes, resolve distinct card IDs, inspect duplicate/partial-success responses and verify suspension state.
5. Interrupt the host after a write is accepted and inspect available readback evidence before selecting retry semantics.
6. Record whether text and structured content both enter model context, and whether direct UI selection invokes the model.

## Gate

No Mac/Desktop session or isolated live Anki is available on this development host. Consequently the combined local interactive UI + independent reviewer + companion path is unverified. Do not freeze production transport/UI implementation from documentation alone, expose Anki publicly as a workaround, or replace the quality process silently. Durable records and other transport-independent work may proceed without claiming this gate passed.

## Disposable probe verification checkpoint

The preparation and evidence-limit fixes are `87391d7` and `93bb57a`.
Post-fix local verification: **624 passed, 25 existing skips** in public-CI mode;
`check-mcp.sh` **391 passed, one existing skip**, frozen hashes and **42 hooks**
intact, wheel/version/privacy checks passed, CLI golden **IDENTICAL (66 files,
14 commands)**. Launcher **42/42** and `uv lock --check` passed. Nine focused probe
tests passed after failed-first steps. Full generated SDK build, rendered reviewer
packets, stdio/resource checks and local iframe emulator passed with zero Anki
operations. Actual tool-schema arrays measured 1,668 / 30,142 UTF-8 bytes for the
four-tool probe / 36-tool product; tokens and host loading remain unmeasured.

The single fresh checkpoint reviewer found a misleading blind-recall expectation:
fronts and backs are exposed together by the preserved packet. A failed regression
now passes with explicit unverified/blocked metadata and corrected evaluator
instructions. The underlying frozen quality-process limitation remains unresolved;
no other material finding or deferred minor was reported. Actual Mac/runtime and
companion results were outside this review. Rulings/costs and the Mac procedure are
in the linked experiment packet. Raw logs and hashes remain ignored under
`.artifacts/compatibility-local/`; generated runs retain their actual dirty-source
provenance. This checkpoint changes no production module or public MCP contract.

Rootless Compose configuration, image build and the hardened real OCR/render smoke
also passed. Image `ankiplusmcp:87391d7-dirty` retains the actual build provenance;
its manifest is `sha256:3d37c8d5ea01100c0f5d99d0535b9da3c767b21ea552b3c0544119f1737237ce`.
The smoke ran as UID 1000 with read-only root, network disabled, dropped
capabilities, no-new-privileges and the existing resource limits. It reported
zero Anki operations. The first build failed fetching pinned `cffi==2.1.1`;
that same version downloaded successfully in a separate bounded diagnostic and
the unchanged build then passed. Both attempts are retained; no lock or runtime
restriction was relaxed. The probe itself is a developer experiment, excluded
from the production container/package.
