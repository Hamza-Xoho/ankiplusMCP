# npx Launcher and Public Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command (`npx -y ankiplusmcp`) starts the AnkiPlus MCP server, `init` registers it in an AI host, `doctor` diagnoses it, and the project lives in a clean public git repository.

**Architecture:** Python stays the implementation. A dependency-free Node package at the repository root finds `uv` and runs the Python server through `uv tool run`, passing stdio straight through. The same Node package carries `init`, `doctor`, `setup` and `uninstall`. The Python MCP layer gains safe defaults, profiles, subcommands and cross-platform locking; `src/cards/` is not touched.

**Tech Stack:** Python 3.12+ (`mcp`, `pydantic`, `platformdirs`, `filelock`), Node 18+ (`node:test`, no runtime dependencies), `uv`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-10-npx-launcher-design.md`

## Global Constraints

- Do not edit `src/cards/`, the frozen tests listed in `.codex/contract.sha256`, `.claude/`, `.codex/` or `.agents/`.
- The launcher writes nothing to stdout while serving. All launcher messages go to stderr.
- No Anki connection, no Anki proxy, no collection operations.
- The launcher never downloads `uv`. Chromium is downloaded only by `setup`, after asking or with `--yes`.
- `init` shows every change before writing, backs up every file it edits, and never replaces an existing `ankiplusmcp` entry or a differing skill copy without `--force`.
- A command with no TTY and no `--yes` exits with code 3 at once. It never waits for input.
- Node 18 or newer. `package.json` has no `dependencies`.
- Python 3.12 or newer. macOS and Linux are supported; nothing may import `fcntl` in `src/ankiplusmcp/`.
- Names: repository `Hamza-Xoho/ankiplusMCP`; npm package, Python distribution and command are lowercase `ankiplusmcp`.
- Version is `0.2.0` in both `package.json` and `pyproject.toml`. `cards.__version__` stays `0.1.0` (frozen tests assert it).
- No `git push`, no tag push and no edit of the author's real host config without the author's explicit go-ahead in chat.
- Use `.venv/bin/python` for Python commands.

**History note:** the spec's "fresh history" means the private development history is not published. Task 1 creates the first commit; later tasks add ordinary commits on top. All of it is pushed in Task 10.

**Tag note:** the spec allows the launcher to point at `main` until a tag exists. This plan pins `v0.2.0` from the start and pushes that tag with the first push, so there is no untagged period.

## Review Focus

1. **A path containing spaces** (`~/Library/Application Support/...`, Google Drive's `My Drive`) given as `--source-root`: it must reach Python as one argument and be written to host config as one array element. Tests in Tasks 7 and 8.
2. **A host config file that is not strict JSON** (comments, trailing commas, truncated): `init` must leave it byte-identical, print the snippet to add by hand, and exit 3. Test in Task 8.
3. **No TTY and no `--yes`** (an agent or CI runs `init`/`setup`): exit 3 immediately, no hang. Tests in Tasks 6 and 8.
4. **The working directory is `/` or the home directory** and no roots are configured (Claude Desktop starts servers this way): no source roots are granted, and `create_workspace` with a path returns a `SOURCE` error naming `--source-root`. Test in Task 4.
5. **`uv` exists but the Python run fails** (offline first run, bad spec): the child's stderr and non-zero exit code reach the caller unchanged, and nothing is printed on stdout. Test in Task 7.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/check_privacy.py` | Fail on personal paths and emails in tracked files |
| `scripts/check_versions.py` | Fail when `package.json` and `pyproject.toml` versions differ |
| `src/ankiplusmcp/settings.py` | Default paths, source-root resolution, profiles, config file |
| `src/ankiplusmcp/doctor.py` | Dependency checks, `require()`, `doctor` and `setup` commands |
| `src/ankiplusmcp/__main__.py` | Subcommand routing only |
| `src/ankiplusmcp/store.py`, `jobs.py` | Same behaviour, `filelock` in place of `fcntl` |
| `package.json` | npm metadata, `bin`, `files` allowlist |
| `launcher/cli.mjs` | Argument routing only |
| `launcher/lib/uv.mjs` | Find `uv` |
| `launcher/lib/spec.mjs` | Python spec, npx reference, version |
| `launcher/lib/serve.mjs` | Spawn and forward |
| `launcher/lib/hosts.mjs` | One adapter per host: where config and skills live |
| `launcher/lib/configfile.mjs` | Strict-JSON read, backup, edit |
| `launcher/lib/init.mjs` | Plan, show, apply, record; `uninstall` |
| `launcher/test/*.test.mjs`, `launcher/test/fixtures/` | Launcher tests, fake `uv`, host config fixtures |

---

### Task 1: Git repository and privacy sweep

**Files:**
- Create: `scripts/check_privacy.py`, `tests/unit/test_privacy_check.py`
- Modify: `.gitignore`, `docs/superpowers/specs/2026-11-07-ankiplusmcp-design.md:62`, `docs/phase4-review.md:43,76`
- Delete: `BUNDLE.txt`

**Interfaces:**
- Produces: `scripts/check_privacy.py` — `find_leaks(paths: list[Path]) -> list[tuple[Path, int, str]]`; `main()` scans `git ls-files`, prints `path:line: match` per leak, exits 1 if any, else 0.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_privacy_check.py
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location('check_privacy', Path(__file__).parents[2]/'scripts/check_privacy.py')
cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)

def write(tmp_path, text):
    p = tmp_path/'f.md'; p.write_text(text); return [p]

