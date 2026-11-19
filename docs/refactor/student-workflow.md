# Connected student workflow

The launcher's explicit companion URL/profile/collection-path options configure
one loopback connection. No automatic companion discovery, generic proxy, public
endpoint or networking in the cards engine is provided. Source-only tools work
without that connection. Runtime host configuration and real collections require
separate acceptance authorization.

## Setup and a first run

`get_student_setup` resumes verified milestones. `get_collection_choices` lists
own and premade decks without mutations. `propose_student_setup` shows complete
choices, plain preference differences and the data folder. Explicitly confirm even
when keeping defaults. `confirm_preferences` saves lasting choices; separate
propose/confirm_run_preferences affect only the named run. Source-folder revocation
also revokes runtime access. On restart confirmed roots remain authoritative, including an empty list;
registration flags/environment seed unconfirmed setup only. Unrelated host settings and guide personal notes are retained.

Required milestones are explicit preferences, durable storage readback, actual
companion/model checks, observed installed App interaction/reconnect, actual
quality runtime evidence, and generated guide. Caller booleans cannot complete
them. Changing the installed review resource invalidates its observed milestone.

Create a workspace, extract the chosen source and inspect cited pages/figures.
Draft with the unchanged selection/design/combination/house-style/tier/tag rules.
Start a student run for the exact source hash and pages. Record coverage with
concept IDs, local draft IDs and EvidenceRef passages. Search wraps the query in
selected decks and the generated tag namespace; previously verified generated
identities are also reread. Overflow refuses rather than claiming complete hits.
Semantic coverage remains a host judgement. Uncertainty defaults to pending;
source contradictions persist for the same concept/source version across citation edits,
pages and reruns until explicit resolution.

Stage captures exact requests, profile/runtime binding, targets, full fields,
models/templates/CSS, card backend state, source, media bytes, relevant effective
and saved configuration, quality-policy files and installed review resource.
Existing-note updates require a separately selected explicit update. Conditional
media uploads use supplied bytes only; conflicting existing names refuse.

## Review, quality and permission

`open_run_review` serves the packaged ext-apps 2.0.4 App. It pages through actual
run state, source passages, viewable cited PDF pages and existing candidates; local decisions survive
reconnect. Unsaved edits block approval/paging/recheck, while a pending save locks
editing; unchanged Keep preserves the exact quality/proposal binding. Application
status includes pending decisions and unsent operations. Shortened fields must be completely loaded before editing. PDF images are read through a session/digest/concept/reference-bound App tool, never an arbitrary supplied file or page. Stale
proposal/session tokens refuse, and changes invalidate affected quality and
approval. The App displays source disagreement, technical and reviewer findings.
Existing-note field editing defaults to a new adapted draft.

Both required reviewer roles consume immutable packets with the unchanged briefs,
rubrics and report format, actual captured supported templates/CSS, media and
source evidence. Image-only PDF references include real cited page images.
Student backs stay withheld until every exact front attempt is durably committed.
The receipt validator binds execution identity, prescribed model/effort, launch
controls, file hashes/read order, turns, attempts and report to proposal content.
Failed or late reports cannot authorize. Packet/report modification revokes use.

`verify-host-evidence` is an operator/supervisor import boundary outside MCP. It
signs only normalized observed execution exports with the required controls and
validates them before retention. It cannot authenticate a dishonest local
operator or invent host capabilities. It must not be used to sign author-created
PASS assertions. Synthetic fixtures deliberately sign test exports only inside
disposable test data; they establish local enforcement, not independent quality.

User approval and saved automatic authorization are separate from quality.
Automatic mode skips the student's interactive approval only when explicitly
saved; it never skips quality. The local stdio host is trusted to present actual
user approval/preference confirmation. App-only tool visibility is host-enforced,
not cryptographic proof of a human click. A direct low-level companion call does
not acquire AnkiPlus authorization from conditional state alone.

## Application and recovery

