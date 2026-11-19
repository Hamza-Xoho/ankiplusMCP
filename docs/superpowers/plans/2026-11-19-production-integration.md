# Student workflow production integration supplement

Execution: executing-plans, inline. Spec: 2026-11-18-student-workflows-design.md.
Preserves original Tasks 7–10 signatures and existing public MCP contracts.
No live collection, installation, deployment or publication is authorized.

## Verified boundary

Source-derived from companion bcde97d: Tool handlers execute synchronously in
one RequestProcessor main-thread request. collection_identity exposes complete
profile/path/creation binding and runtime session, neither proves uniqueness.
notes_info without excerpt_chars returns complete fields and typed card ownership.
add_note, update_note_fields, card_unsuspend and store_media_file(data=...) are
existing primitives. read_media_file returns bounded exact bytes. Linux memory
transport evidence is not HTTP/Qt or Mac acceptance.

## 1. Conditional companion dispatch (first executable dependency)

Add student_operation_state(operation, arguments) and
conditional_student_operation(operation, arguments, expected_state). Allowed
operations: add_note, update_note_fields (full fields only), card_unsuspend,
store_media_file (bytes only). No dynamic registry forwarding. State contains
version, exact arguments, complete profile binding/session, complete affected
notes/cards/models/decks or exact media hash/absence. Reject incomplete binding,
unknown keys, excessive batches and changed state. Compare and invoke fixed
primitive in the same synchronous handler without yielding. This prevents queued
profile/target changes, not unobservable file replacement or external processes.
No authorization is inferred from state: primary must separately bind reviewed
proposal/config/quality and journal intent.

Tests: registry discovery, stale session, changed fields and sibling card state,
unknown operations/path media, duplicate rejection and unchanged dispatch. Run
companion unit suite and standalone no-network synthetic packaged collection test.

## 2. Production adapter and coverage

AnkiAdapter uses an explicit MCP ClientSession, never arbitrary forwarding. Typed
identity requires explicitly selected profile and complete runtime session.
Bound search pages; reject incomplete note/card ownership and truncation; cap
complete search rather than claiming completeness on overflow. Conditional writes
consume exact state from step 1. Surface missing capability as UNSUPPORTED.
Tests use synthetic transport only; engine network boundary remains intact.

## 3. Coordinator and real product path

Coordinator stage/authorize/apply/reconcile retain original signatures. Immutable
proposal snapshots bind request fields, sources, targets, media hashes, relevant
config and quality evidence. Durable intent precedes every send. Timeout after
send is uncertain; known-ID readback may reconcile, inconclusive create never
resends. MCP facade wires these operations to RunStore/ConfigStore and adapter.
Tests cover digest edits, quality refusal, per-item partial outcomes and restart.

## 4. Review and onboarding

Use proven SDK UI metadata/bridge from versioned Desktop experiment with explicit
run/workspace/session/revision. Source-linked review edits/exclusions invalidate
approval and affected quality evidence; existing text editing defaults to new draft.
Onboarding persists verified milestones, preserves preferences and generates the
existing tailored guide. No completion based on caller assertions alone.
Apply impeccable and accessible responsive review tests. Mac embedding and
prescribed private reviewers remain external gates, never synthetic passes.

## Review focus

Stale queued writes; missing/truncated ownership; media collision/renaming;
uncertain create restart; forged/stale review or configuration decisions. Each
belongs to its corresponding failed-first tests. Finish with one fresh branch
review and one regression-tested material fix pass, not per-task reviewers.

## Concrete adapter write interface supplement

The original domain method names remain. Each write receives exact expected
state captured during staging; no method may silently refresh it at application.
`store_media(media)`, `create_notes(batch)` and `update_note(change)` consume
an envelope `{arguments, expected_state}` (batch is 1–100 such envelopes).
`set_suspended(card_ids, suspended, *, expected_state)` selects only the two
fixed card primitives. Methods return per-operation companion envelopes; they
make no product authorization or confirmed-readback claim. Sequential batch
results preserve prior acknowledgements and stop on uncertainty; the coordinator
uses single-item batches and journals each send independently.

Before writes, validate complete fields, required template components and CSS
against the captured model, not a model name alone. Unsupported/empty/malformed
model metadata fails closed. Tests: partial fields and nonmatching model/style
refuse; fixed suspension mapping; no arbitrary dispatch; batch partial results.
Expected: focused adapter tests pass, then full check-mcp and frozen CLI checks.

## Durable workflow interface supplement (resume)

`Coordinator(service)` owns RunStore/ConfigStore under `.student-workflows` and
uses only `service.companion_connection`. `start(workspace, pages)` captures source
selection; `coverage(run_id, query, decisions)` scopes balanced Anki query syntax
to saved deck names/IDs plus the configured generated-card tag namespace, records
full coherent note/card snapshots and normalized EvidenceResolver decisions.
Prior confirmed mappings are reread before reuse. Earlier unresolved intents in
this collection block new coverage/staging until reconciliation.

`stage(run_id)` is async and captures conditional states into immutable Proposal
snapshots; `authorize(run_id, digest, mode)` is synchronous, rereads all local
inputs and quality bindings, and records either human or explicit saved-policy
authorization. Stage/apply/reconcile use dedicated nonblocking cross-process locks.
Proposal content binds selected drafts, decisions, source selection/evidence,
media content, relevant preference values and fixed operation requests/states.
Quality receipts bind the content digest; proposal digest additionally binds the
accepted receipts. Missing/failed/stale host execution evidence refuses authorize.
No public input can mark a quality result independently verified.

Per-operation immutable intent is fsynced before dispatch. Acknowledgements and
readback outcomes are separate cumulative events. Creates journal their returned
note identity before any readback; tier3 suspension resolves actual generated card
IDs after fields/media verification. Intent without a known identity remains
uncertain after restart; known IDs permit bounded readback only. No create search
can by itself manufacture provenance or trigger a resend. Tests cover these
interfaces with real stores, source extraction and transport-only synthetic Anki.
