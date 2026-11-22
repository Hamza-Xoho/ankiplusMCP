# AnkiPlus MCP tool reference

[README](../README.md) · [Setup](setup.md) · [Developer architecture](developer-guide.md)

These are the **33 MCP tools** registered by [server.py](../src/ankiplusmcp/server.py).
Students normally ask their assistant for an outcome; the assistant makes these
calls. Developers can use this reference to understand the same calls and follow
them into the code. The tools do no model inference and no Anki collection I/O.

## Conventions used below

Examples show a tool name followed by its JSON arguments, not a shell command.
`WORKSPACE`, `JOB`, `REVIEW`, `PLAN` and example artifact paths are placeholders:
replace them with values returned by earlier calls. Examples are standalone
illustrations, not a script to execute in order. Use the actual current revision.
Tools are independent except where one needs an artifact or state from another.

| Input | Meaning |
| --- | --- |
| `workspace` | Explicit workspace ID from `create_workspace` or `list_workspaces`; required wherever shown. |
| `expected_revision` | Current integer revision from `get_workspace` or the last mutation result. Read again after a job or artifact-producing operation. |
| `ids` | Optional local card IDs. Omit for all cards; these are distinct from Anki note IDs and card IDs. |
| `slides`, `pages` | Optional 1-based ranges such as `2-5,8`. Omit to use all available pages. |
| `artifact` | Workspace-relative artifact ID returned by a tool, never an arbitrary host path. |
| `offset`, `limit` | Pagination. Offsets start at 0. Most lists default to 20 items, maximum 100. Text defaults to 12,000 characters, maximum 24,000. |

Follow `next_offset` until it is `null` where supplied. `list_workspaces` instead
returns `total`: increment the offset yourself until you have that many entries.
Most tools return JSON in both text and structured MCP content. `get_image`
returns an MCP image content block. Validation and domain errors use
`isError: true` with an error code, message and remedy. The host's discovered MCP
schemas are authoritative for exact types and numeric bounds.

