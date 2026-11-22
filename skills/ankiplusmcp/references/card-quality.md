# Authoring and repairing cards

## Decide what earns retrieval practice

Target the knowledge the learner must retrieve for the requested learning goal.
Preserve examinable source detail without making every aside a card. A useful
mechanism can be tested as a short causal relationship; long explanations belong
on the back or in study notes. Being derivable does not automatically make a fact
unworthy of practice: consider the need for fast, reliable recall.

Identify gaps against selected existing cards first. An extra lecture detail gets
its own focused retrieval target; sufficient visible context may repeat without
retesting the existing fact. Zero new cards is a valid outcome.

## Write questions that work independently

Prefer cloze for concise textual relationships, Basic for questions that are
clearer as direct prompts, and image occlusion for visual identification. Match
available note types and fields; preserve shared types and templates.

- Test a focused relationship or answer unit. Split independent facts and
  unstructured lists. Named phrases, ranges and necessary units can form one
  answer; punctuation alone does not determine atomicity.
- Leave enough context that a knowledgeable learner can answer at the intended
  level. Use category hints only when they clarify scope without supplying the
  answer. Keep necessary conditions visible.
- Check every generated cloze card separately. Visible siblings, sentence
  grammar, titles and hints can reveal an answer. One good deletion is sufficient;
  adding a deletion must add worthwhile retrieval practice.
- Test reverse directions only when useful and sufficiently specific. A category
  can have several valid members. Clozing both sides does not fix ambiguity.
- For a genuine sequence, supply the order/context needed to distinguish steps.
  Sequential reveal belongs to ordered recall, not arbitrary collections.
- Preserve the source's terminology, scope, hedges and units. Separate any
  requested outside explanation from lecture-supported facts and cite its source.
  Surface suspected errors instead of silently repeating or correcting them.

## Worked example: reverse ambiguity

Synthetic source p6: Within the lecture's examples, devices Alpha and Beta both
implement protocol P. The objective is to identify each device's protocol.

Weak: `{{c2::Device Alpha}} implements protocol {{c1::P}}`

The c2 question has at least two valid answers under the source. Better:

- `<b>Device Alpha</b> implements protocol {{c1::P}}` — p6
- `<b>Device Beta</b> implements protocol {{c1::P}}` — p6

Keep the lecture's restricted scope in visible text where needed to avoid a
broader claim. The example tests the requested direction without generating
ambiguous reverse cards. This is an illustration, not an Anki payload schema.

## Make the back useful

The front must be answerable before the back appears. Include only helpful
material: a short why, a contrast or mnemonic, a relevant figure, then the source
reference. Use enough explanation to resolve likely confusion; neither a fixed
line limit nor an image on every card improves quality by itself.

For an AnKing-like style, bold the main subject, emphasise meaning-changing
qualifiers sparingly, and format chemistry/units correctly. Follow the user's
existing conventions. Formatting polish is lower priority than correct recall.
Tier labels can express importance; no tier percentage is required. Generate
peripheral cards suspended only when that preparation is requested; do not create
extra notes just to fill a tier.

## Review with a stopping condition

For each new or changed card, check:
1. The question has an appropriate, unambiguous answer using visible context.
2. The cited source supports the claim, including its qualifications.
3. The deletion tests useful knowledge without accidental answer leakage.
4. The back explains without becoming necessary to interpret the question.

Across the selected and new cards, check duplicate retrieval targets, confusing
near-twins, consistent terms and units, and coverage of requested requirements.
Make discriminating conditions visible or use a focused comparison. Inspect new
card renders when layout, clozes, media or templates could alter the question;
show requested previews. Mechanical checks cannot establish factual correctness.

Fix a specific defect, then recheck that card and affected neighbours. A blocker
still unresolved after two correction passes stays out of activation: report it
as unresolved rather than repeatedly restarting the batch. Independent review is
optional and should address a named uncertainty, not automatically summon panels.

For repairs, inspect siblings and near-twins first. Preserve review history;
resetting, deleting or suspending existing cards must fit the authorized task.
