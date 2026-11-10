# Anki card workspace

This folder is where cards are made and maintained with `/anki2` (`.claude/skills/anki2/SKILL.md`) for BUILD and resume. HARVEST and REPAIR stay on `/anki`.
Anki runs locally with the AnkiMCP add-on (MCP server `anki`, http://127.0.0.1:3141/). Note type for own cards: `ColdRecall Cloze` (fields Text, Extra).

## Always
- Use `/anki2` for lecture card builds and resume; follow its small core and load only the current phase file. Route HARVEST and REPAIR to `/anki`.
- One lecture (or one topic) per conversation.
- Each job gets a folder `builds/<YYYY-MM-DD>_<lecture-id-or-slug>/` for manifest, drafts.jsonl, model/, renders/, reports. Never put working files in the lecture folder or the vault.
- Use `.venv/bin/python` for all scripts. Rebuild the venv with `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`.
- Writes happen without asking once `cards gate` passes (ADR-9)
- Never delete notes unless told "delete". Default for replacing cards: suspend + tag `#ColdRecall::!Flags::Replaced_<date>`.
- Every tag under `#ColdRecall::`. Never write into AnKing's tag trees or note types. Own cards use `ColdRecall Cloze`.
- AnKing first: before drafting, search the AnKing MCAT/Step decks for the same facts; an existing AnKing note becomes an unsuspend proposal, not a new card. MCAT deck fits M1 foundational science; Step deck fits clinical depth; one deck per concept.
- Anatomy is base-first: bones and landmarks → joints → movements → muscles → nerves and vessels.
- Note ids vs card ids: suspend/unsuspend take CARD ids.
- Never invent content for a source file you could not read. A cloud-only Drive file that won't open: tell the user to make it available offline.
- Honor Claude Code tool permissions. A permission refusal stops the run; never work around it.
- After finishing, remind the user to sync Anki.

## How a conversation starts → what to do
1. **"cards from <lecture/file/slides 5–12>"** → `/anki2` BUILD on that source (or only those slides). Resolve the lecture ID from the filename or the block's `session-index.md`.
2. **"cards from this: <pasted text / notes / a topic>"** → `/anki` BUILD with the pasted text as the source. The maintainer checks fidelity against that text only; nothing from general knowledge unless the user says "fill gaps". Source tag `#ColdRecall::#Source::Prompt::<YYYY-MM-DD>_<slug>`. Ask which deck if not obvious.
3. **"fix / adjust / redo <cards, deck, tag, or a search>"** → `/anki` REPAIR, following its review and approval rules.
4. **"suspend / unsuspend <lecture, tag, tier, search>"** → `/anki` for manual suspension requests, following its approval rules. Common searches:
   - a lecture: `tag:#ColdRecall::#Source::<COURSE>::L<nnn>*`
   - a lecture's tier 1–2: add `-tag:#ColdRecall::!Tier::3`
   - AnKing cards for a lecture: by the AnKing tag the user gives, or by keyword in the AnKing deck
5. **"what's due / how am I doing in <subject>"** → `/anki` READ (due today, weak cards below 0.85 retrievability). Other subjects get one line.
6. **Anything else card-related** → say which job it maps to before starting. If none fits, say so and propose the closest.

## Paths and IDs
- Lectures and books (READ-ONLY, never write): `~/Library/CloudStorage/GoogleDrive-<account>/<lecture folder>`
  - Lectures: `01-Blocks/<BLOCK>/Lectures/MED241_L025_2026-09-29_topic.pdf` (P practicals, B CBL, T skills). Each block has `session-index.md`.
  - `03-Resources` is senior material: say so whenever it is used. Books: `<lecture folder>/Books/`.
- Obsidian vault (understanding lives there, not cards): `<your notes vault>`. Read-only unless asked.
- Skills: `.claude/skills/anki2/` (BUILD/resume), `.claude/skills/anki/` (v1 HARVEST/REPAIR). Builds: `builds/`. Scripts: `scripts/`.
- `/anki2` deck convention: flat title resolved by `cards target` from slide 1. Preserve existing nested decks.