Four tools return **jobs**: `extract_source`, `export_figures`, `ocr_image` and
`render_cards`. Use `get_job` until a terminal state, then follow its `result`.
A queued/running response is not the finished output. See [jobs](#get_job).

## Combining the tools for a lecture task

The [worked study workflow](study-workflow.md) shows reuse-first matching,
explanatory backs, diagram choices, manual review and the separate Anki handoff.
The important contracts when combining calls are:

- Collection matching is performed by the host through its Anki MCP, not by
  `resolve_target` or `check_cards`. Source objectives help the assistant decide
  what existing cards cover and where new drafts are needed.
- Keep existing-card preview snapshots separate from new-note drafts. The
  default `action="create"` on a snapshot does not mean it should be imported
  again. Unsuspension uses actual Anki card IDs through the companion.
- Rich backs use the saved note's existing fields, media and supplied templates;
  there is no automatic explanation/image selection tool. Inspect both sides.
- Wait for rendering or other artifact-producing jobs, then refresh the workspace
  before saving/reviewing against its revision. Do not remove the revision guard
  to work around a `STALE` response.
- Preparing a plan and submitting a review do not authorise a collection write.
  If the user requests approval first, the host must preserve that requirement
  through revisions and interruptions; AnkiPlus does not enforce it remotely.

## Setup and workspaces

### capabilities

**Use it to:** find out what this installation can do before starting a task.

**Inputs:** none. **Returns:** server version, stdio transport, Python dependency
versions, Tesseract/browser availability, browser selection, source roots and
their origin, active profile, guidance topics and missing-dependency remedies.
It explicitly reports that Anki is a separate host dependency.

**Example:** `capabilities {}`.

**Implementation:** [API.capabilities](../src/ankiplusmcp/server.py) reads installed
package metadata, [doctor.py](../src/ankiplusmcp/doctor.py) and service settings.
It does not test a live Anki connection. No workspace is required.

### get_guidance

**Use it to:** give the assistant optional workflow examples or a review rubric.

**Inputs:** `topic`: `overview` (default), `quality`, `maintainer` or `student`.
**Returns:** topic, bounded guidance text and `optional: true`.

**Example:** `get_guidance {"topic":"student"}`.

**Implementation:** [API.get_guidance](../src/ankiplusmcp/server.py) loads the packaged
[overview](../src/ankiplusmcp/guidance/SKILL.md), or house-style/reviewer Markdown
from [cards/templates/review](../src/cards/templates/review). It starts no reviewer
and imposes no sequence. No workspace is required.

### create_workspace

**Use it to:** start a lecture task, pasted-notes task or existing-card task.

**Inputs:** `mode`: `cards` (default) or `lecture`; optional `source_path`, `text`
or `cards`. `source_path` must be an absolute PDF/text/Markdown path within a
readable source root. Supply a file or pasted text, not both. Cards can accompany
a source or be used alone. **Returns:** manifest with `id`, `mode`, `source`
provenance and current `revision` (0 initially; saving initial cards advances it).

**Example:** `create_workspace {"mode":"lecture","text":"Osmosis is water movement across a selectively permeable membrane."}`.

**Implementation:** [API.create_workspace](../src/ankiplusmcp/server.py) calls
[Store.create](../src/ankiplusmcp/store.py) to allocate a UUID directory and copy
a read-only source snapshot with SHA-256, then optionally calls `save_cards`.
No extraction, drafting or Anki operation happens automatically.

### list_workspaces

**Use it to:** resume a previous study task.

**Inputs:** `offset=0`, `limit=20`. **Returns:** manifests in `workspaces`, and
`total`. Pagination is by offset, with no `next_offset` field. Order is by workspace
ID, not last-used date.

**Example:** `list_workspaces {"offset":0,"limit":10}`.

**Implementation:** [Store.list](../src/ankiplusmcp/store.py) finds non-symlink
workspace directories containing `workspace.json`. There is no active-workspace
pointer or automatic lookup in the host's chat history.

### get_workspace

**Use it to:** inspect a task's source and obtain the current revision before editing.

**Inputs:** `workspace`. **Returns:** the manifest: ID, mode, revision, optional
source provenance and published extraction pointer.

**Example:** `get_workspace {"workspace":"WORKSPACE"}`.

**Implementation:** [Store.get](../src/ankiplusmcp/store.py) reads `workspace.json`
through containment-checked paths. It does not return the card set; use `get_cards`.

## Lecture text and figures

### extract_source

**Use it to:** make a PDF, text file, Markdown file or pasted source readable to the assistant.

**Inputs:** `workspace`, optional `slides`. A source snapshot must exist.
**Returns:** a job; its completed result contains `slide_count`, `map`, `summary`
and, when reused, `cached: true`. The map and summary are artifact IDs.

**Example:** `extract_source {"workspace":"WORKSPACE","slides":"2-5,8"}`.

**Implementation:** [Sources.extract_source](../src/ankiplusmcp/sources.py) calls the
[extraction core](../src/cards/extract/__init__.py): PyMuPDF text/crops, Tesseract
when OCR is needed, objectives and slide maps. It stages output in a fresh folder,
checks source hashes and publishes a pointer after completion. Matching published
extractions and content-addressed OCR results can be reused. While figure OCR is
running, early text/crops can be read with `labels_pending: true`; coverage needs
the finished extraction. Prior published extraction takes precedence over early
text from a replacement run. Missing Tesseract matters only when OCR is needed.

### read_source

**Use it to:** read selected slides without loading the entire lecture into context.

**Inputs:** `workspace`, optional `slides`, `offset=0`, `limit=12000` characters.
**Returns:** `text`, selected `slides`, `total_chars`, `next_offset` and possibly
`labels_pending`. Extraction must have published text or reached its early-text stage.

**Example:** `read_source {"workspace":"WORKSPACE","slides":"2-3","limit":6000}`.

**Implementation:** [Sources.read_source](../src/ankiplusmcp/sources.py) selects slide
records via [source_data](../src/cards/common/source_data.py), formats them through
[cards.source.slice_text](../src/cards/source.py), then slices the text. It does
not re-open or re-extract the original lecture.

### search_source

**Use it to:** locate a topic or term in the extracted lecture.

**Inputs:** `workspace`, `query` (1–200 characters), `offset=0`, `limit=20`.
**Returns:** matching lines in `hits` with slide numbers, `total`, `next_offset`
and possibly `labels_pending`. Requires extracted or early text.

**Example:** `search_source {"workspace":"WORKSPACE","query":"membrane"}`.

**Implementation:** [Sources.search_source](../src/ankiplusmcp/sources.py) performs
case-insensitive substring matching over saved slide lines. It is a local text
search, not semantic search or a request to a model.

### get_page_image

**Use it to:** inspect a whole slide when text or a figure crop lacks context.

**Inputs:** `workspace`, `page` (1–500, within the extracted selection).
**Returns:** an image `artifact`; pass it to `get_image`. Needs a PDF source and
extracted/early slide data. Text/Markdown sources cannot supply a PDF page image.

**Example:** `get_page_image {"workspace":"WORKSPACE","page":3}`.

**Implementation:** [Sources.get_page_image](../src/ankiplusmcp/sources.py) delegates
to [cards.source.page_image](../src/cards/source.py) and writes a PNG in the current
source folder under a workspace edit lock. This advances the workspace revision.
It is synchronous, not a job.

### list_figures

**Use it to:** discover which extracted diagrams may be useful for cards.

**Inputs:** `workspace`, `offset=0`, `limit=20`. **Returns:** `figures`, `total`,
`next_offset`. Each record includes `fig_id`, slide provenance, crop artifact and
OCR information. Requires extracted/early source data.

**Example:** `list_figures {"workspace":"WORKSPACE","limit":10}`.

**Implementation:** [Sources.list_figures](../src/ankiplusmcp/sources.py) flattens the
saved per-slide figure records and attaches workspace-relative crop paths.
During early extraction, `ocr_labels: null` means labels are not read yet;
`[]` means OCR completed and found none. Look for `labels_pending`.

### get_figure

**Use it to:** resolve one exact figure after listing candidates.

**Inputs:** `workspace`, `figure_id` from `list_figures`. **Returns:** its saved
record, slide number, `artifact` and possibly `labels_pending`. Use `get_image`
to actually view the crop.

**Example:** `get_figure {"workspace":"WORKSPACE","figure_id":"FIGURE_ID"}`.

**Implementation:** [Sources.get_figure](../src/ankiplusmcp/sources.py) searches the
source's figure records by exact ID. Unknown IDs return `FIGURE` with a remedy.
This does not run extraction or OCR again.

### export_figures

**Use it to:** get higher-resolution crops, or export a whole slide containing vector artwork.

**Inputs:** `workspace`, optional `pages`, `zoom=4` (0.5–6), `min_frac=0.05`
(minimum placement area as a fraction of page area), `whole_page=false`.
**Returns:** a job; completed result includes figure artifact records and a JSON
`manifest`. Requires a PDF source; does not require prior text extraction.

**Example:** `export_figures {"workspace":"WORKSPACE","pages":"12","whole_page":true,"zoom":2}`.

**Implementation:** [Sources.export_figures](../src/ankiplusmcp/sources.py) uses
PyMuPDF image placements or whole-page rectangles, checks raster bounds before
allocation, and writes PNGs under `exports/<id>/`. It does not add these exports
to `list_figures`, run OCR or save cards. Large job results may require reading
the manifest through `read_artifact`.

## Images and occlusions

### import_image

**Use it to:** bring a PNG, JPEG or WebP diagram into an existing task.

**Inputs:** `workspace`, absolute `path` under a readable source root.
**Returns:** copied image `artifact`. Advances the workspace revision.

**Example:** `import_image {"workspace":"WORKSPACE","path":"/absolute/lectures/diagram.png"}`.

**Implementation:** [Sources.import_image](../src/ankiplusmcp/sources.py) uses
[Store.import_file](../src/ankiplusmcp/store.py) to validate format/size with Pillow
and copy bytes into `media/<id>.<extension>`. The original is unchanged. Importing
an image does not save a card or recognise any labels.

### ocr_image

**Use it to:** propose label rectangles for an imported image or extracted figure.

**Inputs:** `workspace`, `artifact`, `min_conf=20` (0–100), `min_len=2` (1–100),
`group=true`, `pad=0.004` (0–0.1). Padding is a fraction of image dimensions.
**Returns:** a job; result names an OCR JSON `artifact` and `region_count`.
Read that artifact to obtain `regions`. Requires Tesseract and a valid image.

**Example:** `ocr_image {"workspace":"WORKSPACE","artifact":"media/IMAGE.png","min_conf":40}`.

**Implementation:** [Sources.ocr_image](../src/ankiplusmcp/sources.py) validates the
image, calls [cards.extract.ocr.extract](../src/cards/extract/ocr.py), and stores
fractional rectangles under `ocr/`. Repeated labels are grouped by default.
OCR is a suggestion: inspect the image and adjust regions before masking.

### build_occlusion

**Use it to:** turn chosen label rectangles into native Anki image-occlusion fields.

**Inputs:** `workspace`, image `artifact`, 1–500 `regions`, `mode="one"` or
`"all"`, optional `keep` group IDs. Each region needs `left`, `top`, `width`,
`height` as fractions of image dimensions; optional `text`, positive `group`,
and `conf`. Rectangles must fit inside the image. `keep` selects supplied group
IDs, not rectangle offsets.

**Returns:** `fields` (`Image`, `Occlusion`), `media`, a rectangle-outline
`preview`, and normalised `regions`. No card is saved. Supply the fields/media
in a card with `kind="io"` and the matching Anki note type, then use `save_cards`.

**Example:** `build_occlusion {"workspace":"WORKSPACE","artifact":"media/IMAGE.png","regions":[{"left":0.1,"top":0.2,"width":0.25,"height":0.08,"text":"Nucleus"}],"mode":"one"}`.

**Implementation:** [Sources.build_occlusion](../src/ankiplusmcp/sources.py) reuses
[cards.figures](../src/cards/figures.py) for repeated-label grouping, native cloze
mask markup and Pillow previews. `one` hides the current group while other groups
remain visible; `all` keeps other groups masked too. The preview outlines candidate
rectangles; `render_cards` shows the actual front/back card approximation. Writes
media and `occlusions/<id>.json`, advancing revision. No OCR dependency is needed
when you supply rectangles yourself.

## Cards, organisation and previews

### resolve_target

**Use it to:** suggest a lecture's deck identity and tags.

**Inputs:** `filename=""`; optional `course`, `number` (1–999), `title`, `subject`,
`system`, `existing_decks`; `legacy=false`. Supply course, number and title
explicitly when filename inference is uncertain. **Returns:** inferred target,
confidence, profile note type, and, when confident, whether a deck name would be
new. Needs no workspace. Existing deck names must be supplied by the host.

**Example:** `resolve_target {"course":"BIO101","number":3,"title":"Cell membranes"}`.

**Implementation:** [Sources.resolve_target](../src/ankiplusmcp/sources.py) calls
[cards.target](../src/cards/target.py) with the configured tag root. `legacy=true`
selects the legacy deck naming form. It does not query or create Anki decks,
and it does not assign the target to your saved cards automatically.

### save_cards

**Use it to:** save drafts or snapshots of existing Anki notes locally.

**Inputs:** `workspace`, complete `cards` list (1–500), `expected_revision`.
**Returns:** new `revision` and number `saved`. **Replaces the entire set**;
merge retained cards into the input if you are adding or editing a subset.

**Example:** `save_cards {"workspace":"WORKSPACE","expected_revision":0,"cards":[{"id":"cell-1","fields":{"Text":"The {{c1::nucleus}} contains DNA."},"source_ref":[2]}]}`.

**Implementation:** [Cards.save_cards](../src/ankiplusmcp/cards.py) validates
[Card models](../src/ankiplusmcp/models.py), fills omitted note types from the
profile, checks duplicate local IDs and media images, then writes `cards.json`
under a revision-checked lock. Structural validation here does not replace
`check_cards` technical checks. Saved previews/reviews/plans are not deleted;
their card hashes reveal when they are stale.

### get_cards

**Use it to:** read drafts before inspecting, editing or resuming them.

**Inputs:** `workspace`, optional `ids`, `offset=0`, `limit=20`.
**Returns:** selected `cards`, `total`, current `revision`, `next_offset`.
Unknown selected IDs return an error.

**Example:** `get_cards {"workspace":"WORKSPACE","ids":["cell-1"]}`.

**Implementation:** [Cards.get_cards](../src/ankiplusmcp/cards.py) selects from
`cards.json` while holding the workspace lock, so the list and revision come
from the same snapshot. For large fields, reduce the limit or read the artifact.

### save_omissions

**Use it to:** explain why parts of a lecture intentionally have no cards.

**Inputs:** `workspace`, `omissions` (up to 500 objects, each with positive integer
`slide` and non-empty `reason`), `expected_revision`. **Returns:** new `revision`
and `saved` count. Replaces the omission list; an empty list clears it.

**Example:** `save_omissions {"workspace":"WORKSPACE","expected_revision":1,"omissions":[{"slide":1,"reason":"Title slide only"}]}`.

**Implementation:** [Cards.save_omissions](../src/ankiplusmcp/cards.py) validates the
records and writes `omissions.json` under the revision lock. The optional coverage
check uses these records; saving them does not change cards or extract a source.

### check_cards

**Use it to:** catch mechanical problems before previewing or preparing cards for Anki.

**Inputs:** `workspace`, optional `ids`, `house_style=false`, `coverage=false`.
**Returns:** `findings` with codes/severity, `blockers`, optional `coverage`,
`checked`, and `source_accuracy_verified: false`. Card-only technical checks
need no lecture. Coverage requires completed extraction; early text gives
`LABELS_PENDING`.

**Example:** `check_cards {"workspace":"WORKSPACE","coverage":true}`.

**Implementation:** [Cards.check_cards](../src/ankiplusmcp/cards.py) combines typed
card validation, [cloze/occlusion checks](../src/ankiplusmcp/validation.py), optional
[cards.check.lint](../src/cards/check/lint.py) house rules and
[coverage](../src/cards/check/coverage.py) summaries. It returns findings without
rewriting cards. Coverage on `ids` evaluates that selection, not omitted cards.
It does not verify factual truth or fetch existing Anki cards. Coverage also does
not combine a separate existing-card preview workspace with the draft workspace;
keep an explicit learning-objective map when counting reused cards toward coverage.

### render_cards

**Use it to:** see how draft or existing cards look on front and back.

**Inputs:** `workspace`, optional `ids`, `front`, `back`, `css`; `per_sheet=8`
(1–16), `desktop_sample=0` (0–10), `light=false`. Template arguments apply to
field-based rendering. Paired `question`/`answer` HTML on a saved card takes
precedence. **Returns:** a job; its result contains `sheets`, optional `samples`,
selected IDs, card hash, revision and output prefix. Requires saved cards and
an available preview browser.

**Example:** `render_cards {"workspace":"WORKSPACE","per_sheet":4,"desktop_sample":1,"light":true}`.

**Implementation:** [Cards.render_cards](../src/ankiplusmcp/cards.py) builds rows via
[cards.render](../src/cards/render/__init__.py), sanitises/embeds allowed media,
and uses Playwright for PNG contact sheets. [variants.py](../src/ankiplusmcp/variants.py)
adds 1024px desktop fronts and phone light-mode samples; standard previews are
390px phone views. A revision guard and card hash bind `latest-preview.json` to
the saved snapshot. Use `get_image` on sheet `fronts`/`backs` paths. Anki's full
engine, custom filters and add-on scripts are not emulated.

## Optional review and changes

### prepare_review

**Use it to:** assemble information for a content reviewer or a visual reviewer.

**Inputs:** `workspace`, `scope="content"` or `"visual"`, optional `ids`.
**Returns:** bundle with revision and selected IDs. Content includes cards and
source availability; visual includes only preview sheets and no fields/sources.
Visual review requires current previews for exactly that card selection, otherwise
returns `needs_previews`, `stale_previews` or `needs_scoped_previews` with next steps.

**Example:** `prepare_review {"workspace":"WORKSPACE","scope":"visual"}`.

**Implementation:** [Review.prepare_review](../src/ankiplusmcp/review.py) builds a
bundle under a workspace lock and validates preview hashes/selections. It starts
no agent and saves no findings. The host chooses who reviews; AnkiPlus does not
verify reviewer independence.

### submit_review

**Use it to:** record review findings and proposed field changes without applying them.

**Inputs:** `workspace`, `reviewer` label, `findings` (up to 1000), `expected_revision`.
Each finding has local `card_id`, `verdict` (`pass`, `fix`, `reject`), optional
`message`, `rewrite` mapping existing field names to new values, and `source_refs`.
**Returns:** `review_id`, new `revision`, finding count. A verdict alone does not
remove or change a card.

**Example:** `submit_review {"workspace":"WORKSPACE","reviewer":"content-check","expected_revision":1,"findings":[{"card_id":"cell-1","verdict":"fix","rewrite":{"Text":"The {{c1::nucleus}} contains most eukaryotic cellular DNA."}}]}`.

**Implementation:** [Review.submit_review](../src/ankiplusmcp/review.py) validates
[Finding](../src/ankiplusmcp/models.py), checks card/field references, and writes
`reviews/<id>.json` with a card hash and `identity_verified: false`.

### apply_changes

**Use it to:** inspect a review's before/after diff, then explicitly apply selected rewrites.

**Inputs:** `workspace`, `review_id`, `expected_revision`, optional `ids`,
`apply=false`. **Returns:** `changes`, `applied`, revision and, after saving,
`saved`. Default is preview only. Applying changes affects local fields, never Anki.

**Example:** `apply_changes {"workspace":"WORKSPACE","review_id":"REVIEW","expected_revision":2,"apply":false}`.

**Implementation:** [Review.apply_changes](../src/ankiplusmcp/review.py) checks the
saved review's card hash, rejects conflicting rewrites and stale revisions, then
optionally calls `save_cards`. Changed fields clear supplied question/answer HTML
so old previews cannot hide the edit. It does not create/delete cards from
verdicts or enforce a legacy review gate. Re-check and re-render changed cards.

## Anki handoff and reporting

### prepare_write

**Use it to:** prepare technically valid notes and media for your host to send to Anki.

**Inputs:** `workspace`, `expected_revision`, optional `ids`.
**Returns:** `plan_id`, plan `artifact`, planned create/update counts, batch
references and `performed_anki_operations: 0`. Read the plan and batch artifacts
for actual payload contents. Technical blockers refuse preparation; review and
house-style gates are not required. Does not advance revision.

**Example:** `prepare_write {"workspace":"WORKSPACE","expected_revision":3}`.

**Implementation:** [Payloads.prepare_write](../src/ankiplusmcp/payloads.py) checks
technical validity, groups creates by deck/note type/field layout into batches of
at most 100, merges compatible updates by note ID, detects media-name/content
conflicts, emits text imports via [cards.write.importfile](../src/cards/write/importfile.py)
and records tier-3 suspension intentions. Artifacts live in `write/<plan>/`.
The host imports media, executes writes via Anki MCP and resolves actual Anki
card IDs before suspension. Counts named `created`/`updated` here describe the
plan, not successful writes. They count note records, not all generated study
cards; one cloze or image-occlusion note may produce several cards. Inspect the
desired actions before executing them.

### record_external_results

**Use it to:** attach actual Anki responses supplied by the host to a prepared plan.

**Inputs:** `workspace`, `plan_id`, `results` (up to 1000), `expected_revision`.
Each result has `operation` (`create`, `update`, `media`, `suspend`, `unsuspend`,
`verify`), `status` (`success`, `failed`, `ambiguous`), optional `note_ids`,
`card_ids`, `batch_artifact`, `detail`.
**Returns:** new `revision`, number `recorded`, `evidence_origin: "caller_supplied"`
and `independently_verified: false`. Replaces the supplied result list for that plan.

**Example:** `record_external_results {"workspace":"WORKSPACE","plan_id":"PLAN","expected_revision":3,"results":[{"operation":"create","status":"ambiguous","detail":"Connection closed before a response; reconcile in Anki before retrying."}]}`.

**Implementation:** [Payloads.record_external_results](../src/ankiplusmcp/payloads.py)
validates [ExternalResult](../src/ankiplusmcp/models.py), refuses a stale card hash,
and writes `external-results.json` under the revision lock. It performs no live
verification and is not proof that a caller's claim is correct.

### get_report

**Use it to:** summarise what was planned and what the host says happened.

**Inputs:** `workspace`. **Returns:** local card count/revision, planned create and
update counts when available, `plan_stale`, reported successes/failures/ambiguities,
and explicit evidence-origin/zero-Anki-operation flags. With no plan it returns
a basic workspace report.

**Example:** `get_report {"workspace":"WORKSPACE"}`.

**Implementation:** [Payloads.get_report](../src/ankiplusmcp/payloads.py) follows
`latest-plan.json` and optional receipts. Reported success counts count result
records, not necessarily individual notes. Reports do not reconcile a live
collection; the host must do that through Anki MCP.

## Artifacts, jobs and diagnostics

### list_artifacts

**Use it to:** find generated maps, OCR output, previews, reviews and payload files.

**Inputs:** `workspace`, `offset=0`, `limit=50` (maximum 100).
**Returns:** relative `artifacts`, `total`, `next_offset`.

**Example:** `list_artifacts {"workspace":"WORKSPACE","limit":50}`.

**Implementation:** [Artifacts.artifacts](../src/ankiplusmcp/artifacts.py) walks the
workspace, omitting hidden entries and symlink files. It lists local files, not
Anki media. A file's existence does not mean its generating job completed or
that the artifact is current; check job state and current pointers/hashes.

### read_artifact

**Use it to:** read a generated text or JSON file in bounded chunks.

**Inputs:** `workspace`, `artifact`, `offset=0`, `limit=12000` characters.
**Returns:** bounded `text`, `artifact`, `total_chars`, `next_offset` and possibly
`labels_pending`. Supports JSON/JSONL, text, Markdown, HTML, CSS, CSV and TOML.
HTML is returned as text, not executed.

**Example:** `read_artifact {"workspace":"WORKSPACE","artifact":"cards.json","limit":6000}`.

**Implementation:** [Artifacts.read_artifact](../src/ankiplusmcp/artifacts.py) checks
containment, extension and size, then reads UTF-8 text. JSON output is text that
the caller may parse; it is not automatically a structured card response.

### get_image

**Use it to:** actually show a figure, page, mask preview or rendered card sheet to the assistant.

**Inputs:** `workspace`, image `artifact`. **Returns:** an MCP PNG image content
block resized to at most 1600 pixels per side. Needs a valid workspace image;
not a URL or an arbitrary host path.

**Example:** `get_image {"workspace":"WORKSPACE","artifact":"media/IMAGE_preview.png"}`.

**Implementation:** [API.get_image](../src/ankiplusmcp/server.py) base64-encodes bytes
from [Artifacts.image_bytes](../src/ankiplusmcp/artifacts.py). Pillow validates
size, thumbnails and converts to RGB PNG. The original artifact is unchanged.

### get_job

**Use it to:** follow an extraction, figure-export, OCR or rendering operation.

**Inputs:** `workspace`, `job_id`. **Returns:** persistent record with operation,
status, progress, cancellation flag and, when available, `result` or `error`.
Statuses are `queued`, `running`, `completed`, `failed`, `cancelled`, `interrupted`.
Only `completed` means success; inspect `result` for artifact references.

**Example:** `get_job {"workspace":"WORKSPACE","job_id":"JOB"}`.

**Implementation:** [Jobs.get](../src/ankiplusmcp/jobs.py) reads `jobs/<id>.json`.
An owner lease lock distinguishes live work in another process from abandoned
work after a restart; an abandoned queued/running job becomes `interrupted`.
Jobs are not automatically retried. Read the error/remedy before retrying explicitly.

### cancel_job

**Use it to:** request that a long operation stop.

**Inputs:** `workspace`, `job_id`. **Returns:** updated job record; queued/running
jobs get `cancel_requested: true`. Terminal jobs are returned unchanged. Check
`get_job` for the terminal state rather than assuming the request stopped it.

**Example:** `cancel_job {"workspace":"WORKSPACE","job_id":"JOB"}`.

**Implementation:** [Jobs.cancel](../src/ankiplusmcp/jobs.py) persists a cooperative
flag. Native Tesseract/Chromium work is not killed mid-call. Extraction/preview
publication guards preserve current snapshots on cancellation before publication;
a cancellation after committed publication does not roll back completed output.
Some failed/cancelled operations leave cache or staged artifacts.

### measure_usage

**Use it to:** diagnose the model usage of an explicitly supplied Claude Code transcript.
This is optional and unrelated to card quality.

**Inputs:** `workspace`, absolute `transcript` path to a `.jsonl` file under a
readable source root. **Returns:** `format: "claude_code"`, summary lines, and
JSON/Markdown cost artifact IDs. No transcript history is discovered automatically.

**Example:** `measure_usage {"workspace":"WORKSPACE","transcript":"/absolute/lectures/session.jsonl"}`.

**Implementation:** [Sources.measure_usage](../src/ankiplusmcp/sources.py) validates
paths, including matching subagent transcripts/metadata, and adapts the
[cards.meter](../src/cards/meter/__init__.py) CLI-style entry point with an argument
object. It writes under `usage/<id>/` and advances revision. Pricing/token figures
are diagnostics based on the transcript and packaged prices, not billing receipts.

## Card input model

The complete typed contract is [models.py](../src/ankiplusmcp/models.py).
Unknown fields are refused. Local IDs use letters/numbers, underscores and hyphens,
start with a letter or number, and contain at most 80 characters.

| Card field | Meaning and default |
| --- | --- |
| `id` | Required local identifier, unique within the saved set. |
| `fields` | Required mapping of 1–30 field names to strings; arbitrary Anki field names are supported. Each value is at most 20,000 characters. |
| `kind` | `cloze` (default), `basic` or `io`. Choose validation/rendering behaviour. |
| `notetype` | Anki note type; omitted/null is replaced by the active profile's note type. Explicitly set `Basic`, `Image Occlusion`, or your actual model name for non-cloze cards. |
| `deck`, `tags` | Destination deck (`Default` by default) and tag list (empty by default). Tags cannot contain whitespace. |
| `action`, `note_id` | `create` by default; `update` requires an actual positive Anki note ID from the separate Anki MCP. |
| `card_ids` | Actual Anki card IDs, distinct from note IDs; empty by default. Needed to execute suspension safely. |
| `source_ref`, `objective`, `group` | Optional provenance/coverage and figure grouping. `source_ref` is a list of positive slide numbers, default empty. |
| `tier` | Optional 1–3 importance tier. Tier 3 produces suspension intentions in a write plan. |
| `media` | List of `{path, filename}` records. Path is workspace-relative; filename is the destination Anki media name referenced in fields. |
| `question`, `answer` | Optional supplied front/back HTML, supplied together. Takes precedence over generated field-based previews. |

Example of a basic note snapshot intended for an update:

```json
{
  "id": "existing-1",
  "kind": "basic",
  "notetype": "Basic",
  "action": "update",
  "note_id": 1234567890,
  "fields": {"Front": "What does ATP stand for?", "Back": "Adenosine triphosphate"},
  "deck": "Biology",
  "tags": ["revision"],
  "source_ref": [3]
}
```

The note ID above is illustrative. Fetch real note IDs/fields from Anki rather
than inventing them. For cloze previews without explicit templates, the first
field is the primary text and the second, if present, is extra answer content.
Supply templates for other layouts.

## Limits and errors

- At most 500 PDF pages and 500 saved cards per workspace; input files are
  limited to 64 MiB. Pasted text has an additional MCP input limit of 1,000,000 characters.
- Decoded images/rasters are limited to 20 million pixels, with additional
  extraction raster/dimension guards. Reduce PDF page dimensions or export zoom
  when a raster is refused.
- JSON tool responses are bounded to 64,000 characters. Ask for fewer cards or
  use paginated artifacts when a response is too large. Individual schema limits
  may be smaller.
- Workspace IDs are 1–80 letters/numbers/underscores/hyphens. Paths must remain
  within configured source roots or the selected workspace as appropriate.
- `STALE` means re-read and reconcile; `DEPENDENCY` names an installation remedy;
  `LABELS_PENDING` means wait for extraction. `SOURCE`, `PATH`, `LIMIT`, `CARD`,
  `VALIDATION`, `CONFLICT`, `MEDIA` and `UPDATE` identify other common refusals.
- These limits do not constitute a remote sandbox. The server is a local stdio
  process and has no HTTP authentication layer. Only register it in a host you trust.

For configuration precedence and dependency fixes, see [setup](setup.md).
For locking, hashes, jobs and extension guidance, see [developer architecture](developer-guide.md).
