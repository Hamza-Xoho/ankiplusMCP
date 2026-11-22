# AnkiPlus MCP design

Status: approved by the user on 2026-11-07; implemented and verified locally; see ../../verification.md.

## Intent and agreed scope

Build `ankiplusmcp` from Lecture2Cards as a portable MCP server providing the
mechanical work that is more reliable and efficient in scripts than in model
reasoning. The model chooses tools for the user's task. A short optional skill
offers examples and source/card-quality guidance without prescribing phases,
review counts, agent names, models, or a mandatory sequence.

The official Anki MCP remains a separate companion dependency configured in the
host. AnkiPlus neither connects to it nor proxies its tools. The host model
passes information between the two servers. AnkiPlus can process supplied files
and card data when Anki is offline; operations requiring live collection data
use snapshots supplied by the model from Anki MCP. The server cannot reliably
discover which other MCP servers the host has connected.

The user has selected the independent-tools approach through the preceding
discussion and request to build. Implementation starts after approval of this
written design, as required by the invoked brainstorming skill.

## Approaches considered

1. Wrap `cards build` as an MCP tool. Smallest change, but retains the mandatory
   P0–P7 controller and does not meet the user's goal.
2. Add a typed MCP layer over reusable Python operations, with standalone card
   operations and structured artifact submission. Selected: preserves working
   extraction, rendering, and validation while allowing model-led workflows.
3. Rewrite everything and integrate Anki execution. Unnecessary replacement of
   working code; integrating Anki conflicts with the requested server boundary.

## Goals and boundaries

- Expose the useful capabilities of the existing CLI and five legacy helper
  scripts through discoverable, typed tools. Maintain a capability mapping in
  documentation so a helper option is not silently lost.
- Support lecture drafting, partial-source work, figure occlusion, inspection
  and review of existing cards, structured fixes, and preparation of artifacts
  for the official Anki MCP.
- Keep judgement in the host model: no embedded model calls, model keys,
  automatic reviewer spawning, or mandatory AI-review loop.
- Preserve the legacy `cards` CLI, old skills, frozen contract tests, and the
  existing gate/write semantics. The MCP does not invoke the phase controller.
- Do not implement collection searches, deck mutation, uploads to Anki,
  suspension/unsuspension, scheduling, or deletion: those belong to Anki MCP.
- Do not advertise local validation as proof of source accuracy, independent
  review, actual Anki writes, or successful collection verification.

## Packaging and implementation defaults

Builder recommendation: Python 3.12+, the official Python MCP SDK, Pydantic
schemas, and an `ankiplusmcp` console command using stdio. Pin and record the
tested SDK/dependency resolution. Logs go to stderr; stdout carries MCP only.
Create a sibling package `src/ankiplusmcp/` so MCP/network dependencies never
enter the legacy `src/cards/` package. Reuse its pure functions and operation
entry points through a service adapter, not subprocess text parsing.

Brand the distribution, command, server, README, and companion skill
`ankiplusmcp`; keep the `cards` import namespace and console command for
compatibility. Use a project directory `/home/<name>/projects/ankiplusmcp/`
at implementation time, preserving Git history and the upstream remote. Do not
rename the GitHub repository, push, publish a package, or install globally.

Local stdio is the first delivery. Remote HTTP hosting, authentication,
multi-user uploads, and public deployment are outside this implementation.
Provide an optional non-root container image and stdio invocation if the
selected SDK/dependencies support this cleanly; no network listener or gateway.

## Workspace and artifact model

- Configure a stable workspace root at server launch. Use explicit workspace
  IDs on all workspace calls; never rely on cwd or the legacy `.current` pointer.
- Create lecture workspaces from a read-only local PDF/text/Markdown source,
  pasted text, or existing-card snapshots. Existing-card workspaces do not need
  a lecture, invented slides, learning objectives, or a target deck.
- Allocate IDs on the server. Constrain generated artifacts and mutable state
  to the selected workspace. Resolve and check paths and symlinks; prevent
  overwrites of source files, path traversal, and cross-workspace writes.
- At launch, configure readable source roots. Explicit source/image imports
  may read only from these roots. Copy imported media into the workspace;
  clients subsequently refer to artifact IDs instead of arbitrary output paths.
