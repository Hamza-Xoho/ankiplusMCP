# AnkiPlus MCP

Mac OCR/doctor follow-up: [new pinned packet and narrow retest](docs/refactor/macos-ocr-retest.md).
For local wheels, request `ankiplusmcp[all] @ file:///absolute/wheel.whl`; a bare
wheel omits Playwright. Desktop workflow is available through
`get_guidance(topic="workflow")`; connector registration does not install a
Desktop filesystem skill.

This branch connects student onboarding, source evidence, approved collection
coverage, source-linked review, quality enforcement, exact authorization,
conditional application, readback, recovery and permanent history. Offline
extraction, OCR, image occlusions, card checks and previews remain available.

Collection access uses an explicitly configured loopback companion. Every write
requires a current proposal, required independent quality evidence and exact user
or saved-policy authorization. Real Mac acceptance and prescribed reviewer runtime
controls remain gates; Linux synthetic checks do not establish those capabilities.
See [student workflow](docs/refactor/student-workflow.md),
[local acceptance](docs/refactor/acceptance.md) and the
[Mac packet](docs/refactor/macos-acceptance.md).

This development branch has not been released or deployed. The version 0.3.0
installation examples below describe the historical mechanical-helper package.
Use the revision-pinned checkout and local launcher in the Mac packet for this
branch. Do not infer Windows, alternate-host or production note-type support from
packaging tests.

