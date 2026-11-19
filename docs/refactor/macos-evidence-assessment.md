# Assessment of the received Mac evidence

Received 2026-11-19 against source `f795b56`. This is a cumulative assessment,
not completion of original Task 3 or a release decision. Seven user-supplied
attachments were read locally. Raw files are retained only under ignored
`.artifacts/compatibility-received/20261119/`; no credentials, host configuration,
private transcripts or raw attachments are included in Git.

## What was independently checked here

- All four original companion evidence files match their supplied SHA-256 entries:
  attribution/proposal, cumulative summary, schema metadata and isolated results.
- The two shareable variants only redact the session-transcript/config paths.
  Their hashes appropriately differ from the originals.
- Nine repository originals (two agents, six role templates and shared PROMPT)
  match the manifest. Both original instruction-body hashes also match.
- The schema file is valid JSON with 22 unique tool aliases, internally valid
  required-parameter lists, and zero advertised formal output schemas.
- Local receipt: `local-audit.json` in the ignored evidence directory. Its hashes
  identify the received bytes, not independent authenticity of the Mac execution.

The Mac reviewer transcripts, original ToolSearch responses, generated agent
files, live MCP handshake and installed add-on build were NOT attached. Their
execution/content claims below are supplied evidence, not directly replayed here.

## Cumulative status

| Area | Supported by received evidence | Remaining limit |
| --- | --- | --- |
| UI and installer | Previously reported lifecycle and synthetic Chat/Code save/reload/restart/stale-recovery results preserved | Not production review or combined source-to-collection acceptance; prior feedback/restore limitations remain |
| Reviewer execution | Summary reports per-request Sonnet 5.5, maintainer high/student medium; packet-only initial inputs; unchanged bodies/templates; turn limits 14/6; student read both images of the only sheet | Raw execution transcripts not attached; report findings are diagnostic, not quality passes |
| Reviewer model discrepancy | Request parameters are the strongest supplied evidence; do not replace them with a guessed interpretation of `pickedEffortModel` | The Haiku metadata field remains unexplained; that alone does not require rerunning completed reviewers |
| Blind recall | Original student brief wants front answers before backs | Agent step 2 and shared PROMPT request all images together. Timing cannot be proven; explicit staged-experiment decision required |
| Companion attribution | Config/listener/source chain points to Anki MCP Server add-on 0.41.1; FastMCP streamable HTTP and Bearer auth reported; ColdRecall dev not the reported listener | No live serverInfo, add-on build hash or proven canonical wire tool names. Host aliases are not automatically MCP wire names |
| Collection identity | Synthetic profile reported from media-directory path and owner selection; initially Default-only | A path is corroboration, not a durable collection identity or detection of switching away and back/copying a collection. No usable identity operation captured |
| A: cloze/card state | One stock-Cloze note, two actual card IDs; only selected c1 suspended, sibling c2 unchanged | Unsuspend not exercised; no production ColdRecall template validation |
| B: update | One Back Extra patch, Text and card IDs reportedly unchanged | A–C payload/results reconstructed. Raw output parser shapes unavailable; full-replace/media-bearing update not proved |
| C: media | PNG storage response and filename listing; unsupported text extension rejected | No byte-content readback or advertised retrieval operation |
| D: duplicate/partial batch | Embedded raw excerpts show one created, one skipped duplicate, one failed required-field item, with indexes and IDs | Full batch input not attached. Observed behavior is not a universal duplicate/idempotency contract |
| D: equal IDs | Raw `cid` and `nid` have equal numbers for one record; A has distinct IDs | Preserve typed identities. Equality alone is not a defect; numerical inequality must never be an adapter validation rule |
| Cleanup | Appended record preserves pre-cleanup history: two notes/three cards deleted; PNG moved to trash; two empty decks retained; no sync reported | Do not repeat cleanup or imply trashed media was permanently erased |
| E/F | Not run | Require bounded fault plans. Killing Anki or changing its real key is not the only way to test local failure handling |

The earlier zero-operation statements describe the discovery stage only. A later,
separately authorized Mac synthetic run reports about 20 collection calls plus
cleanup. This Linux evidence assessment performed zero Anki operations.

## Contract findings from the supplied metadata

This is a candidate mapping, not a frozen production wire contract:

| Required adapter responsibility | Captured host alias and input | Evidence / limitation |
| --- | --- | --- |
| Search | `find_notes(query, limit, offset, include_first_field)` | Described bound 500; actual response shape needs original capture; excerpts identify notes and must not be written back |
| Read notes | `notes_info(notes, include_fields, exclude_fields, excerpt_chars)` | Full values require no excerpt limit; optional parameter types partly omitted |
| Read cards | `cards_stats(deck, limit, offset)` | Deck-wide, subdecks included, ordered by card ID; described bound 1000. No by-card-ID operation. Exhaust authorized deck pages and filter typed IDs; never substitute note IDs or assume first-page completeness |
| Read type/templates | `model_names`, `model_field_names(model_name)`, `model_templates(model_name)` | Model/source CSS availability must be established; stock type is not the product type |
| Create | `add_note(deck_name, model_name, fields, tags, allow_duplicate)` / `add_notes(deck_name, model_name, notes, tags, allow_duplicate)` | Individual indexed batch outcomes observed; atomic undo is not an all-or-nothing transaction; do not resend whole partial batches |
| Explicit update | `update_note_fields(id, fields)` OR `(id, field_name, old_str, new_str)` | Mutually exclusive modes; patch must match exactly once. Metadata warns about open Anki-browser notes and JSON-like snippet transport. Verify full actual fields after updating; no automatic overwrite/retry |
| Media | `store_media_file(filename, data)` | Restrict candidate adapter to provided bytes, not arbitrary path/URL forwarding. Listing does not verify bytes; safe content readback remains a blocker |
| Card state | `card_suspend(card_ids)`, `card_unsuspend(card_ids)` | Suspend observed; unsuspend advertised only. Counts alone do not prove actual final card state |
| Identity/auth | No collection identity operation captured | Freshness, profile/collection binding and supported identity readback must be established before mutation |

Absence of formal `outputSchema` is not itself a compatibility failure: original
responses plus identified/versioned implementation can support strict parsers.
Reconstructed ToolSearch metadata must not be misrepresented as the raw schema.
Partial parameter types, missing wire names and missing identity/media capabilities
must not be filled in by assumption. Read-only fallback enumeration needs bounded,
complete pages and explicit truncation/conflict errors.

Do not expose a general proxy. The production adapter should not include deletion,
review/scheduling, `get_due_cards`, arbitrary model editing or deck relocation just
because those operations are advertised. Even apparently observational review tools
can have side effects; they are outside this product's scope.

## Shipping consequence

Foundations and historical local regression checks exist. Core production work
is still ahead: verified adapter/search integration; exact authorization and
uncertain-write reconciliation; production interactive review with quality reruns;
resumable onboarding/guide integration; remaining audit fixes and private/novice/
real-Mac end-to-end acceptance. No honest percentage or delivery date follows
from the evidence counts. This is not a final-polish or single-test-away state.

Next procedure and proposed experiments:
[compatibility follow-up plan](../superpowers/plans/2026-11-19-compatibility-follow-up.md).