- Use atomic artifact writes, a workspace revision, per-workspace mutation
  locks, and expected-revision checks. Reject stale edits with a useful error.
  Concurrent processes using the same root must share the locking mechanism.
- Persist source hashes, card snapshots, findings, previews, review versions,
  changes, and user-supplied external results. Resume after process restart.
  A new request does not silently overwrite or replay an existing workspace.

## Public tool capabilities

Names are proposed API names; the builder can split a tool when its schema or
description would otherwise be ambiguous. Do not expose arbitrary shell
execution, arbitrary file writes, or a generic opaque CLI-argument tool.

| Tools | Inputs and behaviour |
| --- | --- |
| `capabilities`, `get_guidance` | Version, dependencies, supported operations, optional house style/reviewer rubrics, and actionable prerequisite diagnostics. No automatic connection to Anki. |
| `create_workspace`, `list_workspaces`, `get_workspace` | Source or supplied card snapshot; stable IDs, mode, revision, available artifacts and jobs. No mandatory phases. |
| `extract_source`, `read_source`, `search_source` | PDF/text/Markdown extraction, optional slide ranges, objective/map/summary artifacts, bounded paginated slices and search hits with source references. |
| `get_page_image`, `list_figures`, `get_figure` | Page rasterization, figure metadata/crops, OCR labels, repeated-label groups, and image output. |
| `ocr_image`, `build_occlusion` | Imported image or figure artifact, OCR options, normalized regions, grouped repeated labels, selected groups, one/all mode, Anki-native field markup, media and preview artifacts. |
| `resolve_target` | Filename/title identity, explicit overrides, supplied existing deck names, source/tier tags; returns suggestions without creating a deck. Expose the legacy naming convention explicitly when requested. |
| `save_cards`, `get_cards`, `save_omissions` | Structured drafts or existing-card snapshots with stable local IDs, optional Anki note/card IDs and provenance. Validate shape before atomic save; return exact field errors. Paginate reads. |
| `check_cards` | Selected cards; structural and cloze/HTML/style findings. Lecture coverage is an explicit additional check requiring extracted source/objectives. Existing-card checks accept arbitrary supplied field names and do not require ColdRecall tags or a lecture target. |
| `render_cards` | Selected cards, optional supplied note-type front/back/CSS or supplied rendered question/answer HTML, imported media, layout options, individual previews and contact sheets. Works without a lecture pipeline. |
| `prepare_review`, `submit_review`, `apply_changes` | Prepare source-grounded or visual-only review bundles, accept typed findings/rewrites, validate changes, preview the diff, and apply selected changes against the expected workspace revision. No fixed number of reviewers/rounds; no automatic PASS claim. |
| `prepare_write` | Prepare bounded create/update payloads, import files, media manifests, intended suspension mappings and verification expectations from selected cards. Pure artifact production. Revalidate current cards and bind output to the exact workspace/card revision. |
| `record_external_results`, `get_report` | Store explicitly caller-supplied Anki responses and verification evidence; distinguish planned, caller-reported and verified-by-supplied-evidence counts. Report pending/ambiguous results honestly. Never auto-retry Anki writes. |
| `list_artifacts`, `read_artifact`, `get_image` | Allowlisted workspace artifacts; bounded text/JSON with continuation, images returned as MCP image content. No bare-path-only requirement or unrestricted filesystem browsing. |
| `get_job`, `cancel_job` | Poll persistent long-operation state, progress, result references and bounded errors; cooperative cancellation. |

Use the existing source/extraction, OCR, occlusion, renderer, checks, target,
and import serialization code where suitable. Standalone adapters remove
lecture-only assumptions rather than fabricating lecture metadata. Usage-meter
support is an optional diagnostic tool with explicit transcript input and
Claude-format limitations, rather than a required report dependency. Inventory
state-management helpers internally; do not expose arbitrary phase advancement.

## Validation, review, and write preparation

The MCP is not an alternative bypass path into the legacy build gate. New
independent workspaces keep their own manifests. Legacy builds can be inspected
read-only initially; they are not silently converted or modified by MCP tools.

`check_cards` always applies technical schema checks appropriate to the input.
House-style and coverage checks are named options with their applicability
reported. Source fidelity and usefulness remain model/human judgements.
Submitting a review does not confer independence: record reviewer labels and
scope as caller-provided metadata, not independently verified identities.

