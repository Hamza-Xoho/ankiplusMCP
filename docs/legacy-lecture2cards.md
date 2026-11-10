# Lecture2Cards

Turn one lecture PDF into reviewed Anki flashcards.

Lecture2Cards reads a lecture, drafts cloze and image-occlusion cards that use
the lecture's own terms, has two independent AI reviewers check them (one as a
strict AnKing-style deck maintainer, one as a student using the cards), and
writes the cards that pass into a single Anki deck.

It ships two things:

- **`cards`**: a command-line tool that does the deterministic work (text and
  OCR extraction, slide maps, rendering, schema and style checks, the review
  gate, and write plans).
- **`/ankiv2`**: a skill for [Claude Code](https://claude.com/claude-code) or
  [OpenCode](https://opencode.ai) that drives the whole build and does the
  judgement work (drafting, reviewing, rewriting).

> **Before you study from these cards, skim them.** The reviewers are AI and
> they can be wrong. The pipeline is designed to catch most problems, not all of
> them. Lecture2Cards is a drafting assistant, not a replacement for your own
> check of the material.

Want to know how it works or why it is built this way? See
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

---

## What you get

For one lecture, after 30 to 60 minutes of work:

- A new flat deck named after the lecture's first slide title (for example
  `Action potentials`).
- Cloze cards (and image-occlusion cards where a labelled figure matters), each
  tagged `#ColdRecall::…` with its lecture source and a difficulty tier.
- Tier 3 cards, the least essential, written **suspended** so they stay out of
  your reviews until you unsuspend them.
- Existing Anki notes you already have on the same facts are not duplicated.
  The tool proposes them for unsuspending instead.
- A short report with counts and a reminder to sync Anki.

Nothing is deleted. Existing notes are never removed or rewritten by the tool.

## What you need

| Requirement | Notes |
|---|---|
| A lecture PDF | **One lecture per build.** Merged or multi-lecture PDFs are refused. Split them first. Use material you are allowed to use. Do not share the PDFs. |
| Python 3.12+ | `python3 --version` |
| Tesseract OCR | `brew install tesseract` on macOS. Used for text in slide images. |
| Chromium for Playwright | Used to render the card previews. See install step 1. |
| Anki desktop | Must be open while the tool writes cards. |
| A local Anki MCP server | The skill talks to Anki through MCP tools, at `http://127.0.0.1:3141/`. This project was built and tested against the AnkiMCP add-on. |
| The ColdRecall Cloze note type | Shipped in [`src/cards/assets/coldrecall-cloze/`](../src/cards/assets/coldrecall-cloze/). Create it in Anki once (see below). |
| Claude Code or OpenCode | With an account that can run a long agent session. A build reads the lecture, drafts, and runs two review rounds, so it uses a lot of model usage. |

## Install

### 1. Install the `cards` command

From a clone of this repository:

```sh
git clone https://github.com/Hamza-Xoho/Lecture2Cards.git
cd Lecture2Cards
uv tool install .        # or: pipx install .
cards --help
```

Install Chromium for the renderer. Browsers are cached once for all tools, so
this only needs doing once:

```sh
uvx --from playwright==1.64.1 playwright install chromium
# without uv: pip install playwright==1.64.1 && python -m playwright install chromium
```

### 2. Install the skill and reviewer agents

```sh
python3 scripts/package_ankiv2.py --install                  # Codex, Claude Code and OpenCode
python3 scripts/package_ankiv2.py --install --runtime claude   # Claude Code only
python3 scripts/package_ankiv2.py --install --runtime opencode # OpenCode only
python3 scripts/package_ankiv2.py --install --runtime codex    # Codex only
```

This copies the Codex skill to `~/.agents/skills/ankiv2`, and the other runtime skills to `~/.claude/skills/ankiv2` and/or
`~/.config/opencode/skills/ankiv2`, and the two reviewer agents next to it.
Codex uses fresh isolated host subagents for its two reviewer roles.
Re-run the installer after you update the repository.

### 3. Connect Anki

1. Open Anki and install your Anki MCP server add-on. It must serve
   `http://127.0.0.1:3141/`.
2. Add the server to your runtime:

   ```sh
   claude mcp add --transport http anki http://127.0.0.1:3141/   # Claude Code
   opencode mcp add anki --url http://127.0.0.1:3141/            # OpenCode
   ```

3. Create the note type once. In Anki, add a **Cloze** note type named
   `ColdRecall Cloze` with the fields `Text` and `Extra`. Paste the templates
   and CSS from `src/cards/assets/coldrecall-cloze/` (`front.html`, `back.html`,
   `style.css`).

## Make cards

Open Anki, then in Claude Code run:

```text
/ankiv2 "/absolute/path/to/MED241_L006_action-potentials.pdf"
```

In OpenCode, ask for the skill by name and give the same path:

```text
Use the ankiv2 skill on "/absolute/path/to/MED241_L006_action-potentials.pdf"
```

You can also ask for part of a lecture, for example "slides 5-12".

Filenames work best in the form `COURSE_L###_date_topic.pdf`, for example
`MED241_L006_2026-09-13_cell-biology.pdf`. If the name is not recognised, the
skill asks you for the course, lecture number and title.

### What happens

1. **Preflight.** Checks that Anki is reachable and the note type exists.
2. **Extract.** Reads the text, objectives and figures, and builds a slide map.
3. **Draft.** Writes the cards from the lecture's own terms. It does not add
   facts from general knowledge.
4. **Check and render.** Catches broken cloze syntax, style problems and
   coverage gaps, and renders previews.
5. **Review.** A maintainer reviewer and a student reviewer check the cards in
   parallel. Their fixes are applied. At most two rounds.
6. **Gate.** An automatic, fail-closed check. If anything is unresolved, nothing
   is written.
7. **Write.** Cards are added to Anki in batches, then read back and verified.
8. **Report.** Counts, anything suspended, and a sync reminder.

### If it stops

Builds are resumable. Usage limits and interruptions are common on long runs.
To continue, run the same command with the same PDF:

```text
/ankiv2 "/absolute/path/to/MED241_L006_action-potentials.pdf"
```

The skill reads the build's `build.json` and continues from the last completed
step. It does not repeat extraction or resend batches that already succeeded.

Builds are stored in `./builds/` in the folder you start from. To keep them in
one place, set `CARDS_BUILDS` to an absolute path before you run the skill, and
keep it the same when you resume.

## Using the cards

- **Skim the deck before your first review.** Especially the image-occlusion
  cards and any card about a number or a threshold.
- **Tier 3 is suspended.** Unsuspend them when you are ready for the detail.
- **Tags** are under `#ColdRecall::`. For example, `#ColdRecall::!Tier::1` marks
  the core cards.
- **Found a bad card?** Edit or delete it in Anki yourself. The tool does not
  delete or overwrite existing notes, so future builds will not touch your fix.

## Safety and privacy

- **Your files.** The lecture PDF is read, never modified. Working files stay
  in the build folder.
- **Anki writes.** Cards are only written after the automatic gate passes. The
  write step adds notes and suspends listed cards. It does not delete anything,
  and it only edits earlier cards for this same lecture that the draft step
  identified by id.
- **Model provider.** The lecture text and drafts are sent to the model provider
  of the runtime you use (Claude Code or OpenCode), like any other chat. Check
  your provider's data terms if your material is sensitive.
- **Network.** The `cards` command makes no network calls. Only the runtime and
  the local Anki MCP server are contacted.
- **Runtime guards differ.** In Claude Code, this project's own settings can
  add hooks that block direct PDF reads and writes before the gate. The packaged
  skill does not install those hooks. In OpenCode, the gate is enforced by the
  `cards` command and the skill's instructions, so review the write plan before
  you let the agent write.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `cards: command not found` | Run `uv tool install .` again, and check that `~/.local/bin` (or pipx's bin folder) is on your `PATH`. |
| `renderer unavailable` | Install Chromium (install step 1). |
| `OCR failed` or no text extracted | Check that `tesseract` runs in a terminal. |
| `multi-lecture or merged file` | Split the PDF so there is one lecture per build. |
| Deck name is wrong | Ask the skill to set the course, number and title again. It reruns `cards target` with those values. Do not edit build files by hand. |
| Anki not reachable | Open Anki and make sure the MCP add-on is running on port 3141. |
| Usage limit reached | Wait for the limit to reset, then run the same command again. The build resumes. |
| A `cards` command errors | The skill stops and reports the command and error. Fix the cause and resume. Do not edit the installed skill, the package, or the build JSON to get past it. |

## For developers

- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md): how the pipeline works, the
  build state machine, the CLI contract, and the reasons behind the design.
- [`docs/anki-v2-brief.md`](../docs/anki-v2-brief.md): why and what.
- [`docs/anki-v2-trd.md`](../docs/anki-v2-trd.md) and
  [`docs/design-spec.md`](../docs/design-spec.md): requirements and the how.
- [`docs/test-contract.md`](../docs/test-contract.md): the named contract tests.

Development setup:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q tests/unit
CARDS_PUBLIC_CI=1 .venv/bin/python -m pytest -q tests/contract
```

The contract tests in `.codex/contract.sha256` are frozen. Do not edit them to
make a change pass. Tests that need private lecture PDFs are skipped in public CI
through `CARDS_PUBLIC_CI=1`. Locally, a missing private fixture fails the test.

The build history (phase logs and run results) is in
[`docs/development-history.md`](../docs/development-history.md) and
[`docs/decisions.md`](../docs/decisions.md).

## Limitations

- One lecture per build. Multi-lecture builds are planned for a later version.
- Cards are drafts from AI reviewers. A reviewer can miss a problem or be
  wrong about a fact the lecture does not state.
- Image occlusion quality has been checked on few lectures.
- Extracting a cold lecture can take minutes, mostly OCR and rendering.
- HARVEST (study-session capture) and REPAIR (fixing existing decks) are not in
  this version. Use the separate `/anki` skill for those.
- Codex is not supported yet.

## Licence

MIT. See [`LICENSE`](../LICENSE).