def test_flags_named_home_paths_and_emails(tmp_path):
    assert cp.find_leaks(write(tmp_path, 'see /home/alice/projects/x'))
    assert cp.find_leaks(write(tmp_path, 'see /Users/bob/Code/x'))
    assert cp.find_leaks(write(tmp_path, 'mail carol@example.org'))

def test_allows_placeholders_and_decorators(tmp_path):
    ok = '/Users/<name>/x /home/<name>/x /home/user/x /absolute/path\n+@pytest.mark.skip\nnoreply@anthropic.com'
    assert cp.find_leaks(write(tmp_path, ok)) == []
```

- [ ] **Step 2: Run it** — `.venv/bin/python -m pytest tests/unit/test_privacy_check.py -q` — Expected: FAIL (file missing).

- [ ] **Step 3: Implement `find_leaks` and `main` in `scripts/check_privacy.py`**

Path rule: `/(Users|home)/<segment>/` where segment is not in `{'<name>', 'user', 'me', 'app', 'runner'}`. Email rule: local part starts with a letter or digit; allowlist `{'noreply@anthropic.com'}`. Skip binary files.

- [ ] **Step 4: Run it** — Expected: PASS.

- [ ] **Step 5: Initialise git and sweep**

```bash
git init -b main
```

Add `node_modules/` and `*.tgz` to `.gitignore`. Delete `BUNDLE.txt`. Replace the three known home-directory paths with `/home/<name>/...`. Then run `git add -A && .venv/bin/python scripts/check_privacy.py`; fix every remaining line it prints by replacing the personal part with a placeholder. Expected final output: nothing, exit 0.

- [ ] **Step 6: Confirm nothing private is staged**

Run: `git status --short | grep -E '^A.*(workspaces/|builds/|\.venv/|\.claude-flow/|\.env$)'`
Expected: no output.

- [ ] **Step 7: Run the existing suites** — `.venv/bin/python -m pytest -q tests/mcp tests/unit` — Expected: 151 passed (149 existing + 2 new).

- [ ] **Step 8: Commit**

```bash
git commit -m "Initial public release of AnkiPlus MCP"
```

---

### Task 2: Python packaging: one version, compatible pins, extras

**Files:**
- Modify: `pyproject.toml`, `src/ankiplusmcp/server.py:34`, `requirements.lock` (regenerate), `Dockerfile` (install `.[all]`)
- Create: `uv.lock`, `tests/mcp/test_packaging_meta.py`

**Interfaces:**
- Produces: distribution version `0.2.0`; extras `ocr`, `render`, `all`, `dev`; `capabilities()['version']` read from metadata.

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp/test_packaging_meta.py
import importlib.metadata, tomllib
from pathlib import Path
from ankiplusmcp.service import Service
from ankiplusmcp.server import API
ROOT = Path(__file__).parents[2]

def test_version_comes_from_metadata(tmp_path):
    s = Service(tmp_path, [tmp_path])
    try: assert API(s).capabilities()['version'] == importlib.metadata.version('ankiplusmcp') == '0.2.0'
    finally: s.close()

def test_pins_and_extras():
    project = tomllib.loads((ROOT/'pyproject.toml').read_text())['project']
    assert not any('==' in d for d in project['dependencies'])
    assert {'ocr', 'render', 'all', 'dev'} <= set(project['optional-dependencies'])
    names = ' '.join(project['dependencies']).lower()
    assert 'playwright' not in names and 'pytesseract' not in names
    assert 'platformdirs' in names and 'filelock' in names
```

- [ ] **Step 2: Run it** — Expected: FAIL (`0.1.0`, exact pins).

- [ ] **Step 3: Edit `pyproject.toml`**

```toml
version = "0.2.0"
dependencies = ["mcp~=1.30", "pydantic~=2.14", "PyMuPDF~=2.1", "pillow~=13.0", "numpy~=2.5", "platformdirs>=4.2", "filelock>=3.13"]

[project.optional-dependencies]
ocr = ["pytesseract~=0.3.13"]
render = ["playwright~=1.64"]
all = ["ankiplusmcp[ocr,render]"]
dev = ["ankiplusmcp[all]", "pytest>=8", "build"]
```

In `server.py`, replace the literal `'0.1.0'` with `importlib.metadata.version('ankiplusmcp')`.

- [ ] **Step 4: Reinstall and lock**

```bash
.venv/bin/pip install -e '.[dev]'
uv lock
uv export --extra all --no-dev --no-hashes --no-emit-project -o requirements.lock
```

- [ ] **Step 5: Run** `.venv/bin/python -m pytest -q tests/mcp tests/unit` — Expected: all pass.

- [ ] **Step 6: Commit** — `git add -A && git commit -m "build: single version source, compatible pins, ocr/render extras"`

---

### Task 3: Cross-platform file locking

**Files:**
- Modify: `src/ankiplusmcp/store.py:3,70-76`, `src/ankiplusmcp/jobs.py:3,12-13,50-60,69-71`
- Test: `tests/mcp/test_locking.py`

**Interfaces:**
- Consumes: `filelock` (Task 2).
- Produces: unchanged signatures `Store.lock(ident, name='workspace')`, `Jobs.get`, `Jobs.close`. New behaviour: `Jobs.close()` deletes its own `.owner-<id>.lock` file.

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp/test_locking.py
from pathlib import Path
from ankiplusmcp.store import Store
from ankiplusmcp.jobs import Jobs
SRC = Path(__file__).parents[2]/'src/ankiplusmcp'

def test_no_posix_only_locking():
    assert all('fcntl' not in p.read_text() for p in SRC.glob('*.py'))

