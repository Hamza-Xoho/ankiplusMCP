# Close reviewer provenance and companion identity

Use the existing Local Code session on the existing probe folder, Worktree off.
Read-only investigation and evidence preparation only: zero Anki collection tool
calls, no profile changes, no reviewer reruns unless a specific missing check is
identified, and no changes to frozen files or production interfaces. The owner
should not need more clicks for the passed sample UI tests.

## Preserve the current UI results

The latest owner-pasted Mac report confirms Code save/readback at revision 4 with
sample-a `code-test-save` selected and sample-b excluded, then matching fresh-Code
display/readback after a full Desktop restart. It also reports Reload passed.
Reuse these results alongside the existing Chat tests. Raw Mac evidence should
retain the screenshots/readback references, actual server/bundle hashes, app
6.6395.1/bundled runtime and source provenance rather than relying on this summary.

The old revision-3 transition remains unattributed because the probe log omitted
arguments/timestamps. Its save-call count includes rejected stale requests and
must not be treated as a successful-write count. Preserve that historical gap;
do not invent a cause or require the owner to reconstruct it from memory. The
observed Code transition 3→4 is a separate, verified report. This probe limitation
is not an acceptance test of production history or interrupted collection writes.

Keep original artifact-generation revisions (including `bfca2ab`) as history.
Record the latest checkout revision, actual generated-server hash and per-check
origin separately; do not rewrite historical source fields to the latest HEAD.
The owner's skipped historical Code error text stays uncaptured. Retain previous
UI restore/delayed-feedback limitations and both response channels.

## Audit the two existing reviewer executions

Read the round-1 summary, actual reports and existing invocation/subagent
transcripts for the reported `compat-maintainer` and `compat-student` agent IDs.
Both reported `PASS_WITH_FIXES`: the maintainer detected the seeded source
contradiction; the student flagged identical fronts. Findings are expected
diagnostic output, not permission to change the fixture or claim quality passed.

For each role, return the actual evidence for:

- Agent identity and report hash matched to its invocation; exact initial input
  limited to its own packet path, with no author history/other report/answer key.
- Actual runtime model from execution metadata, distinguished from the model
  declared in the agent file. Inspect available initialization/request metadata
  for actual effort; leave it unverified if the runtime did not retain it.
- All reads and writes scoped to the allowed packet/report. Compare the student
  transcript's actual image reads with every sheet listed in `sheets.json`.
- Unchanged instruction-body/template hashes and original turn limits.

Do not rerun completed reviewers merely because their summary was incomplete.
If a material evidence item cannot be recovered, state exactly what is missing
and prepare the smallest evidence-producing follow-up; do not substitute assumed
settings, main-agent review or fabricated transcripts. The parallel front/back
packet's blind-recall limitation stays unverified pending an explicit staged-image
decision; source/read/provenance audit does not resolve that limitation.

## Identify the actual companion connection

Installed candidates reported so far are Anki MCP Server (add-on folder
`124672614`, version missing from manifest) and ColdRecall macOS arm64 dev
`0.1.0-dev`, build receipt revision `98cb93ac`. Installation does not identify
which serves the connected `mcp__anki__*` namespace.

Trace the effective `anki` registration in Desktop/Code, including precedence,
configured executable/arguments or local address, and existing MCP initialization
metadata/serverInfo. Compare those with installed add-on startup/binding metadata
and relevant existing logs. Read installed metadata/source only as needed; access
no collection database and invoke no collection tools. Keep credentials and whole
host configs out of summaries. Report authentication mechanism without its secret.

Produce a sanitized chain from active registration to process/transport to
add-on/build identity. A metadata protocol discovery can establish advertised
schemas, not actual note/card/media behavior. If attribution remains ambiguous,
keep the adapter gate blocked with the precise missing link. Do not choose an
add-on by name or alter registrations to make the ambiguity disappear.

Attach actual advertised input/result schemas and map exact operations for
collection/profile identity, note search/read, card IDs/readback, note types,
media, create/update, suspension, duplicates and partial results. Mark unsupported,
documented-only and unexecuted capabilities separately.

## Make the future isolated-profile plan reviewable

The previous add/read/suspend/unsuspend/delete outline is not full compatibility
acceptance. Prepare a concrete, bounded plan using only the identified companion's
actual schemas. No operation below is authorized for execution in this stage.

Specify the isolated profile and how its collection identity will be verified
before mutations; unique synthetic deck/note-type/run markers; exact payloads,
operation counts and expected evidence; and hard refusal on an unexpected profile
or target. Cover these required cases, or label the precise capability blocker:

1. Synthetic note creation and readback, including multiple cloze cards per note,
   actual note/card ID distinction and verified suspension state for selected IDs.
2. Explicit note update and readback without touching unrelated notes or templates.
3. Synthetic media input and receipt/readback semantics.
4. Controlled duplicate behavior and a partial batch containing a deliberately
   invalid synthetic item, with per-item results and readback of any accepted items.
5. Interruption after acceptance but before local receipt: a concrete fault point,
   durable local intent and readback/reconciliation method. No blind resend of an
   uncertain create. Missing evidence leaves the operation uncertain, not retried.
6. Unavailable/authentication/changed-collection failure boundaries and recovery
   behavior, with all mutations bounded to this isolated synthetic scope.

A deliberate duplicate experiment must be distinguished from an automatic retry
of an uncertain write. A blanket stop-on-error test cannot demonstrate partial
acceptance or interrupted-write recovery; define bounded observation/reconciliation
for those expected failures. Keep cleanup as a separate optional action after
evidence is saved, using exact verified IDs owned by that test run and explicit
deletion authorization. Retaining synthetic notes for inspection is acceptable.

Prepare this operation list completely before requesting its separate execution
authorization. Do not ask a blanket approval question around unknown endpoints,
profiles or payloads. Discovery and this plan do not prove the still-unimplemented
production approval/coordinator enforcement or representative card quality.

## Return a single concise result

Update the Mac evidence files cumulatively. Return: UI tests preserved; per-role
reviewer proof and remaining gaps; active companion attribution and capability
matrix; the bounded proposed operation list with explicit blockers; and exact
artifact paths/hashes. Keep blind recall, channel uncertainty, private quality and
production integration outstanding where unverified. Do not repeat passed UI
checks or request the skipped historical error text.
