# Compatibility follow-up implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Work inline. No implementer subagents or routine per-task reviews.

**Goal:** Close the remaining Task 3 evidence gaps, then specify original Tasks
7–10 using established contracts rather than inferred companion behavior.

**Architecture:** Keep raw evidence ignored; version only sanitized findings and
procedures. Separate read-only existing-record inspection, offline fault rehearsal,
new isolated collection experiments, and production implementation. No current
result authorizes the next category automatically.

**Tech Stack:** Existing Python/Pydantic/MCP and dependency-free Node launcher;
reported Mac companion FastMCP streamable HTTP. Wire names, exact result parsing,
identity/media mechanisms and final UI/runtime handoff remain conditional.

**Spec:** `../specs/2026-11-18-student-workflows-design.md`.
**Evidence:** `../../refactor/macos-evidence-assessment.md`.

## Global constraints

- Preserve selection/design/rubrics/tiering/tags/rendering, public contracts and history.
- Keep `.codex/`, `.agents/` and existing `.claude/` instructions frozen. Never bypass a hook using another tool or transport.
- Keep both response channels and historical failures. Do not repeat passed A–D/UI checks or request skipped historical error text.
- No collection tool calls, profile changes, key changes, restarts, new registration or cleanup under this plan's read-only stage.
- Staged reviewer experiment requires the explicit decision in Task 2; new collection experiments require their own exact authorization packet.
- Do not remove missing identity/media/quality requirements to unblock shipping.

## Review focus

- Equal numerical note/card IDs: preserve typed units and ownership, never require inequality.
- Cross-deck duplicates and partial batches: retain indexed accepted/skipped/failed items without whole-batch retry.
- Profile switches between review and send: lack of a proven collection identity blocks apply, even with a familiar media path.
- Changed note fields, open browser edits and truncated readback: never overwrite from an excerpt or treat a receipt as verified fields.
- Lost create acknowledgement: preserve durable intent and uncertainty; no automatic create retry from an empty or incomplete search.

## Task 1: Complete existing-record metadata evidence (read-only, can run now)

**Files:** Mac ignored evidence directory only: `METADATA-CLOSURE.md`,
`host-metadata.json`, `CAPABILITY-BLOCKERS.md`, updated `SHA256SUMS.txt`.
**Interfaces:** Produces sanitized observed wire names/input schemas, original raw
response shapes, build provenance and identity/media capability disposition.
No invented `collection_identity` endpoint or note-to-card tool is produced.

- [ ] Verify Darwin and access to the existing worktree/probe evidence before any work. If not local, stop rather than regenerate reports in the cloud.
- [ ] Reuse original transcript/log records: extract original ToolSearch metadata, existing initialize/serverInfo/tools-list responses if present, and exact A–C call/result blocks. Preserve distinction between original bytes and redacted/normalized views with separate hashes. Do not re-query collection tools.
- [ ] If handshake records do not exist, mark not_captured. Do not issue a blocked shell request through another tool. Metadata-only host diagnostics may be used only through an already permitted route; if a guard rejects it, retain the rejection and stop that action.
- [ ] Hash relevant installed add-on source/manifest files without modifying them. Inspect registration precedence, endpoint path and canonical wire names in existing initialization/source metadata; record source-derived versus live-observed fields separately.
- [ ] Inspect installed source/resource declarations for stable profile AND collection identity, media byte retrieval, full note/card/CSS reads and pagination/completeness. Do not execute those operations. Output exact operation/resource declarations if present, otherwise an explicit missing capability. Source inspection is not behavioral acceptance.
- [ ] Record update preconditions from implementation, including editor/browser behavior and patch transport. Do not turn a warning into an unsupported automatic retry policy.
- [ ] Return actual sanitized results and hashes, not another summary of these instructions. Do not rerun completed reviewers to explain a selection-metadata field when per-request values already establish the reported model/effort.

**Expected:** New record distinguishes available original captures, source-derived
capabilities and missing operations. Zero collection operations and no guard bypass.
A required unsupported identity/media capability remains an explicit blocker; it
requires a narrow companion enhancement or an owner-approved architecture decision,
not an invented fallback. No secret is requested or copied into public artifacts.

## Task 2: Proposed staged student experiment (decision required; not executed)

**Files if approved:** A NEW ignored synthetic packet and supplemental student
alias, `STAGED-PROTOCOL.md`, `front-attempts.json`, final report and invocation trace.
**Consumes:** Existing synthetic sheet fixture and unchanged rubric/report format.
**Produces:** Evidence of front-only exposure → durable attempts → back inspection,
not a retroactive pass for the original parallel packet.