`prepare_write` produces payloads only, including any remaining warnings,
review evidence, input hashes and intended operations. It never writes to Anki
or stamps a legacy gate as passed. There is no mandatory two-reviewer gate in
this new toolkit. Preserve source fidelity guidance, prevent malformed payloads,
require existing note IDs for updates, and represent suspension intentions using
explicit known card IDs or an unresolved note-to-card mapping. Never confuse
note IDs with card IDs or infer returned IDs. The host uses Anki MCP to perform
and verify authorized operations.

## Result, image, and error contracts

- Typed inputs with explicit enum/range/size validation and tool descriptions
  covering purpose, required inputs, side effects and useful follow-ups.
- Structured results with status, workspace revision, summary, findings,
  artifact references and continuation information. Provide readable text
  alongside structured data for clients that display only text.
- Domain errors include code, affected field/artifact and concrete remedies.
  A correctable field error must not require restarting a workspace. Mark
  operation errors through MCP error results rather than crashing the server.
- Cap text, pages, card batches, image dimensions and decoded image size.
  Preserve full artifacts on disk. Expose images as MCP image blocks when
  requested; support tool-based retrieval even if resources are unsupported.
- Render HTML inertly: disable JavaScript, external requests, service workers
  and downloads; serve only imported/allowlisted workspace media. Keep existing
  sanitization and renderer network blocking.

## Long work, interruption, and compatibility

Extraction, OCR and batch rendering run as jobs, returning an ID promptly.
Use a bounded worker pool and avoid blocking the MCP event loop. Durable job
records distinguish queued/running/completed/failed/cancelled/interrupted.
After restart, previously running work is interrupted, never falsely complete;
explicit retry uses valid cached artifacts and writes outputs atomically.
Queued cancellations stop promptly; running cancellation is cooperative between
safe work units and must not publish partial outputs as complete.

Use standard stdio and ordinary tools/results as the compatibility baseline;
do not require MCP sampling, host subagents, experimental tasks, or resource
support. Document tested client setup for Codex, Claude Code and OpenCode and
the separate official Anki MCP dependency. Verify client config syntax against
current primary documentation during implementation. Do not claim live
end-to-end client or Anki testing that was not performed.

## Companion skill

Ship a small portable skill named `ankiplusmcp` with usage examples: lecture to
cards, targeted source inspection, image occlusion, visual review of existing
cards, and an Anki-only unsuspension request. Explain that AnkiPlus tools handle
artifacts, Anki tools handle the collection, and the model chooses the sequence.
Keep detailed optional quality guidance in separately retrievable resources.
Do not install the skill or alter user MCP settings without an explicit request.

## Verification and delivery

- Add meaningful tests for tool schemas and a real stdio MCP session covering
  discovery, structured results, image retrieval, domain errors, cancellation,
  restart recovery, revision conflicts and path containment.
- Exercise PDF/text extraction, OCR/occlusion with synthetic input, card saving,
  standalone checking/rendering, review changes, payload preparation and
  external-result reporting without Anki or private lecture fixtures.
- Test malformed HTML, missing dependencies, invalid review fields, stale
  artifacts, note/card ID distinctions, and refusal to access source/output
  paths outside allowed roots. Confirm no collection network calls occur.
- Run the existing unit suite and applicable available regression checks.
  Preserve frozen tests. If private fixtures are required but absent, report
  that limitation instead of weakening or silently skipping those tests.
- Build a wheel, install it into a clean environment, run stdio discovery and
  one synthetic workflow from outside the checkout, and verify bundled assets.
- Supply README setup/build/check commands, environment/config examples,
  capability mapping, companion skill and repeatable smoke-check helpers.
  Record source revision/dirty status for any image build.
- Use focused local commits if configured Git identity is available. Do not
  invent identity, push, publish, or deploy. Currently no local Git author
  identity was returned; if still absent, leave changes reviewable and report it.

## Builder-owned details

The builder chooses internal module boundaries, exact Pydantic models, the
compatible MCP SDK version, artifact URI format, pagination defaults, worker
limits, lock implementation, and testing fixtures. These must satisfy the
contracts above and be recorded where needed for maintenance. Major scope
changes return to the user; routine implementation choices do not.