Before each conditional send, the exact intent is fsynced. The acknowledgement is
saved separately before readback. Writes compare exact state synchronously in the
companion main-thread handler. This is a conditional operation, not a distributed
transaction or a persistent collection-uniqueness guarantee.

Readback verifies fields, full note/card ownership, model/templates/style, tags,
creation deck, referenced media and suspension state. Tier-3 followup uses real
generated card IDs and the complete verified generated state. A foreign change
between create readback and followup refuses. Existing tier-1/2 scheduling is not
silently reset; the retained policy suspends tier 3 and explicit coverage actions
unsuspend selected card IDs. Tags are preserved on explicit field updates.

Failures before dispatch are `failed` with `delivery=not_sent`; possible sends
remain `uncertain`. Confirmed, unchanged, failed, conflict and uncertain results
accumulate per operation, including separate tier failures. Remaining work is not
flattened into success. No-op runs perform readback of already-covered decisions
without write authorization or quality receipts; they cannot send mutations.
Pending and excluded decision counts remain visible.

Restart reconstructs intent, acknowledgement and results from permanent events.
Reconciliation is read-only. Known create acknowledgements can establish actual
identity and restore verified mappings. Missing create acknowledgements remain
uncertain even if a search finds similar content. No batch retry, blind create
resend, destructive rollback, deletion or automatic history pruning exists.

## History, concurrency and cleanup

Run journals live under `<workspace-root>/.student-workflows`; SQLite search is
rebuildable. MCP list_student_runs/get_run_history/get_run_results provide bounded
pages; read_run_record slices exact immutable JSON. The separate CLI discovers
this root with `ankiplusmcp history --workspace-root <workspace-root>`. Use
`--journal-root` to inspect an older standalone journal without migrating it.

Workspace, configuration, run and collection locks prevent overlapping local
publication and sends. Native OCR/render work uses captured inputs and short
publication locks; stale/cancelled results refuse publication. Job shutdown
requests cancellation, cancels queued futures and waits at most two seconds in
its API. Active callbacks retain the owner lease until stopping. Python process
exit may still wait at a native boundary; OCR subprocess calls have a 30-second
limit. This is cooperative cancellation, not forcible native-thread termination.

Explicit cleanup previews only reproducible workspace previews. A digest-confirmed
apply saves the deletion manifest first and refuses active jobs or changed files.
Sources, drafts, referenced media, collection-media copies, reviews, jobs, quality
packets, run journals and receipts remain. Abandoned source extraction directories
and journal temporary evidence are retained for inspection, never guessed safe.

## Acceptance boundary

The known observed Mac host lacks launch-level cumulative turn/tool controls;
same-reviewer continuation within six cumulative turns is unproven. Another alias
does not establish either capability. The importer cannot cure this, and no
additional exploratory reviewer launch is part of Linux implementation. Actual
prescribed reviewers, embedding, private fixtures, production note types and real
Mac lifecycle/collection behavior remain acceptance gates. Do not weaken them.

## Supported rendering and bounded operations

The ordinary saved card profile can share a run with canonical native Image
Occlusion. Existing/update reviews use actual model semantics and retained note
tags. Native IO uses fractional rectangle masks in a phone-contained image without changing
source bytes or mask resolution; unsupported variants refuse.
Unimplemented template metadata/filters refuse rather than render empty evidence.
CSS-loaded resources (including inline/import/escaped forms) refuse before a
dispatchable companion state or a quality render. Supply supported image fields
instead; absent assets never become an accepted empty background.

Quality preflight counts full cloze/template expansion and packet files before
allocation. Source packet limit is 250 files/128 MiB; expanded HTML/media and
image dimensions have additional bounds. Actual Chromium layout is bounded before
screenshot allocation (390px wide, 12,000px height per side, 24 million aggregate
pixels). Narrow or resize selections when refused; no silent sample replaces the
complete selected review. Suspension requests are partitioned at staging so
already-active cards are readback-unchanged, never counted as newly unsuspended.