def test_dead_owner_marks_job_interrupted_and_live_owner_does_not(tmp_path):
    store = Store(tmp_path, [tmp_path]); w = store.create('cards')['id']
    a, b = Jobs(store), Jobs(store)
    store.write_json(w, 'jobs/j1.json', {'id':'j1','owner':a.owner,'operation':'x','status':'running','progress':'','cancel_requested':False})
    assert b.get(w, 'j1')['status'] == 'running'
    a.close()
    assert not (tmp_path/f'.owner-{a.owner}.lock').exists()
    assert b.get(w, 'j1')['status'] == 'interrupted'
    b.close()
```

- [ ] **Step 2: Run it** — Expected: FAIL on `fcntl`.

- [ ] **Step 3: Replace `fcntl` with `filelock.FileLock`**

`Store.lock`: `with FileLock(path): yield`. `Jobs.__init__`: hold `FileLock(lease_path)` acquired for the process lifetime. `Jobs.get` liveness probe: `FileLock(lease_path).acquire(timeout=0)` raising `filelock.Timeout` means the owner is alive; release at once if acquired. Create a new `FileLock` object per call so two threads in one process still exclude each other.

- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q tests/mcp` — Expected: all pass.

- [ ] **Step 5: Commit** — `git commit -am "fix: cross-platform locking via filelock"`

---

### Task 4: Default workspace root and source-root resolution

**Files:**
- Create: `src/ankiplusmcp/settings.py`, `tests/mcp/test_settings.py`
- Modify: `src/ankiplusmcp/__main__.py`, `src/ankiplusmcp/store.py:25-28,50-59`, `src/ankiplusmcp/server.py` (the `invoke` wrapper and `capabilities`)

**Interfaces:**
- Produces, in `settings.py`:
  - `default_workspace_root() -> Path` — `platformdirs.user_data_path('ankiplusmcp') / 'workspaces'`.
  - `configured_source_roots(flags: list[str] | None, env: Mapping[str, str]) -> tuple[list[Path], str] | None` — returns `(roots, 'flags')`, or `(roots, 'env')` from `ANKIPLUS_SOURCE_ROOTS` split on `os.pathsep` with empty entries dropped, or `None` when neither is set.
  - `safe_cwd_root(cwd: Path, home: Path) -> Path | None` — `None` when `cwd` is a filesystem root or equals `home`.
- Produces, in `store.py`: `Store(root, source_roots: Iterable | None)`; `Store.source_roots: tuple[Path, ...] | None` (`None` = not yet resolved); `Store.source_roots_origin: str`; `Store.set_source_roots(paths, origin)`.
- Produces, in `server.py`: `async def resolve_roots(server, store) -> None` — called by `invoke` before the first tool call when `store.source_roots is None`. Order: client roots via `server.get_context().session.list_roots()` (keep `file://` URIs only, any exception means none) with origin `'client'`; else `safe_cwd_root` with origin `'cwd'`; else `()` with origin `'none'`.
- `capabilities()` adds `source_roots_origin`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/mcp/test_settings.py
import os
from pathlib import Path
import pytest
from ankiplusmcp import settings
from ankiplusmcp.store import Store, DomainError

def test_workspace_default_is_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = settings.default_workspace_root()
    assert root.name == 'workspaces' and 'ankiplusmcp' in root.parts and tmp_path not in root.parents

def test_flags_beat_env_and_empty_entries_are_dropped(tmp_path):
    env = {'ANKIPLUS_SOURCE_ROOTS': os.pathsep.join(['', str(tmp_path), ''])}
    assert settings.configured_source_roots(['/a b'], env) == ([Path('/a b')], 'flags')
    assert settings.configured_source_roots(None, env) == ([tmp_path], 'env')
    assert settings.configured_source_roots(None, {}) is None

def test_cwd_is_refused_at_root_and_home(tmp_path):
    assert settings.safe_cwd_root(Path('/'), tmp_path) is None
    assert settings.safe_cwd_root(tmp_path, tmp_path) is None
    assert settings.safe_cwd_root(tmp_path/'proj', tmp_path) == tmp_path/'proj'

def test_no_roots_gives_source_error_naming_the_flag(tmp_path):
    store = Store(tmp_path/'w', None); store.set_source_roots([], 'none')
    f = tmp_path/'a.txt'; f.write_text('x')
    with pytest.raises(DomainError) as e: store.source(str(f))
    assert e.value.code == 'SOURCE' and '--source-root' in e.value.remedy
```

Add to `tests/mcp/test_protocol.py` a stdio test `test_client_roots_become_source_roots`: start the server with only `--workspace-root`, with `cwd=/`, and a `ClientSession(..., list_roots_callback=...)` returning `file://<tmp_path>/allowed`. Assert `create_workspace` succeeds for a file under `allowed`, fails with code `SOURCE` for a file outside it, and `capabilities()['source_roots_origin'] == 'client'`.

- [ ] **Step 2: Run them** — Expected: FAIL (module missing).

- [ ] **Step 3: Implement `settings.py`, the `Store` changes and `resolve_roots`.** In `__main__.py`, the workspace default becomes `os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or settings.default_workspace_root()`, and `Service` receives `None` for source roots when `configured_source_roots` returns `None`.

- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q tests/mcp` — Expected: all pass. Existing tests pass explicit roots and are unaffected.

- [ ] **Step 5: Commit** — `git commit -am "feat: safe default paths and client-provided source roots"`

---

### Task 5: Profiles

**Files:**
- Modify: `src/ankiplusmcp/settings.py`, `src/ankiplusmcp/models.py:20`, `src/ankiplusmcp/cards.py:20-29`, `src/ankiplusmcp/sources.py:118-126`, `src/ankiplusmcp/service.py`, `src/ankiplusmcp/server.py` (`capabilities`), `src/ankiplusmcp/__main__.py`
- Test: `tests/mcp/test_profiles.py`; update any `tests/mcp/` assertion that relied on the old default note type.

**Interfaces:**
- Produces, in `settings.py`:
  - `@dataclass(frozen=True) class Profile: name: str; note_type: str; tag_root: str`
  - `PROFILES = {'default': Profile('default', 'Cloze', '#AnkiPlus'), 'coldrecall': Profile('coldrecall', 'ColdRecall Cloze', '#ColdRecall')}`
  - `default_config_path() -> Path` — `platformdirs.user_config_path('ankiplusmcp') / 'config.toml'`
  - `load_profile(profile_flag: str | None, config_path: Path | None, env: Mapping[str, str]) -> Profile` — precedence: `profile_flag`, then the config file (`--config`, else `ANKIPLUS_CONFIG`, else `default_config_path()` if it exists), then `'default'`. Config keys: `profile` (a `PROFILES` name), `note_type`, `tag_root` (overrides). Unknown profile name or unknown key raises `ValueError` naming it.
- `Service(root, source_roots, profile: Profile = PROFILES['default'])`; `service.profile`.
- `Card.notetype: Short | None = None`; `Cards.save_cards` fills `None` with `self.profile.note_type` before writing.
- `resolve_target` passes `root=self.profile.tag_root` to `target.build` and `target.parse`, and adds `note_type` to its result.
- `capabilities()` adds `profile: {'name', 'note_type', 'tag_root'}`.
- CLI flags: `--profile`, `--config`.

- [ ] **Step 1: Write the failing test**

```python
# tests/mcp/test_profiles.py
import pytest
from ankiplusmcp import settings
from ankiplusmcp.service import Service
CARD = [{'id': 'a', 'fields': {'Text': 'x {{c1::y}}'}}]

def service(tmp_path, name):
    return Service(tmp_path, [tmp_path], settings.PROFILES[name])

@pytest.mark.parametrize('name,note,root', [('default', 'Cloze', '#AnkiPlus'), ('coldrecall', 'ColdRecall Cloze', '#ColdRecall')])
def test_profile_sets_note_type_and_tag_root(tmp_path, name, note, root):
    s = service(tmp_path, name)
    try:
        w = s.store.create('cards')['id']; s.save_cards(w, CARD, 0)
        assert s.get_cards(w)['cards'][0]['notetype'] == note
        t = s.resolve_target(course='BIO101', number=3, title='Membranes')
        assert t['source_tag'].startswith(root + '::') and t['note_type'] == note
    finally: s.close()

def test_explicit_note_type_is_kept(tmp_path):
    s = service(tmp_path, 'default')
    try:
        w = s.store.create('cards')['id']; s.save_cards(w, [dict(CARD[0], notetype='Basic')], 0)
        assert s.get_cards(w)['cards'][0]['notetype'] == 'Basic'
    finally: s.close()

def test_config_file_precedence_and_errors(tmp_path):
    cfg = tmp_path/'config.toml'; cfg.write_text('profile = "coldrecall"\ntag_root = "#Mine"\n')
    p = settings.load_profile(None, cfg, {})
    assert (p.note_type, p.tag_root) == ('ColdRecall Cloze', '#Mine')
    assert settings.load_profile('default', cfg, {}).tag_root == '#AnkiPlus'
    cfg.write_text('profile = "nope"\n')
    with pytest.raises(ValueError, match='nope'): settings.load_profile(None, cfg, {})
```

The key holding the source tag in `target.build`'s result is defined in `src/cards/target.py:57-75`; use that exact key in the assertion.

- [ ] **Step 2: Run it** — Expected: FAIL.
- [ ] **Step 3: Implement the interfaces above.**
- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q tests/mcp tests/unit` — Expected: all pass after updating old-default assertions in `tests/mcp/` only.
- [ ] **Step 5: Commit** — `git commit -am "feat: profiles for note type and tag root"`

---

### Task 6: Python subcommands, `doctor`, `setup`, dependency errors

**Files:**
- Create: `src/ankiplusmcp/doctor.py`, `tests/mcp/test_doctor.py`
- Modify: `src/ankiplusmcp/__main__.py`, `src/ankiplusmcp/sources.py` (`ocr_image`, `extract_source`), `src/ankiplusmcp/cards.py` (`render_cards`), `src/ankiplusmcp/server.py` (`capabilities`)

**Interfaces:**
- Produces, in `doctor.py`:
  - `have(name: Literal['tesseract', 'chromium']) -> bool` — `tesseract`: `pytesseract` importable and `shutil.which('tesseract')`. `chromium`: `playwright` importable and its Chromium executable path exists.
  - `require(name) -> None` — raises `DomainError('DEPENDENCY', ...)` with remedy `FIXES[name]`.
  - `FIXES = {'tesseract': 'Install Tesseract: macOS `brew install tesseract`; Debian/Ubuntu `sudo apt-get install -y tesseract-ocr`.', 'chromium': 'Run `npx ankiplusmcp setup` (or `ankiplusmcp setup`) to install Chromium for previews.'}`
  - `run_checks(workspace_root: Path, store, profile) -> list[dict]` — each `{'name', 'status': 'ok'|'missing', 'required': bool, 'detail', 'fix'}`. Required: `python` (>= 3.12), `mcp`, `pymupdf`, `pillow`, `workspace_root` (writable). Optional: `tesseract`, `chromium`.
  - `doctor_main(args) -> int` — exit 0 all ok; 1 only optional items missing; 2 a required item missing. `--json` prints `{"ok": bool, "version": str, "checks": [...]}` on stdout; otherwise one line per check.
  - `setup_main(args) -> int` — prints that Chromium will be downloaded and the Tesseract command; without `--yes`: asks on a TTY, exits 3 with `pass --yes to run without a prompt` when there is no TTY; then runs `sys.executable -m playwright install chromium`; exit code is that command's. With `--json`, stdout is `{"chromium": {"installed": bool}, "tesseract": {"available": bool, "fix": str}}` and progress goes to stderr.
