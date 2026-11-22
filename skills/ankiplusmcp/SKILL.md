---
name: ankiplusmcp
description: Use when selecting existing Anki cards, unsuspending lecture-relevant cards, or making and improving flashcards from lectures, notes or diagrams with AnkiPlus MCP and a separate Anki MCP.
---

# AnkiPlus companion

Cover the requested learning requirements with suitable existing cards, preferring
AnkiHub-linked cards when available. Author only the remaining gaps. AnkiPlus
handles sources, local drafts, checks and previews; the separate Anki MCP reads
and changes the collection. The host chooses tools to fit the task.

## Select before drafting

Read [selection](references/existing-card-selection.md) when matching existing
cards or choosing unsuspensions.

- Search **all decks by default**; preserve a user-selected narrower scope.
- Establish AnkiHub availability once. Prefer suitable linked cards, then search
  non-AnkiHub cards for remaining gaps. With no linked cards, search existing
  cards directly. If origin cannot be established, search all scoped cards and
  record origin as unknown. AnkiHub is optional.
- Judge the actual question and answer of each card/cloze. Keywords and facts
  appearing only in Extra are not tested coverage. Count already-active cards
  as covered; select only relevant suspended card IDs for unsuspension.
- Partial coverage keeps the useful existing card and targets the extra lecture
  detail separately. Check that gap against other existing cards before writing
  it. Resolve source conflicts separately from missing detail.

## Source and card quality

Read [card quality](references/card-quality.md) before authoring or rewriting;
read [diagrams](references/diagram-cards.md) only for visual identification tasks.

Inspect the requested source scope, including diagrams needed to understand it.
Keep a compact coverage record: **requirement | page/slide | selected card IDs |
remaining gap or exclusion reason**. Use explicit objectives where available;
otherwise identify testable requirements without inventing lecturer objectives.
Preserve terminology, conditions, qualifications and units. Create clear,
focused retrieval questions with useful explanatory backs.

Review new/changed cards and uncertain matches for fidelity, ambiguity, leakage,
duplication and interference. Check the resulting set against the coverage record.
Cloze is a preference, not a quota. Additional reviewers are optional; choose them
for a concrete uncertainty or a user request. There is no compulsory pipeline.

## Keep work bounded

Extract once per source version. Batch related searches, inspect plausible
candidates and retain results. Read full fields/images only where needed to judge
a match. Avoid dumping the collection or rendering unrelated cards. Broaden an
unsuccessful search with relevant synonyms; if results remain unmanageably broad,
report the uncertain gap rather than repeatedly expanding the search.

Revisit settled decisions when evidence changes. Recheck revised cards and their
affected group, rather than restarting the task. Stop when each requirement is
covered, deliberately excluded or explicitly unresolved. Offer peripheral detail
separately; a card count or tier percentage is never a target. Bundled optional
rubrics may contain legacy house-style rules; apply the user's requested style
and this companion's selection policy, without importing a mandatory review panel
or fixed tier/cloze quotas.

## Apply and report

Follow the user's authorization and any requested preview-before-write boundary;
local review findings and write plans are not user approval. Preserve existing
decks, history and shared note types. Use current tool schemas for exact calls.

Use explicit workspace IDs and current revisions. `save_cards` replaces the local
set; preserve intended unchanged cards. Follow job IDs to completion.
`prepare_write` prepares payloads, not Anki changes. Suspension uses Anki **card**
IDs, not note IDs or workspace IDs. Inspect Anki before retrying an ambiguous write.

Verify actual collection changes by readback. Report existing coverage, cards
newly unsuspended, new notes and generated cards separately; distinguish proposed
from executed actions and identify unresolved gaps. An unavailable Anki connection
permits local drafting, not claims that existing coverage or writes were checked.
