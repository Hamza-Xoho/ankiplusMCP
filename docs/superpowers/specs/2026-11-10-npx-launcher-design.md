# npx launcher and public repository design

Status: approved by the author on 2026-11-10. Nothing here is built yet.

This covers the first two of five pieces of work. The other three (efficacy
refactor and the Anki bridge decision, skill unification, registry publishing)
get their own designs later.

## Intent

Let a stranger go from nothing to a working AnkiPlus MCP in their AI host with
one command, and let an agent do the same without a human. Today that takes a
clone, a venv, a lockfile install, a system package, a browser download and
hand-edited absolute paths in each host's config.

## Goals

- `npx -y ankiplusmcp` starts the stdio MCP server on macOS and Linux.
- `npx ankiplusmcp init` registers the server in the user's host and installs
  the `ankiplusmcp` skill. The two reviewer agents belong to the older `anki2`
  pipeline and are left to the skill work in piece 4.
- `npx ankiplusmcp doctor` says exactly what is missing and the command to fix it.
- It works straight from GitHub (`npx github:Hamza-Xoho/ankiplusMCP`) before
  anything is published to npm or PyPI.
- Every launcher command can run with no human present: `--yes` answers the
  questions, `--json` gives machine-readable output, and exit codes say what
  happened. An agent must be able to install and check this by itself.
- Defaults are safe and sensible for someone who is not the author.
- The author's current setup keeps working unchanged.

## Non-goals (this piece)

- Reducing the 33 tools, the core-library refactor, or any change in `src/cards/`.
- Connecting to Anki. The boundary in the 2026-11-07 design stands until piece 3.
- Rewriting or merging the skills.
- Publishing to npm, PyPI or the MCP registry. That is piece 5, after the tool
  API settles.
- A TypeScript port.
- Guaranteed Windows support. The design only stops ruling it out.

## Anti-goals

- The launcher writing anything to stdout. Stdout belongs to the MCP protocol.
- `init` changing a config file or overwriting a skill without showing the
  change first.
- Downloading and running binaries (uv, Chromium) without the user asking.
- Publishing private development history or personal paths.

## Approaches considered

1. **uvx only.** `uvx --from git+https://github.com/Hamza-Xoho/ankiplusMCP ankiplusmcp`.
   Almost works today and needs no Node code. Rejected as the only route
   because it is not npx, and it gives no place for host setup.
2. **npm launcher over uvx. Chosen by the user on 2026-11-10.** A small Node
   package finds `uv` and runs the Python server through `uvx`. It also carries
   `init` and `doctor`. Python stays the implementation; uvx remains a
   documented second way in.
3. **Full TypeScript port.** True native npx with no Python. Rejected: it
   rewrites about 6,600 lines and their tests, and risks regressions in
   extraction and OCR quality for no gain the launcher does not already give.

## Part 1: the repository

Findings that shape this:

- This folder is not a git repository. It is a bundle cut from commit `5bb2530`.
- The public `Lecture2Cards` repository is a single squashed commit that does
  not contain `5bb2530`. The detailed history lives only in a private local clone.
- Only seven tracked files differ from `5bb2530`; the rest of the change is new
  files (`src/ankiplusmcp/`, `tests/mcp/`, docs, container files).
- Frozen tests read `.claude/`, `.codex/`, `CLAUDE.md` and `settings.json`, so
  those cannot move in this piece.

Design:

- **Repository: `https://github.com/Hamza-Xoho/ankiplusMCP`**, named by the
  author on 2026-11-10. It is public and empty (no commits, no default branch),
  so the first push is visible to everyone at once. The privacy sweep below
  therefore comes before that push, and the push waits for the author's go-ahead.
- **Fresh history.** One initial commit on `main`, the same way Lecture2Cards
  was released. The private history stays private. README and LICENSE keep
  crediting Lecture2Cards. *(My call.)*
- **Names.** The repository is `ankiplusMCP`; the npm package, the Python
  package and the command stay lowercase `ankiplusmcp`, because npm requires
  lowercase names.
- **Nothing of the author's is moved.** `builds/` and `workspaces/` are already
  git-ignored. The legacy tree (`.claude/`, `.codex/`, `.agents/`, `prompts/`)
  stays where the tests expect it. Sorting product from workspace is piece 4.
