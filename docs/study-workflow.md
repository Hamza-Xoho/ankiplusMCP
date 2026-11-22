# A worked lecture-to-Anki workflow

[README](../README.md) · [Tool reference](tools.md) · [Setup and troubleshooting](setup.md) · [Developer guide](developer-guide.md)

This guide draws on an example conversation containing two lecture tasks and
their revisions and recoveries. Names, paths, identifiers and study examples are
generalised. It explains a useful way to combine the existing tools, not a new
automatic pipeline. The assistant still chooses tools to fit your request.

## 1. Tell the assistant what you want to study

Give it the lecture path, the deck to search, the destination for new notes and
the review you want before Anki changes. For example:

> Use `/absolute/lectures/cell-biology.pdf`. Read the learning objectives and
> compare them with my existing Biology deck. Propose existing cards to reuse,
> make new cards only for gaps, and include useful explanations and figures on
> the backs. Show me all proposed cards before adding or unsuspending anything.
> Keep existing cards in their original decks; put new notes in my lecture deck.

Allow both AnkiPlus and a separately configured Anki MCP for this task. AnkiPlus
cannot search your collection or unsuspend cards. If you restrict the assistant
to AnkiPlus alone, it can prepare local drafts but cannot determine what your
collection already covers.

The review-before-write requirement here is your instruction to the host. There
is no server-side human-approval token or mandatory review gate in AnkiPlus.
`submit_review` records findings; it does not record your permission to change Anki.

## 2. Check the source before drafting

The assistant creates a lecture workspace, calls `extract_source`, and follows
the returned job with `get_job`. It reads the map, objectives and selected source
slides rather than repeatedly requesting the whole document. Original files are
unchanged; the workspace contains a source snapshot.

Check what is actually in the slides. A filename may describe several topics
while the supplied PDF covers only part of them. Source ambiguities or conflicts
should be shown to you, not silently filled with outside knowledge.

If extracted text is garbled, the assistant can use `get_page_image` followed by
`get_image` to inspect the rendered slide. A visually readable PDF can have a
broken text layer. Page viewing does not repair the extracted text, and
`extract_source` does not guarantee OCR replacement of a non-empty garbled layer.
Do not treat coverage computed from unreadable text as proof of complete coverage.

## 3. Compare existing cards with the learning objectives

Your assistant searches through Anki MCP, fetches candidate notes and checks the
actual questions, answers, Extra fields and relevant images. It decides whether
the cards teach the lecture's facts and qualifications. A matching keyword alone
does not establish useful coverage.

Ask for a compact learning map:

| Learning objective | Existing card coverage | Remaining work |
| --- | --- | --- |
| Identify cell structures | Suitable existing cards found | Propose those cards for reuse. |
| Identify labels on a lecture diagram | Text cards cover names but not locations | Consider a small image-occlusion set. |
| Explain a comparison in the lecture | No suitable existing card found | Draft a new card with an explanatory back. |
| Material is ambiguous or outside the objective | Candidate conflicts with the lecture | Flag the conflict and agree what to omit. |

For previews, the assistant may save existing-note snapshots in a separate
cards workspace, using templates/CSS or actual question/answer HTML supplied
by Anki MCP. Keep this preview-only workspace separate from new-note drafts.
`Card.action` defaults to `create`: do not prepare and send these snapshots as
new notes just to unsuspend existing cards. Unsuspension uses their actual
Anki **card IDs** through the companion tool.

Matching, deduplication decisions and this learning map belong to the assistant.
AnkiPlus does not search Anki or automatically combine coverage across workspaces.

## 4. Draft only the gaps and choose diagrams deliberately

New cloze cards should preserve the lecture's wording, scope and slide references.
For explanatory backs, ask for a short context paragraph or comparison, a useful
lecture figure when available, and a source reference. An image is not required
on every card: a relevant explanation is better than an unrelated picture.

The assistant saves fields and workspace media with `save_cards`; it does not
need a special rich-back tool. `Extra` is a common field name, but actual fields
must match the chosen note type. Supply the appropriate back template if the
preview's default first/second-field layout does not show the intended fields.

Choose image occlusion when locating a labelled structure is itself part of
the learning goal. Clinical photographs, decorative images and repeated diagrams
may be useful context without needing new masks. OCR is optional assistance:
the assistant can inspect a figure and supply fractional rectangles manually.
`build_occlusion` returns fields, media and an outline preview; `save_cards`
must explicitly save the resulting note with `kind="io"` and the correct note type.

Use `check_cards` for technical problems. Add `house_style=true` only when that
style is intended, and keep the configured profile/tag root consistent with the
drafts. Switching house style off does not fix its findings; report separately
what passed technically and what style rules were not checked.