The conflict is concrete: frozen student step 2 and shared PROMPT ask for all
images together, while the brief asks for an answer before backs. This cannot be
resolved by reinterpreting the existing transcript. A supplemental experiment
must explicitly change its disposable image-delivery protocol; shipped/frozen
instructions are not edited. This does not authorize a production quality-policy
change or more lenient verdicts.

- [ ] Owner decision: approve a disposable staged-image experiment with the same synthetic fixture, Sonnet 5.5/medium, maxTurns 6, same body except the explicitly documented exposure-protocol override, same rubric and final report format. No Anki tools. Do not rerun maintainer.
- [ ] Create a new experiment directory without touching existing packets. Record all body/envelope differences and fixture hashes. Do not pass author conversation, answer key or prior reports to the student.
- [ ] The supplemental alias's stage-1 instructions permit reading only its brief/rubric/protocol, front-only manifest and front PNGs. It writes `front-attempts.json` with every tile ID and an answer or `don't know`. It must not inspect backs or back-bearing card data before that write.
- [ ] The front manifest lists only fronts. Keep back paths/data out of the stage-1 packet and context. The supervising harness releases/copies backs into the packet only after validating complete attempts, hashing and durably preserving them. Do not assume an unverified host resume API: first inspect available host continuation support; if no same-reviewer continuation/release mechanism is available, mark this experiment blocked and propose the exact supported alternative before execution.
- [ ] The same reviewer then reads each back once and writes the unchanged final report, referring to the committed answers. Do not accept rewritten attempts. Inspect the actual read/write/continuation trace and per-request model/effort.
- [ ] Pass criteria: every front read/attempt is before any back exposure, every listed image inspected once, attempt-file hash unchanged, no answer-key/other-report reads, no increased turn budget or weakened rubric. A seeded-defect verdict is diagnostic, not a representative quality pass.

**Expected:** A verifiable staged exposure sequence or a precise host limitation.
Do not fabricate blind recall from simultaneous reads. Further production adoption
and representative source-to-card A/B acceptance remain separately required.

## Task 3: Design local fault harness before live E/F (no collection permission)

**Candidate files after a concrete interface is established:** test-only
`tests/mcp/fakes/companion_transport.py`, fault scenarios and ignored fault traces.
**Interfaces to preserve:** original `Coordinator.stage/authorize/apply/reconcile`
and `AnkiAdapter` responsibility names remain the approved domain API. Exact wire
mapping and parser implementations are not authorized until Task 1 resolves them.

Define a test-only transport boundary around a fixed allowlist, not arbitrary
MCP forwarding. Its fault switches are outside production and never disable
quality/authorization guards. Tests are written RED before implementation.

| Scenario/test | Exact fault and expected behavior | Real collection calls |
| --- | --- | --- |
| `test_intent_without_dispatch_is_not_success` | Durable operation intent saved; transport fails before forwarding. Record not_sent/failed, no fabricated acknowledgement | 0 |
| `test_acceptance_then_lost_receipt_never_blindly_resends` | Fake companion accepts exactly one indexed create; suppress delivery before the local receipt is saved; restart local coordinator. One create dispatch total, uncertain journal survives, only bounded reads may reconcile | 0 |
| `test_missing_or_ambiguous_readback_keeps_uncertain` | Recovery reads return zero, duplicate, incomplete or mismatching candidates. Do not call create again or promote a sort-field duplicate to confirmed ownership | 0 |
| `test_partial_batch_reconciles_per_index` | Replay captured D shape (one created/one skipped/one failed); record each separately; no whole-batch retry, no treating skipped as verified success | 0 |
| `test_unavailable_auth_and_identity_fail_closed` | Fake transport returns connection error, 401, then identity token change between stage and pre-send. No write on preflight failure; no key edits; keep staged proposal and expose typed errors | 0 |
| `test_equal_ids_keep_note_card_units` | Fixture has equal note/card integers plus another note with two different card IDs. Suspension consumes selected `cid` values only | 0 |

These prove local enforcement only, not real companion identity or acceptance.
Do not count a fake response as real Anki evidence or run a mock script instead
of implementing the coordinator under original Task 8.

### Exact future live-E envelope (BLOCKED, not executable now)

A new isolated synthetic run would contain one note and two cloze cards, retained
afterward. It uses the existing verified stock type for recovery mechanics only;
ColdRecall/type acceptance is separate. Example fixed namespace:
`APLUS-E-20261119-01`; deck `ZZ-APLUS-E-20261119-01`;
tag `APLUS_E_20261119_01` (no existing production tags are changed).
Refuse if any marker/deck already exists. A new run needs new approved names;
never reuse a partially completed envelope.

Candidate calls use captured HOST aliases, not assumed wire names:

1. At most two identity reads, immediately before target setup and immediately
   before create. **BLOCKED:** exact collection/profile identity operation is absent.
2. `find_notes({"query":"tag:APLUS_E_20261119_01","limit":2,"offset":0,"include_first_field":false})`; expect zero. This alone cannot prove an absent deck or correct profile.
3. `list_decks({"include_stats":false})`; require the exact target deck absent.
4. `model_field_names({"model_name":"Cloze"})`; require the exact Text/Back Extra field contract.
5. `create_deck({"deck_name":"ZZ-APLUS-E-20261119-01"})`, once.
6. Persist full approved operation intent and fsync before exactly ONE
   `add_note({"deck_name":"ZZ-APLUS-E-20261119-01","model_name":"Cloze","fields":{"Text":"APLUS-E-20261119-01 {{c1::alpha}} then {{c2::beta}}","Back Extra":"Isolated receipt-loss experiment"},"tags":["APLUS_E_20261119_01"],"allow_duplicate":false})`.
7. Fault point: local wrapper has received the successful upstream response but
   terminates BEFORE delivery to coordinator/receipt publication. An ignored
   verifier trace retains actual acceptance evidence, isolated from coordinator
   recovery input. Do not kill Anki. **BLOCKED:** exact permitted local wrapper/
   connection topology, guard compatibility and raw success parsing remain unset.
8. Restart ONLY the local experimental process, once. Recover durable intent.
   One `find_notes` with the same query/limit; if exactly one candidate, one
   `notes_info({"notes":[<returned note ID>]})` with no excerpts, and one
   `cards_stats({"deck":"ZZ-APLUS-E-20261119-01","limit":10,"offset":0})`.
   Compare exact fields, tags, model, bound identity and actual note/card ownership.
   If anything is missing/ambiguous/incomplete, stop as uncertain, no create retry.

Hard upper bound: 10 remote calls including the two identity reads, one create
attempt, one optional readback sequence, zero updates/suspension/deletion/media/
sync/profile switches. No cleanup is included. An exact identity/transport/parser
blocker must be resolved before requesting authorization. Already-deleted A/D
notes must not be reused as future targets.

### Future live-F boundaries (BLOCKED, not executable now)

Offline tests above need neither Anki shutdown nor key rotation. An eventual
integration failure packet must separately specify a permit-compliant LOCAL
transport shim, exact endpoint isolation and identity reads before approval.
For unavailable/auth failures, the shim refuses before forwarding any mutation;
use a transient invalid request credential only if explicitly authorized, never
change the saved real key or registrations. For identity change, replay a changed
identity in the local harness first; a real collection switch requires separate
owner authorization and valid identity capability. No destructive rollback or
profile switch is currently proposed for execution. Offline F cannot close the
real changed-collection acceptance requirement.

## Task 4: Write and execute the production integration supplement

**Files:** A concrete follow-up to original Tasks 7–10, preserving their public
domain signatures. Exact runtime/UI/transport files are selected ONLY after
Tasks 1–3's applicable capability and quality decisions settle.

- [ ] Specify connection topology including Desktop stdio/product → fixed local companion HTTP, canonical names, auth injection without logged credentials, initialization/capability checks, bounded errors and absent outputSchema handling. Do not assume the mechanical network-disabled container can reach the companion.
- [ ] Map search/read/card ownership/type/media operations from actual evidence, including pagination and byte verification. Missing identity/media mechanisms need a narrow supported extension or explicit architecture decision; no claim of verified mutation until solved.
- [ ] Specify digest-bound staging, explicit human/config authorization, affected quality reruns, durable intent-before-send, indexed outcomes, fresh readback and uncertainty reconciliation. Bind actual identity and preserve card-selection/tag rules; do not invent idempotency from a duplicate-skip response.
- [ ] Specify production MCP-App session/run binding and edit/exclude/approve callbacks from actual Apps SDK/host evidence. Independent synthetic UI and reviewer successes are not proof of their production handoff.
- [ ] Finish configuration/onboarding/guide milestones, remaining required audit fixes and acceptance. Keep original historical snapshots and public APIs. Apply TDD, frontend/accessibility and verification skills when implementation begins.

**Expected:** An implementable supplement with exact tests/interfaces and evidence
for every required capability; no silent fallback to text-only UI or weaker
reviewers. Only then resume the original remaining tasks. Full release still
requires independent representative/private quality, novice-guide and real-Mac
end-to-end scenarios, exact changed-collection refusal, interrupted writes and
all required audit dispositions/checks. No publishing/deployment is authorized.

## Self-review / handoff

This plan retains all unresolved capabilities instead of inventing endpoints.
Tasks 1 and 2 do not execute collection operations. Task 3 separates local faults
from the explicitly BLOCKED future live envelope. Task 4 does not authorize a
speculative production wire contract. The only immediate policy decision is
whether to approve Task 2's disposable staged-image protocol; formal collection
execution authorization must wait for resolved identity/transport/readback details.
