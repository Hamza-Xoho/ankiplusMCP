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

## Mac probe registration diagnosis

The owner subsequently supplied a real Code-session report at `bfca2ab`:
production `ankiplusmcp` was connected, but the separate probe was absent from
tool discovery. Its folder contained `registration.json` without `.mcp.json`.
A separate process listed four probe tools; its piped resource response was not
confirmed. These observations do not establish host connection or embedded UI
support. The reported Desktop version was read from earlier evidence, not
remeasured in that session.

The generator now supplies the missing project-local `.mcp.json` automatically,
identical to the registration fragment, with the absolute venv command and paths.
A new regression reproduced the missing file before the fix, and the stdio/resource
test now uses the generated command/arguments. For an already-prepared Mac folder,
the agent can create that file from its existing fragment if absent, then the owner
starts a new Local Code session on that exact folder, with Worktree off, and accepts
probe enablement. Global Desktop configuration remains a separate Chat-stage action.
Actual probe discovery/resource access/embedding on the Mac are still pending.

Registration-fix verification: ten focused tests passed; `check-mcp.sh` passed
392 tests with its one existing skip, all frozen hashes/42 hooks, wheel/version/
privacy checks and the unchanged 66-file/14-command CLI golden. No production
module, launcher dependency or container build input changed in this fix.

## Observed widget bridge failure

The owner subsequently supplied the widget error
`IPC not available for MCP tool call`. Together with the Mac agent's revision-0
readback and absent save observation, this establishes that saving failed through
the tested Code-managed route while initial embedded rendering succeeded.

The exact symptom is reported in
[Anthropic's issue tracker](https://github.com/anthropics/claude-code/issues/106708).
Independent contributor tests there report that Desktop-managed stdio registration
can forward widget calls in Code and Chat. This is a candidate workaround, not
verified on the owner's Mac. The [scoped retest packet](macos-ipc-probe-retest.md)
backs up configurations, preserves the same server/data, removes only the owned
project-local duplicate and tests Desktop-owned registration. There is no claim
that changing models or repeatedly clicking Save repairs this bridge. Production
UI/coordinator contracts remain gated; restart persistence has not passed.

## Desktop-owned widget-load result

The owner then supplied a screenshot after registering the probe only through
Desktop and restarting: its tools were available and the opener returned revision
0, but Desktop displayed an explicit widget-load error and a JSON text fallback.
Rendering failed on that attempt; it provides no button-save or restart-persistence
pass. Keep it distinct from the earlier Code-managed view that rendered but had
an IPC error on Save. The new screenshot shows Haiku 5.5 / Medium; remeasure actual
runtime versions rather than copying older environment evidence.

The probe's handwritten tool metadata omitted the legacy flat resource URI alias
that the pinned official Apps SDK 2.0.4 supplies alongside the modern nested form.
The generator now matches that normalization, with save still app-only. Its missing
alias was reproduced by a failing test; eleven focused tests now pass. This is a
metadata compatibility correction, not a demonstrated fix for the Mac rendering
failure. The retest packet includes resource/log diagnosis and an owned-file refresh
that preserves registrations, bundle and data, then tests Code/Chat independently.

Metadata-correction verification: eleven focused tests and `check-mcp.sh` passed
(393 tests, one existing skip), with frozen hashes/42 hooks, wheel/version/privacy
and unchanged CLI golden. The real stdio/resource check and SDK iframe emulator
passed using the unchanged previously built UI bundle; zero Anki operations.
The probe schema is now 1,770 UTF-8 bytes with the compatibility aliases; the
production schema remains 30,142 bytes. This is local evidence only.

## Reported Chat save and restart persistence

The owner subsequently pasted Mac-agent evidence that the **Desktop Chat**
widget's Save reached the server: the observation log names the Chat client and
state.json/read_sample_state show revision 1, sample-a `Mac test edit` selected
and sample-b excluded. Reload then displayed the same revision/text/selection.
After a full Desktop quit/reopen, a newly opened Chat view showed those decisions
again, matching server readback and the unchanged state file. These establish
reported save, explicit reload and fresh-Chat restart persistence for that probe.
Zero Anki operations were reported. Raw Mac files remain on the Mac; this host
has not independently inspected them. The exact source/runtime identity for this
latest result must be retained in that Mac evidence rather than inferred here.

Two display limitations remain: save feedback initially stayed stale until
Reload, and a previous conversation's view displayed `Missing synthetic state`.
Persisted data remains intact according to readback, but the old-view error's
cause is undiagnosed. Do not call it harmless or use that broken widget to prove
stale-decision refusal. Use two freshly rendered working views, confirm their
starting revisions and verify an actual rejected stale save. Latest Code-surface
error, content-channel behavior, independent reviewer execution and the companion
gates remain outstanding. A Chat pass does not establish a combined Code workflow.
