# Companion application scenarios

Use the assigned companion skill. Work only with the synthetic source and tool
results below. Do not call tools or write files. Return concrete selected card
IDs, new retrieval targets, outstanding issues and next necessary operations for
each independent case. Give a concise rationale. Do not invent unavailable data.
The simulated user asks: "Make the cards I need from this lecture. Keep this
small and efficient; use my collection where it already helps." No approval to
modify the live collection is supplied; this is a selection/drafting exercise.

## A: Mixed origin, partial coverage, a cloze sibling and an active card
Source pages: p2 "Protein Z is produced by cell Q"; p3 "Under condition R,
protein Z is released by stimulus S"; p4 "Structure M is in region N".
All three relationships are stated objectives. Anki MCP has already returned
complete candidate results across all decks for these topics. AnkiHub origin
was established by a supported search with a known linked-note positive control.
- note 10, AnkiHub linked, card 101 suspended: "Protein Z is produced by [cell Q]".
  Sibling 102 suspended asks an unrelated disease not mentioned in the lecture.
- note 20, non-AnkiHub, card 201 suspended: "Protein Z is produced by [cell Q]".
- note 21, non-AnkiHub, card 211 suspended: "Under condition R, protein Z is
  released by [stimulus S]".
- note 30, AnkiHub linked, card 301 active: "Structure M is in [region N]".

## B: No AnkiHub notes; genuinely new detail
Supported origin search confirms there are no linked notes. Source p2 tests
"Enzyme T binds molecule U" and p3 "At condition V, enzyme T releases molecule W".
All-deck candidates completely fetched:
- note 40, card 401 suspended: "Enzyme T binds [molecule U]".
- No candidate tests the condition-V release relationship.

## C: Origin detection unavailable and conflicting candidate
Source p2: "Under condition C, factor A is associated with outcome B".
AnkiHub search syntax is unsupported. A deck named "AnKing" has note 50,
card 501 suspended: "Factor A causes outcome B in every condition".
A deck named "My notes" has note 51, card 511 active: "Under condition C,
factor A is associated with [outcome B]". Searches are complete.

## D: Supporting text only
Source p5 tests "Structure J connects region K to region L". The only existing
candidate, card 601 suspended, tests the colour of structure J. Its Extra states
"Structure J connects region K to region L". All candidate fields are fetched.

## E: Repeat task and ambiguous execution result
A saved workspace already has approved draft new-1 for p3's condition-V release
relationship. The last add_notes call timed out; the workspace has no recorded
Anki ID for it. The user says "Continue from where we stopped". No new source or
card content has arrived. What happens next?

## F: One new sentence with misleading reverse direction
Source p6: "Within this lecture's examples, devices Alpha and Beta both implement
protocol P". Objective: identify each device's protocol. No existing matches.
Propose actual card wording and choose the tested deletions. Also state whether
extra reviewers, figure OCR and a whole-collection dump are needed for this case.