With `coverage=true`, the check examines saved local cards and recorded
omissions against completed extraction. It cannot see the existing Anki cards
selected elsewhere. Use the learning map to track their contribution; do not
record genuine unfilled learning gaps as omissions merely to make a check clear.
`save_omissions` is for explicit, reasoned exclusions such as a title slide or
a repeated view.

## 5. Review the complete proposal

Ask the assistant to show both existing cards proposed for reuse and every new
card, including front/back previews and each distinct diagram mask. Stable local
labels such as `existing-1`, `new-1` and `diagram-1` make feedback easier.
Existing-card labels must map to their real Anki card IDs. New draft labels get
their Anki ID mappings only after creation and readback.

For existing cards, a main-text approximation may omit Extra content, images,
hint behaviour or add-on features. Ask to inspect the actual card in Anki if
those details matter. The assistant can provide a Browse search using real card
IDs from your collection; local labels and note IDs cannot substitute for them.

You might ask:

> Keep the existing cards where they are. Add a short comparison to the backs of
> new-2 and new-3, remove diagram-2 because it repeats the first diagram, and
> show me the revised cards before proceeding.

After revisions, save the complete intended card set, check it, render fresh
previews and inspect the result. `save_cards` replaces rather than appends.
Changing fields makes previous reviews/previews/plans stale by card hash.
`apply_changes` previews review rewrites by default; applying local changes
still does not edit Anki.

Before approval, confirm the proposed destination, note types, omitted content,
and separate counts for:

- **New notes:** the records that will be added to Anki.
- **New cards:** the study questions generated by those notes.
- **Existing cards to unsuspend:** cards already in your collection.

For an illustrative disjoint set, three single-deletion cloze notes and two
diagram notes with three tested mask groups each mean **5 new notes, 9 new cards**.
Reusing four different existing cards adds **4 unsuspensions**, not four more
new notes. Across several lectures, deduplicate card IDs before claiming a unique
total of reused cards: the same existing card may cover more than one lecture.

## 6. Approve the actions, then hand off to Anki

Once you have reviewed the proposed changes, explicitly tell the assistant to
execute them. A request to continue preparing after a network interruption is
not approval to write when you previously asked for manual review.

`prepare_write` can generate a local plan before approval: its planned counts
and `performed_anki_operations: 0` are not collection changes. Refresh the
workspace and prepare a current plan after changes to cards, destination or media.

Before executing, the host should check current collection state, the note
types/fields, duplicate candidates and the requested deck path using its Anki MCP.
The example run encountered a companion tool with a deck-depth restriction;
that is not a universal limit in AnkiPlus. Inspect the installed tool's schema
and error remedies rather than assuming every Anki server behaves identically.
Confirm an available creation/move approach before adding notes to a staging deck.
If one is used, track the newly created card IDs and move only that approved set.

The host stores approved media, adds new notes or applies separately approved
updates, and unsuspends the selected existing card IDs through Anki MCP. AnkiPlus
does none of these operations itself. Existing cards can remain in their original
decks while the new notes go to the agreed lecture deck.

## 7. Verify, report and sync

Ask the host to read back the created notes/cards, destination deck and suspension
state. Count actual returned IDs and reconcile them with the plan. If a write
times out or has an ambiguous response, inspect Anki before retrying it; blindly
repeating a successful-but-unacknowledged addition can duplicate cards.

`record_external_results` optionally stores actual host-supplied responses against
the plan. It labels those results `caller_supplied` and never independently
verifies Anki. `get_report` counts submitted result records, not automatically
the number of notes/cards affected. The assistant's final summary should distinguish
planned actions, observed readbacks, failures and any unresolved ambiguity.

Sync Anki when you are ready. A reminder to sync is not evidence that a sync
completed.

## When something interrupts the task

| Problem | Useful recovery |
| --- | --- |
| Extracted text is unreadable | Inspect rendered page images and say what was read visually; do not claim an OCR repair without doing one. |
| A read asks for too much text | Keep `read_source`/`read_artifact` limits at or below 24,000 characters and follow `next_offset`. |
| A job changes the workspace revision | Wait for completion, read `get_workspace`, inspect current cards if needed, and reconcile before saving/reviewing. |
| House style rejects the tag tree | Check the server profile/tag root against the draft tags. Fix the mismatch or explicitly choose technical-only checks; do not describe disabled rules as passed. |
| Network/chat stream breaks | Resume the saved workspace and inspect jobs/cards/plan. Reconcile possible Anki writes; preserve the original review/approval requirement. |
| The requested deck cannot be created | Check the companion tool's current constraints before choosing a supported creation/move approach. |

See [setup troubleshooting](setup.md#troubleshooting) and the individual
[tool contracts](tools.md) for exact inputs and returned errors.