Derived from [Lecture2Cards](https://github.com/Hamza-Xoho/Lecture2Cards). Its
`cards` CLI remains available with its original gate and semantics. See the
[legacy guide](docs/legacy-lecture2cards.md) and [capability mapping](docs/capabilities.md).

## Historical 0.3.0 installation

You need [Node](https://nodejs.org) 18 or newer and [uv](https://docs.astral.sh/uv/).
uv fetches Python and the server's dependencies for you. macOS and Linux are
supported; Windows is untested.

Register the server in your AI host with one command:

```sh
npx -y github:Hamza-Xoho/ankiplusMCP#v0.3.0 init --host claude-code --source-root /absolute/lectures
```

`init` shows every change before it makes it, backs up any file it edits, and
installs the companion skill where the host has a place for one. It never
replaces an existing `ankiplusmcp` entry or a skill copy you have edited unless
you pass `--force`. It finishes by starting the server once, because the very
first start downloads dependencies and can take a minute or more.

| Flag | Meaning |
| --- | --- |
| `--host` | `claude-code`, `claude-desktop`, `codex`, `opencode` or `hermes`. Needed when more than one is installed. |
| `--scope` | `user` (default) or `project`, where the host supports project config. |
| `--source-root DIR` | A directory the server may read lectures from. Repeatable. |
| `--workspace-root DIR` | Where workspaces are kept. Defaults to your per-user data directory. |
| `--profile NAME` | `default` or `coldrecall` (see Profiles). |
| `--dry-run` | Show what would change and stop. |
| `--yes` | Do not ask for confirmation. |
| `--print` | Print a generic config snippet for any other host and change nothing. |
| `--json` | Machine-readable result on stdout. |

How each host is registered:

| Host | What `init` does |
| --- | --- |
| Claude Code | User scope runs `claude mcp add`; project scope edits `.mcp.json`. Skill goes to `.claude/skills/`. |
| Claude Desktop | Edits `claude_desktop_config.json`. |
| Codex | Runs `codex mcp add`. |
| OpenCode | Edits `opencode.json` (`mcp.servers`, the v2 layout). |
| Hermes Agent | Prints the YAML to add to `~/.hermes/config.yaml`; it does not edit YAML. |

Registration is covered by automated tests against sample config files. On a
real machine only Claude Code has been tried, and only as a dry run; treat the
others as untested until you have run them once.

The other commands:

```sh
npx -y github:Hamza-Xoho/ankiplusMCP#v0.3.0 doctor      # what is missing, and the command that fixes it
npx -y github:Hamza-Xoho/ankiplusMCP#v0.3.0 setup       # download Chromium for card previews (asks first)
npx -y github:Hamza-Xoho/ankiplusMCP#v0.3.0 uninstall   # remove exactly what init added
```

OCR needs the Tesseract program (`brew install tesseract`, or
`sudo apt-get install -y tesseract-ocr`). Card previews need a browser: either
Chromium, which `setup` installs, or Google Chrome. If Google Chrome is
installed, you do not need to run `setup`. Everything else works without
either, and a tool that needs a missing one returns a `DEPENDENCY` error naming
the fix.

### Choosing the preview browser

By default (`auto`) the server uses Playwright's Chromium when it is installed,
and otherwise Google Chrome. To choose, pass `--browser` to `serve`, `doctor`
or `setup`, or set `browser` in `config.toml`. The flag wins over the file.
All three also take `--config` to name the config file. `setup` downloads
Chromium only when the chosen setting finds no browser.

| Value | Meaning |
| --- | --- |
| `auto` | Chromium if installed, else Google Chrome. The default. |
| `chromium` | Only Playwright's Chromium. |
| `chrome` | Only the installed Google Chrome. |
| An absolute path | That browser program. The file must exist. |

```toml
browser = "chrome"
```

`doctor` shows which browser it found, and `setup --json` and the
`capabilities` tool report it too.

### Without npx

The launcher only finds uv and starts the Python program. You can do that
yourself:

```sh
uvx --from "ankiplusmcp[all] @ git+https://github.com/Hamza-Xoho/ankiplusMCP@v0.3.0" ankiplusmcp --source-root /absolute/lectures
```

The server speaks MCP over stdio. It is not an HTTP server and opens no port.
No credentials or model API key are needed.

### Where things go

- **Workspaces** live in your per-user data directory
  (`~/Library/Application Support/ankiplusmcp/workspaces` on macOS,
  `~/.local/share/ankiplusmcp/workspaces` on Linux). Override with
  `--workspace-root` or `ANKIPLUS_WORKSPACE_ROOT`.
- **Readable source directories** are taken from the first of these that is
  set: `--source-root` flags; `ANKIPLUS_SOURCE_ROOTS` (separated like `PATH`);
  the folders your host offers as MCP roots; the directory the server was
  started in, unless that is `/` or your home directory. If none applies the
  server can read no source files and says so.

Only requested sources are copied into a workspace; original files are never
changed. Native OCR and rendering cancel at operation boundaries, not by
interrupting Tesseract or Chromium mid-run.

### Profiles

A profile sets the note type used when a card does not name one, and the root
of suggested tags.

| Profile | Note type | Tag root |
| --- | --- | --- |
| `default` | `Cloze` (Anki's own) | `#AnkiPlus` |
| `coldrecall` | `ColdRecall Cloze` | `#ColdRecall` |

Choose one with `--profile`, or put a `config.toml` in your per-user config
directory (or point `--config` / `ANKIPLUS_CONFIG` at one):

```toml
profile = "coldrecall"   # optional starting point
note_type = "My Cloze"   # optional override
tag_root = "#Medicine"   # optional override
```

### Running unattended

Every launcher command can run with no person present. Pass `--yes` to skip
confirmation and `--json` for output a program can read. Without a terminal and
without `--yes`, a command that would ask a question exits at once instead of
waiting. Exit codes: `0` done, `1` declined or only optional tools missing,
`2` error or a required item missing, `3` refused (pass `--yes` or `--force`,
or follow the printed manual step).

### Licences

This project is MIT-licensed. It depends on [PyMuPDF](https://pymupdf.readthedocs.io),
which is AGPL-licensed (a commercial licence is sold separately by its authors).
PyMuPDF is installed from PyPI on your machine and is not redistributed here.
If you ship software that includes it, read its terms.

## Using the toolkit

Ask for the outcome you want, for example “make cards from these slides”, “show
me previews of these existing cards”, or “occlude labels on this figure”. Tool
descriptions and typed inputs describe what each helper needs. `capabilities`
reports dependencies and `get_guidance` optionally supplies examples/quality
rubrics. The [companion skill](skills/ankiplusmcp/SKILL.md) is optional; `init` installs
it for hosts that have a skill directory.

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
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m playwright install chromium
./scripts/check-mcp.sh        # Python tests, frozen-contract hashes, wheel build
npm test                      # launcher tests (Node 18+, no dependencies)
```

The npm launcher lives in `launcher/`; it has no runtime dependencies. Its
version in `package.json` must equal the one in `pyproject.toml`
(`scripts/check_versions.py`), because the launcher installs the Python package
tagged with its own version. To run the launcher against your checkout, set
`ANKIPLUSMCP_PY_SPEC="ankiplusmcp[all] @ file://$PWD"`.

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

## Student-workflow product in this checkout

The connected durable run path is described in [student workflow](docs/refactor/student-workflow.md). It connects source evidence, scoped companion reads, review, quality evidence, exact authorization, guarded application, recovery and verified onboarding. Actual Mac embedding, prescribed reviewer controls and private acceptance remain separate gates.

- `get_source_evidence` resolves a source hash, physical page/section and optional quotation against stored extraction. It returns the exact source substring, distinguishes printed PDF labels from physical page numbers and labels OCR text. It does not establish factual accuracy.
- `patch_cards` merges supplied note fields into selected draft IDs, preserves untouched drafts, rejects stale revisions and avoids resending the full set for one correction. It never writes to Anki.
- `list_jobs` rediscovers job IDs with bounded summaries. Workspaces now have labels and activity timestamps; old unknown dates stay unknown.
- Coverage decision records preserve source passages, collection snapshot IDs and actual card-vs-note identities. The student-run adapter obtains verified scoped companion readback; legacy supplied collection evidence retains caller-supplied provenance.

Inspect or export run history separately from card review:

```sh
.venv/bin/python -m ankiplusmcp history list --workspace-root /absolute/data --json
.venv/bin/python -m ankiplusmcp history list --workspace-root /absolute/data --card-id 123456 --json
.venv/bin/python -m ankiplusmcp history show RUN_ID --workspace-root /absolute/data
.venv/bin/python -m ankiplusmcp history export RUN_ID --workspace-root /absolute/data --output /absolute/run-summary.md
.venv/bin/python -m ankiplusmcp history import-legacy WORKSPACE_ID --workspace-root /absolute/data --from /absolute/legacy-workspace --json
```

Exports do not overwrite existing files, and legacy import does not modify the original workspace or invent verification. The student workflow uses durable run/configuration/guide stores. Legacy mechanical helpers remain explicit offline utilities; installing this branch alone does not complete verified onboarding. The guide writer preserves its personal-notes section and refuses to overwrite other user edits.

See [the approved design](docs/superpowers/specs/2026-11-18-student-workflows-design.md), [implementation plan](docs/superpowers/plans/2026-11-18-student-workflows.md) and [verification checkpoint](docs/refactor/implementation-checkpoint.md). To use this checkout through the launcher, set `ANKIPLUSMCP_PY_SPEC` as documented above; the released version tag does not contain unpushed branch changes.

### Historical pre-macOS refactor investigation

The source catalog, artifact publisher, authoritative run discovery and shared coverage batches are internal refactors; they do not establish Desktop or release compatibility. Run the disposable synthetic rehearsal with `.venv/bin/python scripts/smoke-premacos.py --output .artifacts/premacos/smoke.json` (fresh output only). It uses real extraction, OCR and Chromium with zero Anki operations. See [local evidence](docs/refactor/premacos-readiness.md) and the [ordered Mac test packet](docs/refactor/macos-test-packet.md). That rehearsal predates the connected product. Current installed companion/coordinator/onboarding acceptance uses `tests/isolated/compose.yaml`; prescribed host reviewers and private/Mac acceptance remain gates in [the current packet](docs/refactor/macos-acceptance.md).

For a local test build, set `ANKIPLUSMCP_NPX_REF` to its launcher `.tgz` and `ANKIPLUSMCP_PY_SPEC` to its absolute wheel path before `init`. Local launcher paths become absolute `file:` references. Init records the Python override and resolved uv executable in the host registration, so restarted Desktop does not depend on the installer's shell PATH. `ANKIPLUSMCP_UV` explicitly selects a nonstandard uv location. Only these runtime dependencies are persisted, not the full shell environment.

Uninstall preserves entries edited since installation. It exits **3** and retains their install records when removal is incomplete; restore the recorded entry before retrying, or resolve that entry explicitly. Backups are retained. See [Mac lifecycle evidence and retesting](docs/refactor/macos-host-lifecycle.md).

### Experimental student workflow integration

The `refactor/student-workflows` branch is not a finished student product.
`get_student_setup`, `propose_preferences` and `confirm_preferences` expose saved
preferences through MCP. Confirmation regenerates `Start here — AnkiPlus.md`
under `<workspace-root>/.student-workflows/`, preserving its personal notes.
The completion flag stays false while required setup/quality/UI gates are open.

Collection coverage reads are opt-in. Configure the existing local companion
with `serve --companion-url http://127.0.0.1:<port>/mcp --anki-profile <name>
--anki-collection-path <absolute-path>`. An optional `--companion-token-file`
reads the existing bearer key from a private file; never paste keys into command
arguments or source. These options do not install, launch or reconfigure Anki.
The default remains disconnected. `search_collection_coverage` retrieves at most
500 complete notes, with actual note/card ownership and suspended card IDs.
Overflow, missing records, excerpts and changed sessions refuse the read.
Retrieved coverage is not proof of semantic matching or an authorization to write.

The narrow adapter requires the versioned companion conditional-operation
extension for guarded state reads/writes. Installed older companions fail closed.
No coordinator apply/reconciliation tools or production review UI are provided
by this checkpoint. The container remains network-disabled and cannot connect to
a host companion; these optional native connection flags do not change that.
