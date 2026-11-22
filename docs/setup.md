# Installation and configuration

[Back to the README](../README.md) · [Tool reference](tools.md) · [Developer guide](developer-guide.md)

Use this guide for host registration, configuration, optional dependencies and
unattended installation. The [README quick start](../README.md#quick-start)
contains the shortest path to your first study task.

## Install and register

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

Launcher commands can run with no person present. For commands that ask for
confirmation (`init`, `setup`, `uninstall`), pass `--yes` to skip it.
Administrative commands (`init`, `doctor`, `setup`, `uninstall`) support `--json`
for output a program can read; `serve` uses MCP stdio instead. Without a terminal and
without `--yes`, a command that would ask a question exits at once instead of
waiting. Exit codes: `0` done, `1` declined or only optional tools missing,
`2` error or a required item missing, `3` refused (pass `--yes` or `--force`,
or follow the printed manual step).

### Licences

This project is MIT-licensed. It depends on [PyMuPDF](https://pymupdf.readthedocs.io),
which is AGPL-licensed (a commercial licence is sold separately by its authors).
PyMuPDF is installed from PyPI on your machine and is not redistributed here.
If you ship software that includes it, read its terms.


## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `uv` is missing | Install uv, restart the host so its PATH is refreshed, then run `doctor`. The launcher also checks uv's standard per-user install location. |
| Source is outside readable roots | Register or launch with `--source-root` for its parent directory; use an absolute file path. |
| No tools after registration | Restart/reconnect your AI host, check its MCP logs, and run `doctor`. The server uses stdio; there is no URL or port to open. |
| `DEPENDENCY` error | Follow the remedy returned by the tool. OCR needs system Tesseract; rendering needs an available browser. |
| Preview browser is missing | Run `setup`, or choose an installed Chrome using `--browser chrome` or `browser = "chrome"` in the config file. |
| `STALE` revision | If a job is running, wait for it with `get_job`, then read the workspace again and reconcile the edit with its current cards. Page/image generation and rendering can advance revisions too. Do not blindly repeat the old save. |
| `LABELS_PENDING` | Text is available but figure OCR is still running. Wait for `get_job` to complete before checking coverage. |
| Anki collection operations are unavailable | Configure a separate Anki MCP in your host. AnkiPlus itself cannot connect to Anki. |
| PDF text is garbled although slides look normal | After extraction provides slide data, use `get_page_image` and `get_image` to inspect the slide. A non-empty broken text layer may not trigger OCR replacement. Page viewing does not repair extracted text. |
| House-style checks report a foreign tag tree | Compare draft tags with the active profile/tag root from `capabilities`. Correct the mismatch if that style is intended. Technical-only checks do not establish that disabled style rules passed. |
| `read_source` or `read_artifact` rejects the requested limit | Use at most 24,000 characters and follow `next_offset`; do not increase the limit to force the whole lecture into one response. |
| Companion Anki tool rejects a deck path | Inspect that tool's schema/remedy and current decks. Deck creation limits belong to the installed companion, not AnkiPlus; choose a supported creation/move method before writing. |
| A connection drops during an Anki write | Inspect actual notes/card IDs in Anki before retrying. Resume the saved workspace and retain any previously requested approval-before-write requirement. |

For a full example combining existing-card matching, gap drafts, explanatory
backs and manual review, see the [worked study workflow](study-workflow.md).

Keep your host's logs separate from MCP stdout. For source-only work you do not
need Anki running; Anki connection requirements belong to the separately installed
Anki MCP. AnkiPlus needs no model API key, but your AI host may require an account
or model-provider credentials.
