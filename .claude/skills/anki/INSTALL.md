# Installing the anki skill in Claude Code (macOS)

1. **Copy the folder**

       mkdir -p ~/.claude/skills
       cp -R anki ~/.claude/skills/anki

   Claude Code picks it up the next time it starts. Check with `/skills`.

2. **Connect AnkiMCP.** Anki must be open with the AnkiMCP add-on
   (AnkiWeb code 124672614) running on http://127.0.0.1:3141/.

       claude mcp add --transport http --scope user anki http://127.0.0.1:3141/

   If the add-on's README gives a different endpoint path, use that one.
   Check with `/mcp`: the tools show up as `mcp__anki__*`.

3. **Renderer dependencies** (one time)

       python3 -m pip install --user playwright pymupdf pillow   # and: brew install poppler (pdftotext)
       python3 -m playwright install chromium

   The occlusion scripts also need what `references/image-occlusion.md` lists
   (OCR).

4. **Use it.** In a terminal opened at your lecture folder:

       cd ~/Library/CloudStorage/GoogleDrive-<account>/My\ Drive/<lecture-folder>
       claude
       > make cards from MED241_L025

The `ColdRecall Cloze` note type already exists in your Anki, so nothing to
create. On a fresh profile, the skill makes it from `assets/coldrecall-cloze/`.
