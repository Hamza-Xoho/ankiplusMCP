# AnkiPlus MCP

`ankiplusmcp` gives a model independent mechanical helpers for lecture extraction,
OCR, image occlusions, card validation, previews, review changes and Anki payload
preparation. The model chooses which tools to use. There is no mandatory pipeline,
review panel or model provider.

**The official Anki MCP is a separate companion dependency.** Configure both in
your AI host. AnkiPlus never connects to Anki, proxies that server, or performs
collection operations. The model passes snapshots and prepared payloads between
the servers. Source-only and supplied-card operations also work offline.

Derived from [Lecture2Cards](https://github.com/Hamza-Xoho/Lecture2Cards). Its
`cards` CLI remains available with its original gate and semantics. See the
[legacy guide](docs/legacy-lecture2cards.md) and [capability mapping](docs/capabilities.md).

## Install and run

Python 3.12+ and POSIX file locking are required (Linux tested; Windows can use WSL or the Linux container). The lockfile is verified with Python 3.14 on Linux;
platform-specific wheels on other Python/OS versions may resolve differently.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
# Install Tesseract through your OS package manager (Ubuntu: tesseract-ocr).
.venv/bin/python -m playwright install chromium
.venv/bin/ankiplusmcp --workspace-root /absolute/workspaces --source-root /absolute/lectures
```

The host starts this command and communicates over stdio. It is not an HTTP
server and needs no open port. Repeat `--source-root` to allow additional readable
input directories. Only requested sources are copied into workspace snapshots;
original files remain unchanged. No credentials or model API key are needed.
Generated data stays under the workspace root. Use a stable absolute root for
resume across sessions; different clients may use the same root with locks and
revision preconditions. Native OCR/render work cancels at operation boundaries,
not by forcibly interrupting Tesseract or Chromium.

`ANKIPLUS_WORKSPACE_ROOT` supplies the default workspace root; otherwise it is
`./workspaces`. Without `--source-root`, the process working directory is allowed.
For predictable access, configure absolute roots explicitly. No global client
configuration is changed by installation.

## Connect your host

Use the absolute installed executable. Configure the official Anki MCP separately
using that server's own instructions; AnkiPlus does not require or assume its URL.

Codex CLI:

```sh
codex mcp add ankiplusmcp -- /absolute/ankiplusmcp/.venv/bin/ankiplusmcp --workspace-root /absolute/workspaces --source-root /absolute/lectures
```

Claude Code:

```sh
claude mcp add --transport stdio ankiplusmcp -- /absolute/ankiplusmcp/.venv/bin/ankiplusmcp --workspace-root /absolute/workspaces --source-root /absolute/lectures
```

OpenCode v2 `opencode.jsonc` (v1 uses the server name directly under `mcp`):

```json
{
  "mcp": {
    "servers": {
      "ankiplusmcp": {
        "type": "local",
        "command": ["/absolute/ankiplusmcp/.venv/bin/ankiplusmcp", "--workspace-root", "/absolute/workspaces", "--source-root", "/absolute/lectures"]
      }
    }
  }
}
```

These examples follow the primary [Codex](https://learn.chatgpt.com/docs/extend/mcp),
[Claude Code](https://code.claude.com/docs/en/mcp), and
[OpenCode](https://opencode.ai/docs/mcp-servers/) documentation checked during
implementation. Real MCP stdio discovery/calls are tested; interactive operation
in those three clients and a live Anki collection is not part of the test suite.

## Using the toolkit

Ask for the outcome you want, for example “make cards from these slides”, “show
me previews of these existing cards”, or “occlude labels on this figure”. Tool
descriptions and typed inputs describe what each helper needs. `capabilities`
reports dependencies and `get_guidance` optionally supplies examples/quality
rubrics. The [companion skill](skills/ankiplusmcp/SKILL.md) can be copied to your
host's skill directory if desired; it is not required or installed automatically.

- Every workspace has an explicit ID and revision. `save_cards` replaces the
  complete workspace card set; `expected_revision` protects against lost edits.
- `extract_source`, `export_figures`, `ocr_image` and `render_cards` return jobs.
  Use `get_job` for status/results and `cancel_job` to request cancellation. Cancellation before publication preserves the current source/preview snapshot; a cancellation arriving after an atomic publication does not undo completed work.
- `get_image` returns an image block. Text and card lists have bounded results;
  follow `next_offset`, reduce the requested selection, or use `read_artifact`.
- Existing-note snapshots can have arbitrary field names. Supply note-type
  templates/CSS or actual question/answer HTML from Anki MCP for closer previews.
  Anki's full template engine, custom filters and add-on JavaScript are not emulated.
- `submit_review` stores proposals; `apply_changes` previews a diff by default.
  Applying changes is explicit. Reviews are optional and reviewer identities
  are labels supplied by the caller, not verified independence.
- `prepare_write` creates payload and import artifacts without writing to Anki.
  Pass their contents to the official Anki MCP. Note IDs and card IDs remain
  distinct; suspension requires actual card IDs, sometimes resolved after creation.
- `record_external_results` stores supplied evidence. Reports label it
  `caller_supplied` and never claim independent Anki verification.

House-style and lecture-coverage checks are optional; technical validation always
applies to prepared payloads. Neither checks nor AI reviews establish factual
accuracy. Legacy build files are not silently migrated into new workspaces.

## Development and checks

```sh
.venv/bin/pip install -e '.[dev]'
./scripts/check-mcp.sh
.venv/bin/python -m build --wheel
```

Tests use synthetic sources/cards, real Chromium, OCR and an SDK stdio client.
The default check includes the original unit suite and synthetic foundational
contracts. Private lecture contract fixtures are not shipped: their absence is
reported as an untested limitation, not hidden by changing frozen tests.

## Optional stdio container

```sh
# Set revision accurately, including the dirty suffix for local changes.
ANKIPLUS_REVISION="$(git rev-parse --short HEAD)"
if test -n "$(git status --porcelain)"; then ANKIPLUS_REVISION="$ANKIPLUS_REVISION-dirty"; fi
export ANKIPLUS_REVISION
export ANKIPLUS_SOURCES=/absolute/lectures
docker compose -p ankiplusmcp config --quiet
docker compose -p ankiplusmcp build
./scripts/run-container.sh "$ANKIPLUS_REVISION" "$ANKIPLUS_SOURCES"
```

This runs an isolated stdio process; it publishes no ports, uses no gateway and
contacts no Anki server. The container is non-root, uses a read-only filesystem,
limited resources, dropped capabilities and no-new-privileges. Source files are
mounted read-only at `/sources`; persistent workspaces use the project volume.
Configure the host to run scripts/run-container.sh with the image revision and source directory as arguments if using this transport. The wrapper refuses a missing image so build logs cannot enter MCP stdout. Existing
media must be imported from the source mount, not arbitrary host paths.

Upstream attribution and MIT terms are retained in [LICENSE](LICENSE).