- **Privacy sweep before the first commit.** Known leaks: a home-directory path
  with a person's name in `docs/superpowers/specs/2026-11-07-ankiplusmcp-design.md`
  (line 62) and `docs/phase4-review.md` (lines 43 and 76). Replace with
  placeholders. Add a CI check that fails on `/Users/<name>/`, `/home/<name>/`
  and email addresses in tracked files.
- **Remove stale bundle files.** `BUNDLE.txt` describes a snapshot that no
  longer applies. `dist/` and `*.egg-info/` are already ignored.
- **Licence note.** The project is MIT, but PyMuPDF is AGPL-licensed. The
  README says so plainly, and the project does not redistribute PyMuPDF itself
  (users get it from PyPI). This is a reason not to ship fat bundles. Not legal
  advice; the author decides whether that is acceptable for a public project.

## Part 2: the launcher

### Layout

```
package.json          name ankiplusmcp, bin -> launcher/cli.mjs, no runtime dependencies
launcher/cli.mjs      argument routing only
launcher/lib/         uv lookup, spawn, host adapters, config edit, skill install
launcher/test/        node:test suites
pyproject.toml        Python package (unchanged location)
skills/ankiplusmcp/   skill shipped to hosts
```

`package.json` sits at the repository root because that is what
`npx github:<owner>/<repo>` installs. A `files` allowlist keeps the npm package
to the launcher and the skill. Node 18 or newer.

### Commands

| Command | What it does |
|---|---|
| *(none)* or `serve [flags]` | Finds `uv`, runs `uvx --from <spec> ankiplusmcp <flags>` with stdio passed straight through. Forwards signals and the exit code. |
| `init` | Registers the server in a host and installs the skill. |
| `doctor` | Checks Node and `uv` itself, then hands over to the Python `doctor`. |
| `setup` | Installs Chromium for previews after stating the download size and asking. Prints the Tesseract install command for the user's OS. |
| `uninstall` | Removes what `init` added, using the record `init` wrote. |
| `--version` | Launcher and Python versions. |

**The Python spec.** While unpublished:
`git+https://github.com/Hamza-Xoho/ankiplusMCP@v<version>`. After piece 5:
`ankiplusmcp==<version>` from PyPI. The launcher's own version decides the
Python version, so the two cannot drift. `ANKIPLUSMCP_PY_SPEC` overrides it for
development and tests.

**When `uv` is missing.** Exit non-zero with one stderr message giving the
official install command. The launcher does not fetch `uv` itself.

**`init` behaviour.**

- Hosts: Claude Code, Claude Desktop, Codex and OpenCode, plus Hermes Agent if
  the builder confirms how it registers stdio MCP servers. `--print` emits a
  generic stdio snippet for any other host.
- Uses the host's own command (`claude mcp add`, `codex mcp add`) when present;
  edits the config file only when there is no such command.
- Shows the exact change and asks before writing. `--yes` skips the question
  for agents; `--dry-run` only shows it.
- Backs up any file it edits. Never replaces an existing `ankiplusmcp` entry or
  a differing skill copy without `--force`. Running it twice changes nothing.
- Flags: `--host`, `--scope user|project`, `--source-root` (repeatable),
  `--workspace-root`, `--profile`.
- Ends by running the server once so the first start inside the host is not
  the slow one, then runs `doctor`.
- Records what it installed so `uninstall` is exact.

### Python changes (MCP layer only)

- **Subcommands.** `ankiplusmcp serve|doctor|setup`, with bare flags still
  meaning `serve` so existing host configs keep working.
- **Workspace root default.** The platform data directory instead of
  `./workspaces`. Under npx the working directory is whatever the host picked.
  The flag and `ANKIPLUS_WORKSPACE_ROOT` still win.
- **Source roots default.** Order: flags, then `ANKIPLUS_SOURCE_ROOTS`, then
  the folders the MCP client offers as roots, then the working directory only
  if it is not the filesystem root or the home directory. Otherwise none, with
  an error that names the fix. Today the default is the working directory,
  which under some hosts is `/`.
