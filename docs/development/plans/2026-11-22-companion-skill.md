# AnkiPlus companion skill implementation plan

**Goal:** Deliver the approved companion: prefer suitable AnkiHub-linked cards,
reuse other existing cards for gaps, then author only uncovered retrieval targets.
**Architecture:** Extend the existing installer-distributed skill with conditional
references. Leave MCP tools and legacy CLI/rubrics unchanged. Bundle the result
as a portable skill, without changing any host configuration or Anki collection.
**Spec:** User-approved design in this conversation, 2026-11-22.

## Constraints

- Search all decks by default; AnkiHub is optional and origin may be unknown.
- Decide coverage at card/cloze level, preserving source qualifications.
- Partial coverage retains the useful existing card and fills only its gap.
- Keep mechanical tool choice with the host; use no compulsory reviewer panel.
- Extract once, batch searches, fetch plausible candidates, reuse a compact map.
- Preserve user approval requirements, history, shared note types and unrelated work.
- No new server tools, configuration changes, publication or live Anki operations.

## Review focus

Missing AnkiHub, unsupported origin search, Extra-only matches, cloze siblings,
source conflicts, and interrupted writes must have explicit handling. References
must survive installer copying and the downloadable archive. Legacy optional
rubrics must not silently reinstate quotas or a fixed review pipeline.

## Work

- [x] Run the old companion on synthetic cases before writing; record failures.
- [x] Update `skills/ankiplusmcp/SKILL.md`; add conditional selection, authoring,
      and diagram references in `skills/ankiplusmcp/references/`.
- [x] Run a fresh independent application of the same cases; fix material gaps.
- [x] Validate skill structure, local links, npm package contents and installed
      reference copying; run existing launcher and MCP checks.
- [x] Record evidence in `docs/development/companion-skill-validation.md`.
- [x] Build a `.skill` archive under Hamza's existing local outputs directory,
      inspect its contents, and commit only source/docs for this change.

## Baseline criteria

A: select AnkiHub 101 and active 301; reuse 211 for the additional requirement;
no new note, duplicate 201 or unrelated sibling 102.
B: reuse 401 and draft only the condition-V relationship.
C: retain unknown origin, reject 501 as coverage, count active 511.
D: Extra is not tested coverage; draft the connection relationship.
E: read collection state before retrying the ambiguous write.
F: test Alpha→P and Beta→P without ambiguous P→device reversal; skip unrelated work.

Behavioral runs are small synthetic checks, not statistical quality or token
benchmarks. There is no live Anki MCP available for end-to-end validation.