- `__main__.main(argv=None)`: `serve` (default; bare flags still mean `serve`), `doctor`, `setup`, `--version` (prints `ankiplusmcp 0.2.0`).
- `ocr_image` calls `require('tesseract')` and `render_cards` calls `require('chromium')` before submitting a job. In `extract_source`'s job, a `pytesseract.TesseractNotFoundError` or missing `pytesseract` becomes `DomainError('DEPENDENCY', ...)`.
- `capabilities()` adds `chromium_available`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/mcp/test_doctor.py
import json, subprocess, sys
import pytest
from ankiplusmcp import doctor
from ankiplusmcp.store import DomainError
from ankiplusmcp.service import Service
RUN = [sys.executable, '-m', 'ankiplusmcp']

def test_version_and_bare_flags_still_serve():
    out = subprocess.run(RUN + ['--version'], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == 'ankiplusmcp 0.2.0'

def test_doctor_json_shape_and_exit_codes(tmp_path, monkeypatch):
    out = subprocess.run(RUN + ['doctor', '--json', '--workspace-root', str(tmp_path)], capture_output=True, text=True)
    data = json.loads(out.stdout)
    assert {'ok', 'version', 'checks'} <= set(data)
    assert {c['name'] for c in data['checks']} >= {'python', 'mcp', 'pymupdf', 'pillow', 'workspace_root', 'tesseract', 'chromium'}
    assert out.returncode in (0, 1)

def test_missing_tesseract_is_a_dependency_error_with_fix(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    s = Service(tmp_path, [tmp_path])
    try:
        w = s.store.create('cards')['id']
        with pytest.raises(DomainError) as e: s.ocr_image(w, 'media/none.png')
        assert e.value.code == 'DEPENDENCY' and 'tesseract' in e.value.remedy.lower()
        s.save_cards(w, [{'id': 'a', 'fields': {'Text': '{{c1::y}}'}}], 0)
        with pytest.raises(DomainError) as e: s.render_cards(w)
        assert e.value.code == 'DEPENDENCY' and 'setup' in e.value.remedy
    finally: s.close()

def test_setup_without_tty_or_yes_exits_3():
    out = subprocess.run(RUN + ['setup'], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert out.returncode == 3 and '--yes' in out.stderr
```

In `ocr_image`, `require('tesseract')` must run before the image check so the dependency error wins.

- [ ] **Step 2: Run them** — Expected: FAIL.
- [ ] **Step 3: Implement `doctor.py` and the routing in `__main__.py`.**
- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q tests/mcp tests/unit` — Expected: all pass. `tests/mcp/test_protocol.py` still launches with bare flags and must pass unchanged.
- [ ] **Step 5: Commit** — `git commit -am "feat: serve/doctor/setup subcommands and dependency errors"`

---

### Task 7: Launcher core: find `uv`, serve, doctor, setup

**Files:**
- Create: `package.json`, `launcher/cli.mjs`, `launcher/lib/uv.mjs`, `launcher/lib/spec.mjs`, `launcher/lib/serve.mjs`, `launcher/test/serve.test.mjs`, `launcher/test/fixtures/fake-uv` (executable shell script)

**Interfaces:**
- `package.json`: `"name": "ankiplusmcp"`, `"version": "0.2.0"`, `"type": "module"`, `"bin": {"ankiplusmcp": "launcher/cli.mjs"}`, `"engines": {"node": ">=18"}`, `"files": ["launcher/cli.mjs", "launcher/lib", "skills/ankiplusmcp", "README.md", "LICENSE"]`, `"scripts": {"test": "node --test launcher/test/"}`, `"license": "MIT"`, `"repository": "github:Hamza-Xoho/ankiplusMCP"`. No `dependencies`.
- `uv.mjs`: `findUv(env, homedir) -> string | null` — `env.ANKIPLUSMCP_UV` if set; else the first `uv` on `env.PATH`; else the first existing of `~/.local/bin/uv`, `~/.cargo/bin/uv`, `/opt/homebrew/bin/uv`, `/usr/local/bin/uv`.
- `spec.mjs`: `VERSION` (read from `package.json`); `pySpec(env) -> string` — `env.ANKIPLUSMCP_PY_SPEC` or `` `ankiplusmcp[all] @ git+https://github.com/Hamza-Xoho/ankiplusMCP@v${VERSION}` ``; `npxRef(env) -> string` — `env.ANKIPLUSMCP_NPX_REF` or `` `github:Hamza-Xoho/ankiplusMCP#v${VERSION}` ``.
- `serve.mjs`: `uvArgs(spec, args) -> string[]` — `['tool', 'run', '--from', spec, 'ankiplusmcp', ...args]`; `run(uv, args, {stdio}) -> Promise<number>` — spawns with `stdio: 'inherit'` by default, forwards `SIGINT` and `SIGTERM`, resolves with the child's exit code, or `128 + signal number` when killed by a signal.
- `cli.mjs` routing: first argument `init` / `uninstall` (Task 8), `doctor`, `setup`, `serve`, `--version`; anything else, including no arguments or a leading flag, is `serve` with all arguments passed through.
- Missing `uv`: exit code 127 and exactly this on stderr:

```
ankiplusmcp: uv was not found. Install it, then run this again:
  curl -LsSf https://astral.sh/uv/install.sh | sh
or: brew install uv
```

- `doctor`: with `--json`, stdout is one object `{"launcher": {"node": "<version>", "node_ok": bool, "uv": "<path>"|null}, "python": <the Python doctor's JSON, or null>}`. Exit 2 when `uv` is missing or Node is older than 18; otherwise the Python doctor's exit code.
- `setup`: runs the Python `setup` with the same arguments.
- `--version`: prints `ankiplusmcp-launcher 0.2.0` to stdout, then the Python `--version` line if `uv` is present.

`fake-uv` records its arguments one per line to `$FAKE_UV_LOG`, writes `$FAKE_UV_STDOUT` to stdout and `$FAKE_UV_STDERR` to stderr if set, and exits with `$FAKE_UV_EXIT` (default 0).

- [ ] **Step 1: Write the failing tests** (`launcher/test/serve.test.mjs`, `node:test` + `node:assert/strict`, each running `launcher/cli.mjs` with `spawnSync(process.execPath, [cli, ...])` and `ANKIPLUSMCP_UV` pointing at `fake-uv`):

  - `serve passes flags through as single arguments`: args `--source-root '/tmp/My Drive/Lectures' --workspace-root /w` → the log's lines equal `tool, run, --from, <pySpec>, ankiplusmcp, --source-root, /tmp/My Drive/Lectures, --workspace-root, /w`.
  - `explicit serve word is dropped`: `serve --workspace-root /w` gives the same tail as above without `serve`.
  - `stdout is exactly the child's`: `FAKE_UV_STDOUT='{"jsonrpc":"2.0"}'` → launcher stdout equals that string and nothing else.
  - `child failure is forwarded`: `FAKE_UV_EXIT=7`, `FAKE_UV_STDERR=boom` → status 7, stderr contains `boom`, stdout is empty.
  - `missing uv`: `ANKIPLUSMCP_UV` unset, `PATH` and `HOME` pointing at an empty temp dir → status 127, stdout empty, stderr equals the exact message above.
  - `default spec pins the tag`: with `ANKIPLUSMCP_PY_SPEC` unset, the `--from` value is `ankiplusmcp[all] @ git+https://github.com/Hamza-Xoho/ankiplusMCP@v0.2.0`.
  - `doctor --json without uv`: status 2, stdout parses as JSON with `launcher.uv === null` and `python === null`.
  - `package has no runtime dependencies`: `package.json` has no `dependencies` key and `bin.ankiplusmcp === 'launcher/cli.mjs'`.

- [ ] **Step 2: Run them** — `npm test` — Expected: FAIL (files missing).
- [ ] **Step 3: Implement the four modules.** `cli.mjs` starts with `#!/usr/bin/env node` and is `chmod +x`.
- [ ] **Step 4: Run** `npm test` — Expected: 8 passing.
- [ ] **Step 5: Real smoke against the local checkout**

Run: `ANKIPLUSMCP_PY_SPEC="ankiplusmcp[all] @ file://$PWD" node launcher/cli.mjs --version`
Expected: two lines, `ankiplusmcp-launcher 0.2.0` then `ankiplusmcp 0.2.0`.

- [ ] **Step 6: Commit** — `git add package.json launcher && git commit -m "feat: npm launcher that runs the server through uv"`

---

### Task 8: `init` and `uninstall`

**Files:**
- Create: `launcher/lib/hosts.mjs`, `launcher/lib/configfile.mjs`, `launcher/lib/init.mjs`, `launcher/test/init.test.mjs`, `launcher/test/fixtures/hosts/` (one sample config per host: empty, with other servers, with an existing `ankiplusmcp` entry, with comments)
- Modify: `launcher/cli.mjs`

**Interfaces:**
- `configfile.mjs`:
  - `readStrictJson(file) -> {ok: true, data} | {ok: false, reason: 'missing' | 'not-json'}`
  - `writeWithBackup(file, data) -> backupPath` — copies the original to `<file>.ankiplusmcp-backup-<YYYYMMDDHHMMSS>` first; writes 2-space JSON with a trailing newline.
- `hosts.mjs` exports `HOSTS`, keyed `claude-code`, `claude-desktop`, `codex`, `opencode`. Each adapter:
  - `detect(env, homedir) -> boolean`
  - `plan({scope, serverArgs, cwd, env, homedir}) -> Change[]`
  - `skillDir({scope, cwd, homedir}) -> string | null`
- `Change` is one of:
  - `{kind: 'command', argv: string[], undo: string[]}`
  - `{kind: 'json', file: string, keyPath: string[], value: object}`
  - `{kind: 'skill', from: string, to: string}`
- The server entry every host receives: command `npx`, arguments `['-y', npxRef(env), 'serve', ...serverArgs]`, where `serverArgs` is built from `--workspace-root`, each `--source-root`, and `--profile`, each as separate array elements.
- Host formats to implement, each verified against that host's current documentation before coding (the README's existing examples are the starting point):

| Host | User scope | Project scope | Skill directory |
|---|---|---|---|
| `claude-code` | `command`: `claude mcp add --scope user --transport stdio ankiplusmcp -- npx ...` | `json`: `./.mcp.json`, key path `mcpServers.ankiplusmcp`, value `{type: 'stdio', command, args}` | `~/.claude/skills/ankiplusmcp` or `./.claude/skills/ankiplusmcp` |
| `claude-desktop` | `json`: macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Linux `~/.config/Claude/claude_desktop_config.json`, key path `mcpServers.ankiplusmcp` | not offered | none |
| `codex` | `command`: `codex mcp add ankiplusmcp -- npx ...` | not offered | per Codex documentation, else none |
| `opencode` | `json`: `~/.config/opencode/opencode.json`, key path per the installed OpenCode version, value `{type: 'local', command: [...]}` | `json`: `./opencode.json` | per OpenCode documentation, else none |

  Add `hermes` only if its documentation confirms a stdio MCP registration format; otherwise leave it to `--print` and say so in the README.
- `init.mjs`:
  - `initMain(argv, {env, homedir, cwd, stdin, stdout, stderr}) -> Promise<number>`
  - `uninstallMain(argv, io) -> Promise<number>`
  - Flags: `--host <id>`, `--scope user|project` (default `user`), `--source-root <dir>` (repeatable), `--workspace-root <dir>`, `--profile <name>`, `--yes`, `--dry-run`, `--force`, `--print`, `--json`, `--no-warmup`.
  - Exit codes: 0 applied or nothing to do; 1 the user declined; 2 error; 3 refused (existing differing entry or skill without `--force`; a config file that is not strict JSON; no TTY without `--yes`).
  - Without `--host`: use the single detected host; with several detected and no TTY, exit 3 listing them.
  - Record file: `<data dir>/install-manifest.json`, where the data dir is macOS `~/Library/Application Support/ankiplusmcp`, Linux `${XDG_DATA_HOME:-~/.local/share}/ankiplusmcp`. It lists every applied change and backup path. `uninstall` reverses exactly those: removes the JSON key it added (leaving other keys), runs each `undo`, removes a skill directory only if it still matches what was installed.
  - After applying, unless `--no-warmup`: run `uv tool run --from <pySpec> ankiplusmcp --version`, then the launcher's `doctor`. Their failure is reported but does not undo the changes.
  - `--json` output: `{"host", "scope", "changes": [{"kind", "target", "status": "applied"|"unchanged"|"refused"|"planned"}], "manual": string | null, "warmup": {"ok": bool} | null}`.
  - `--print`: writes only the generic snippet `{"mcpServers": {"ankiplusmcp": {"command": "npx", "args": [...]}}}` to stdout and exits 0.

- [ ] **Step 1: Write the failing tests** (`launcher/test/init.test.mjs`; every test uses a temp `homedir` and `cwd`, `--no-warmup`, and fixture copies):

  - `dry run shows the change and writes nothing`: `--host claude-code --scope project --dry-run --yes` → exit 0, `.mcp.json` absent, output names `.mcp.json` and `mcpServers.ankiplusmcp`.
  - `project scope writes the entry and keeps other servers`: start from the fixture with an `anki` server → both `anki` and `ankiplusmcp` present; `ankiplusmcp.args` begins `['-y', 'github:Hamza-Xoho/ankiplusMCP#v0.2.0', 'serve']`; a backup file exists and equals the original.
  - `source root with spaces is one array element`: `--source-root '/tmp/My Drive/Lectures'` → `args` contains that exact string as one element directly after `'--source-root'`.
  - `second run changes nothing`: run twice → second exit 0, every change `unchanged`, no second backup.
  - `existing different entry is refused without force`: fixture with another `ankiplusmcp` entry → exit 3, file byte-identical; with `--force` → exit 0 and replaced.
  - `non-JSON config is left alone`: fixture with comments → exit 3, file byte-identical, `manual` holds the snippet.
  - `no TTY without --yes exits 3 at once`: stdin not a TTY, no `--yes` → exit 3, nothing written, stderr contains `--yes`.
  - `skill is installed and a differing copy is refused`: skill directory created and equal to `skills/ankiplusmcp`; with a pre-existing different `SKILL.md` → exit 3 unless `--force`.
  - `command hosts run the host's own command`: with a fake `claude` on `PATH` recording its arguments, `--host claude-code --scope user --yes` → recorded arguments equal `mcp add --scope user --transport stdio ankiplusmcp -- npx -y github:Hamza-Xoho/ankiplusMCP#v0.2.0 serve`.
  - `uninstall restores the original`: init then uninstall on the `anki` fixture → `.mcp.json` deep-equals the original; skill directory gone.
  - `print emits only the snippet`: `--print --source-root /a` → stdout parses as JSON with `mcpServers.ankiplusmcp.command === 'npx'`; nothing written.
  - `claude-desktop on linux and macos paths`: adapter `plan` returns the right file for `platform` `darwin` and `linux`.

- [ ] **Step 2: Run them** — `npm test` — Expected: the new tests FAIL.
- [ ] **Step 3: Implement the three modules and wire `init` / `uninstall` into `cli.mjs`.**
- [ ] **Step 4: Run** `npm test` — Expected: all pass.
- [ ] **Step 5: Commit** — `git add launcher && git commit -m "feat: init and uninstall for supported hosts"`

---

### Task 9: CI, version check and end-to-end run

**Files:**
- Create: `scripts/check_versions.py`, `tests/unit/test_release_checks.py`
- Modify: `.github/workflows/ci.yml`, `scripts/check-mcp.sh`

**Interfaces:**
- `scripts/check_versions.py`: `versions(root: Path) -> dict[str, str]` returning `{'package.json': ..., 'pyproject.toml': ...}`; `main()` exits 1 and prints both when they differ.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_release_checks.py
from pathlib import Path
import importlib.util, json
ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('cv', ROOT/'scripts/check_versions.py')
cv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cv)

def test_repo_versions_agree():
    v = cv.versions(ROOT)
    assert v['package.json'] == v['pyproject.toml'] == '0.2.0'

def test_mismatch_is_reported(tmp_path):
    (tmp_path/'package.json').write_text(json.dumps({'version': '1.0.0'}))
    (tmp_path/'pyproject.toml').write_text('[project]\nversion = "1.0.1"\n')
    assert len(set(cv.versions(tmp_path).values())) == 2
```

- [ ] **Step 2: Run it** — Expected: FAIL. **Step 3: Implement.** **Step 4: Run** — Expected: PASS.

- [ ] **Step 5: Make `scripts/check-mcp.sh` portable.** Replace `sha256sum --check` with `shasum -a 256 --check` when `sha256sum` is absent. Run `./scripts/check-mcp.sh` on this Mac. Expected: tests pass, contract hashes `OK`, wheel built.

- [ ] **Step 6: Extend `.github/workflows/ci.yml`**

  - `test` job: matrix `os: [ubuntu-latest, macos-latest]`; install Tesseract with `apt-get` or `brew`; install with `pip install -e '.[dev]'`.
  - New `checks` job: `python scripts/check_privacy.py` and `python scripts/check_versions.py`.
  - New `launcher` job, matrix `os: [ubuntu-latest, macos-latest]`, `node: [18, 22]`: `npm test`; then the end-to-end steps:

```bash
python -m pip wheel . --no-deps -w dist
npm pack
export ANKIPLUSMCP_PY_SPEC="ankiplusmcp[all] @ file://$PWD/dist/ankiplusmcp-0.2.0-py3-none-any.whl"
work="$(mktemp -d)"
python scripts/smoke-mcp.py --command npx -y "$PWD/ankiplusmcp-0.2.0.tgz" serve --workspace-root "$work/w" --source-root "$work"
```

  The job installs `uv` with `astral-sh/setup-uv`, Tesseract, and Chromium via `npx -y "$PWD/ankiplusmcp-0.2.0.tgz" setup --yes` before the smoke run.

- [ ] **Step 7: Run the end-to-end steps locally** from a temp directory outside the checkout. Expected: `smoke-mcp.py` exits 0.

- [ ] **Step 8: Commit** — `git add -A && git commit -m "ci: launcher tests, end-to-end run, privacy and version checks"`

---

### Task 10: README, manual check, first push

**Files:**
- Modify: `README.md`, `AGENTS.md` (first block only), `docs/capabilities.md` (scope-limits paragraph)

- [ ] **Step 1: Rewrite the README's "Install and run" and "Connect your host" sections**

Required content, in this order: the one-line start (`npx -y github:Hamza-Xoho/ankiplusMCP#v0.2.0`); `init` with `--host`, `--scope`, `--source-root`, `--profile`, `--dry-run`, `--yes`; `doctor`; `setup`; `uninstall`; the `uv`-only alternative (`uvx --from "ankiplusmcp[all] @ git+https://github.com/Hamza-Xoho/ankiplusMCP@v0.2.0" ankiplusmcp`); prerequisites (Node 18+, `uv`, Tesseract for OCR, Chromium for previews); default paths and the source-root order; profiles (`default`, `coldrecall`, `config.toml` keys); a "Running unattended" paragraph (`--yes`, `--json`, exit codes 0/1/2/3); a "Licences" paragraph stating the project is MIT and that PyMuPDF, a dependency installed from PyPI, is AGPL-licensed. Keep the existing "Using the toolkit" section. State which hosts were tried for real and which are covered by fixtures only.

- [ ] **Step 2: Update `AGENTS.md`'s first block** to name `launcher/` and `npm test`, and `docs/capabilities.md` to drop "local stdio only ... `./workspaces`" wording that Task 4 made untrue.

- [ ] **Step 3: Run everything**

```bash
./scripts/check-mcp.sh && npm test && .venv/bin/python scripts/check_privacy.py && .venv/bin/python scripts/check_versions.py
```

Expected: all green.

- [ ] **Step 4: Manual check on the author's machine (read-only)**

Run: `ANKIPLUSMCP_PY_SPEC="ankiplusmcp[all] @ file://$PWD" node launcher/cli.mjs init --host claude-code --scope user --dry-run --yes`
Expected: it reports the existing `ankiplusmcp` entry and makes no change. Report the actual output to the author.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "docs: npx install, init, doctor, profiles, licences"`

- [ ] **Step 6: STOP. Ask the author for the go-ahead to push.** Show `git log --oneline`, the output of `check_privacy.py`, and `git ls-files | wc -l`. Also ask whether they want their own install switched to `--profile coldrecall`; without it their default note type becomes `Cloze`. Do neither without a yes.

- [ ] **Step 7: After a yes, push and tag**

```bash
git remote add origin https://github.com/Hamza-Xoho/ankiplusMCP.git
git tag v0.2.0
git push -u origin main
git push origin v0.2.0
```

- [ ] **Step 8: Verify from GitHub**, in a temp directory outside the checkout:

Run: `npx -y github:Hamza-Xoho/ankiplusMCP#v0.2.0 --version`
Expected: `ankiplusmcp-launcher 0.2.0` then `ankiplusmcp 0.2.0`.

Run: `npx -y github:Hamza-Xoho/ankiplusMCP#v0.2.0 doctor`
Expected: every required check `ok`.

Check the CI run on GitHub and report its result as it is.