- **Profiles.** A small config file (`config.toml` in the platform config
  directory, or `--config`) with `note_type` and `tag_root`. The built-in
  default is generic (Anki's stock `Cloze`, tag root `#AnkiPlus`). A
  `coldrecall` profile reproduces today's behaviour exactly, and the author's
  install selects it, so nothing changes for them. `target.build` already takes
  `root`, so this needs no change in `src/cards/`. *(My call.)*
- **Optional dependencies.** Extras `ocr` and `render`; the launcher installs
  both by default. Missing Tesseract or Chromium returns a `DEPENDENCY` error
  with the fix, and `capabilities` reports it. There is no Tesseract-missing
  handling today.
- **Dependency pins.** Compatible-release pins in `pyproject.toml` in place of
  exact pins, plus a committed `uv.lock` for development. uvx does not read the
  lockfile, so the pins must be tight enough on their own.
- **File locking.** Replace `fcntl` in `store.py` and `jobs.py` with a
  cross-platform lock. This is the only thing excluding Windows.
- **One version.** Read from package metadata; `server.py` hardcodes `0.1.0`
  today. CI fails if `package.json` and `pyproject.toml` disagree.

Deferred to piece 3 because it needs a change in `src/cards/render/`: using the
system's Chrome to avoid the Chromium download.

## Unattended use inside agent systems

The author's stated direction (2026-11-10): this will run as one part of
automated agent systems. The example given: a WhatsApp archiver saves lecture
files from a group chat, an agent (Hermes, for instance) notices them, works
out which lecture they are, and has the cards made ahead of time.

AnkiPlus stays a tool in that chain. Watching chats, scheduling and deciding
which file is which lecture belong to the system around it, not to this package.

What this piece contributes: an agent can install, register and health-check
the server with no human (`--yes`, `--json`, exit codes), and any host that
speaks stdio MCP can start it with one command.

What it does not solve, recorded here so the later designs pick it up:

- **The method must live in the server.** An unattended agent on another host
  has no Claude Code skill, hooks or reviewer agents. Checks and any gate before
  writing have to be enforced by the server, not requested by a skill.
- **Anki is often closed when the automation runs.** The useful end state is a
  staged workspace that is ready to write, not a write. This bears directly on
  the Anki bridge decision in piece 3.
- **Repeat deliveries.** The same file will arrive twice. `create_workspace`
  makes a new workspace every time; it needs to recognise a source it has
  already seen by its hash.
- **Readable state.** Workspaces are bare IDs with no label or stage. An agent
  resuming later, or a person skimming, needs "which lecture, what stage, what
  next".
- **A plain command-line face.** Mechanical steps such as extraction should be
  runnable from a script with JSON in and out, without a model in the loop.
- **File types.** Lecturers send PowerPoint files; only PDF, text and Markdown
  are accepted today.
- **Untrusted input.** Files from a group chat are processed by an agent that
  can reach the user's collection. Source text is data, never instructions, and
  nothing unattended should be able to skip the server's checks.

## Testing

- **Launcher units** with a fake `uv` on `PATH`: spec building, flag
  pass-through, nothing on stdout, exit-code and signal forwarding, the
  missing-`uv` message.
- **`init`** against a temporary home with fixture configs for each host:
  dry-run output, backup, refusal to overwrite, second run is a no-op,
  `uninstall` restores the original.
- **End to end in CI** on Ubuntu and macOS: `npm pack`, run the tarball with
  `ANKIPLUSMCP_PY_SPEC` pointing at the locally built wheel, complete an MCP
  handshake and a tool listing.
- **Python:** the existing 149 MCP and unit tests keep passing. New tests for
  default paths, source-root resolution, profiles, `doctor` output and the new
  lock.
- **Manual, reported honestly:** one real `init` into Claude Code on the
  author's machine. Other hosts are covered by fixtures only unless tried.

## Left to the builder

- Exact config formats and commands per host, checked against each host's
  current documentation at build time.
- How to read client roots through the Python MCP SDK in use.
- Whether a pinned `npx -y ankiplusmcp@<version>` avoids a registry round trip
  on every start, and the measured cold and warm start times. If cold start
  risks a host timeout, `init`'s warm-up run is the mitigation.
- Flag spellings and message wording.
- Where each host keeps skills, and the skill-install step for hosts that have
  no such place.
- The git spec needs a `v<version>` tag to exist. Until the first tag, the
  launcher points at `main`.
- The npm name `ankiplusmcp` has not been checked for availability. Fallback:
  a scoped name under the owner's account.

## Decisions for the author

1. Settled: the repository is `Hamza-Xoho/ankiplusMCP`. Still open: a fresh
   single-commit history, and the go-ahead for the first push.
2. Generic default profile for strangers, `coldrecall` profile for the author.
3. PyMuPDF's AGPL licence as a dependency of a public MIT project.
