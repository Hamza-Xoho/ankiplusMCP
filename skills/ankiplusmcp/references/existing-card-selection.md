# Existing-card selection

## Establish scope and origin

Search all decks unless the user restricts them. Search concepts within that scope,
not every field of every note. AnkiHub priority applies to suitable cards only.
A linked but irrelevant, ambiguous or contradictory card does not earn selection.

Use the installed Anki MCP's actual capabilities. With the AnkiHub add-on active,
its search extensions may identify linked notes. A documented non-empty-ID search
is `ankihub_id:_*`; verify that the installed combination supports it. Where
possible, compare a known linked note as a positive control. An unsupported query
or unexplained empty result is not proof that no AnkiHub notes exist. A genuinely
empty supported search permits skipping the AnkiHub branch.

A valid non-empty AnkiHub ID is evidence of linkage; merely having an ID field,
an AnKing note type, tags or a familiar deck name is insufficient. Linkage does
not establish an active subscription. Classify notes, not whole decks: a deck may
mix linked and local notes. No linkage does not mean user-authored; other shared
decks belong in the second search too. If identification fails, retain unknown
origin and continue across the selected collection without a priority claim.

## Compare retrieval targets

Read candidates' relevant fields, cloze variants and suspension states. Inspect
media or rendered questions if needed to determine what is actually tested.
Match the tested relationship, conditions, answer specificity and qualifications.
An answer appearing somewhere in a note is insufficient evidence of coverage.

| Finding | Decision |
| --- | --- |
| Suitable linked card tests the requirement | Select it ahead of equivalent non-linked candidates |
| Selected card already active | Count coverage; no unsuspension needed |
| Selected card suspended | Include that card ID in the unsuspension set |
| Linked card covers only part | Keep it; search other cards for the extra detail |
| Suitable non-linked card covers a remaining gap | Reuse it before creating a new note |
| Required fact appears only in Extra | Supporting context, not tested coverage |
| Candidate changes the claim or its conditions | Flag the conflict; seek compatible coverage |
| No suitable match after reasonable searches | Draft the missing retrieval target |

Choose sufficient coverage rather than every related card. Within the same origin
priority, prefer a clear, focused card and avoid redundant activation. Deduplicate
card IDs across requirements. Never unsuspend all cloze siblings merely because
one is relevant. Note IDs group notes; card IDs identify specific study questions.

Existing active duplicates can remain in place. Report meaningful overlap if
selecting an AnkiHub replacement would add redundant review; suspending, moving
or editing the earlier card is a separate change requiring task authorization.

## Partial-coverage example

Synthetic source:
- p2: Protein Z is produced by cell Q.
- p3: Under condition R, protein Z is released by stimulus S.

A linked card tests cell Q. Select that card. Search non-linked notes for the
condition-R release relationship. If one tests stimulus S with the correct
condition, reuse it. Otherwise draft that relationship alone, retaining condition
R as context and citing p3. A new note repeating both p2 and p3 adds unnecessary
retrieval work. A different release condition is a source conflict to resolve,
not a reason to strengthen the lecture's claim.

## Finish and resume

Store compact evidence per requirement and real ID mappings. Keep existing-note
preview snapshots separate from new-note drafts: their default create action can
otherwise turn an unsuspension task into duplicate additions.

Coverage checks over local AnkiPlus drafts cannot see selected Anki cards
elsewhere. Combine both in the coverage record. Use omission records for actual
exclusions, not to conceal gaps covered elsewhere or unresolved requirements.

On reruns, reconcile the saved drafts, source identifiers and collection before
creating anything. After a timeout, inspect for the exact previously submitted
content and reconcile matching notes/cards before retrying. Record ambiguity if
identity cannot be established; response counts alone do not verify a write.

Search syntax references, consulted 2026-11-22:
- [AnkiMCP tool reference](https://ankimcp.ai/docs/reference/addon/tools/)
- [AnKing's non-empty AnkiHub ID search](https://community.ankihub.net/t/anking-v11-not-updating-to-v12/3816)
