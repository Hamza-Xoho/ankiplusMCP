# Companion skill validation — 2026-11-22

## Deliverable

`skills/ankiplusmcp/SKILL.md` and its three conditional references. The npm
installer already copies this entire directory recursively. No MCP API,
collection access code, host configuration, legacy rubric or CLI was changed.
The tool-served overview remains its existing general mechanical guidance;
these new editorial instructions are distributed as the companion skill, not
as new server guidance topics. Install the complete skill directory, not only
its entrypoint, so the references are available.

## Application checks

Two fresh independent applications used the same six
[synthetic scenarios](evaluations/companion-scenarios.md), first with the old
companion, then with the new companion. Neither agent received the expected
answers or the author's rationale. There were no live collection operations.

| Case | Observed new-companion decision |
| --- | --- |
| Mixed origin, partial coverage, sibling | Select linked 101; reuse non-linked 211; count active 301; exclude duplicate 201 and unrelated sibling 102 |
| No AnkiHub notes | Reuse 401 and draft only the condition-V release fact |
| Unknown origin, conflicting card | Keep origin unknown; count active 511; exclude universal-causation card 501 |
| Fact only in Extra | Decline 601 as tested coverage and draft the connection relationship |
| Timed-out addition | Inspect collection state before retry; preserve the existing draft |
| Ambiguous reverse direction | Draft Alpha→P and Beta→P only; skip unrelated OCR/reviewer/collection-dump work |

The baseline also made mostly sound choices and selected the same existing IDs.
It explicitly stated: "The companion does not mandate an AnkiHub preference."
This comparison verifies that the new instructions can be applied coherently;
it does **not** demonstrate a measured improvement over baseline or statistical
reliability. The fresh application reported no concrete contradictions or
omissions. These are six small synthetic cases, not a full lecture trial.

## Mechanical checks

- Skill creator `quick_validate.py`: passed.
- Local Markdown reference resolution: passed for all four skill files.
- `npm pack --dry-run --json`: includes the entrypoint and all three references.
- Isolated launcher `init` using the repository's test helper and temporary
  project/home: all four installed files match source byte-for-byte. Temporary
  directories removed; real host configuration unchanged.
- `npm test`: 28 passed, zero failures.
- `./scripts/check-mcp.sh`: 250 passed, 1 skipped; all frozen contract hashes
  matched; Python wheel built. The existing optional system-Chrome rendering
  test skips when Google Chrome is not installed (`tests/mcp/test_cards.py`).
- `git diff --check`: passed.
- Portable archive: exactly the four skill Markdown files under `ankiplusmcp/`,
  CRC and byte-for-byte source comparison passed.

The entrypoint is approximately 590 words. The complete skill is approximately
2,240 words; selection, authoring and diagram detail are loaded conditionally.
No container build was needed: only companion Markdown and development notes
changed, and no application or container configuration was modified.

## Limits and next useful evidence

No live Anki MCP was connected, so actual AnkiHub search-extension behaviour,
origin detection, collection writes and sync were not exercised. Unsupported
origin detection explicitly falls back to searching all scoped decks.

No claim of reduced lecture token use is made. To measure it, run the same
representative lecture and collection snapshot with the old and new companion,
keeping model/settings fixed. Record input/output tokens, tool calls, selected
existing cards, new notes/generated cards, duplicate retrieval targets, missed
requirements and correction rounds. Include both an AnkiHub and a non-AnkiHub
collection case. Mechanical check results do not establish factual accuracy.
