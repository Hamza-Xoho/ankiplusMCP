# Efficacy 3a: Core and Speed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The MCP layer calls typed functions in `src/cards/` (no faked argument objects, no private imports, no fake `build.json`), extraction no longer blocks the workspace and is readable before figure labels finish, previews can use the system's Chrome, and the handshake reports the right version.

**Architecture:** `src/cards/` stays the core and keeps its module names. Each operation the MCP uses gains a public function with plain arguments; the CLI's `run(args)` functions call the same code and print exactly what they print today. `src/ankiplusmcp/` is rewired onto those functions. No tool is added, renamed or removed; that is 3b. The spec's table also lists `extract/pdf.py` and `extract/figures.py`; reading the code showed they need no change, so this plan leaves them alone.

**Tech Stack:** Python 3.12+, PyMuPDF, Pillow, Tesseract (subprocess), Playwright, `mcp` 1.30, pytest.

**Spec:** `docs/superpowers/specs/2026-11-10-efficacy-design.md`, section "3a. Core and speed". Read "What was measured", "Constraints" and "3a" before starting.

## Global Constraints

- The owner lifted the `src/cards/` freeze for source files only, on 2026-11-10. In `src/cards/` you may edit only: `extract/__init__.py`, `extract/ocr.py`, `source.py`, `figures.py`, `render/__init__.py`, `check/lint.py`, `common/files.py`. Nothing else under `src/cards/`.
- Never edit, move, skip or xfail anything in `tests/contract/`. Never edit `.codex/`, `.agents/` or `.claude/`. A contract test that seems to need a change is a stop and a question to the owner.
- The `cards` CLI prints the same stdout, returns the same exit codes and writes the same files as before. Proof is `tests/tools/cli_baseline.py compare` (Task 1) printing `IDENTICAL`, run after every task that touches `src/cards/`.
- No network import anywhere in `src/cards/` (a frozen test checks).
- OCR settings do not change: modes `[11, 6, 12, 4]`, threshold 128, 2x upscale, 4x figure raster, `min_conf=20`, `min_len=2`, `pad=0.004`. Only how many times and how concurrently OCR runs may change.
- No MCP tool is added, removed or renamed, and no tool argument changes. Result fields may be added.
- No Anki connection, proxy or collection code. That is 3d.
- The version stays `0.2.0` in `pyproject.toml` and `package.json`. The launcher installs the git tag named after the version, so a bump without a tag breaks installs. Releasing is the owner's call. `cards.__version__` stays `0.1.0`.
- Work on a branch named `efficacy-3a`, cut from `main`. Commit locally. No `git push`, no tag.
- Use `.venv/bin/python` for everything. Suites: `./scripts/check-mcp.sh`, `npm test`, and `CARDS_PUBLIC_CI=1 PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/contract` (expected today: 261 passed, 24 skipped, about three minutes).
- No home-directory paths or email addresses in tracked files; `.venv/bin/python scripts/check_privacy.py` must exit 0.
- A project hook blocks shell commands that mention local ports. Do not work around it.

## Review Focus

1. An extraction cancelled while figures are being read leaves no published extraction and no "partial" marker, and running it again succeeds. (Tests in Tasks 4 and 6.)
2. The source file changing while extraction runs publishes nothing and reports `SOURCE_CHANGED`. (Task 4.)
3. A truncated or unreadable OCR cache entry is treated as a miss and replaced, never a crash. (Task 5.)
4. Two extractions of the same workspace running at once both finish, and the workspace points at one complete extraction. (Task 4.)
5. A browser that is configured but not installed gives a `DEPENDENCY` error that names the fix, not a Playwright traceback. (Task 8.)

## File Structure

| File | Responsibility after this plan |
|---|---|
| `tests/tools/cli_baseline.py` | New. Records and compares everything the `cards` CLI prints and writes for a fixed synthetic lecture. |
| `tests/tools/time_extract.py` | New. Prints the render and OCR timing split for a synthetic PDF. |
| `src/cards/common/files.py` | Adds public `atomic_write`. |
| `src/cards/figures.py` | Adds public `parse_regions`, `occlusion_markup`, `write_images`. |
| `src/cards/check/lint.py` | `lint` takes `tag_root`. |
| `src/cards/extract/__init__.py` | Adds `extract_source`, `Extraction`, `ExtractionCancelled`, `ocr_figures`, `default_workers`. `run` calls `extract_source`. |
| `src/cards/extract/ocr.py` | Adds `cached_extract`, `tesseract_version`, public `binarise` and `words`. |
| `src/cards/source.py` | Adds `page_image`. `run` calls it. |
| `src/cards/render/__init__.py` | Adds `render_rows`, `launch_options`. `_render` takes `browser`. |
| `src/ankiplusmcp/sources.py` | Extraction outside the lock, two stages, progress; no faked arguments except in `measure_usage`. |
| `src/ankiplusmcp/cards.py` | Rendering through `render_rows`; lint with the profile's tag root. |
| `src/ankiplusmcp/jobs.py` | Job callbacks can report progress. |
| `src/ankiplusmcp/settings.py`, `doctor.py`, `__main__.py`, `service.py`, `variants.py` | Browser setting and resolution. |
| `src/ankiplusmcp/server.py` | Handshake version; `capabilities` reports the browser. |
| `tests/unit/test_core_api.py`, `tests/unit/test_ocr_speed.py`, `tests/mcp/test_adapters.py` | New test files. |

---

### Task 1: Record the freeze lift and build the before/after safety net

Without private fixtures, the 24 skipped contract tests are the ones that cover extraction, figures and rendering. This task gives every later task a byte-level check that the CLI did not move.

**Files:**
- Modify: `AGENTS.md` (the paragraph that says to keep `src/cards/` unchanged)
- Create: `tests/tools/cli_baseline.py`
- Create: `tests/unit/test_cli_baseline.py`

**Interfaces:**
- Produces: `.venv/bin/python tests/tools/cli_baseline.py record <dir>` and `... compare <dir>`. `compare` prints `IDENTICAL (<n> files, <m> commands)` and exits 0, or prints a unified diff per differing entry and exits 1.
- Produces: `normalize(name: str, text: str, root: Path) -> str` in that file, used by the unit test.

- [ ] **Step 1: Branch**

```bash
git switch -c efficacy-3a
```

- [ ] **Step 2: Edit `AGENTS.md`**

Replace the sentence "Keep `src/cards/`, frozen contract tests, `.codex/`, `.agents/` and existing `.claude/` skills unchanged." with:

```
Frozen: the contract tests in `.codex/contract.sha256`, `.codex/`, `.agents/`
and existing `.claude/` skills. `src/cards/` source files may change only as an
approved plan lists (owner's decision, 2026-11-10); the `cards` CLI's output
must stay byte-identical, checked with `tests/tools/cli_baseline.py compare`.
```

- [ ] **Step 3: Write the failing test** in `tests/unit/test_cli_baseline.py`

```python
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('cli_baseline', Path(__file__).parents[1]/'tools/cli_baseline.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

def test_normalize_removes_run_to_run_noise(tmp_path):
    a = tool.normalize('x.json', '{"_meta": {"created": "2026-01-01T00:00:00Z"}, "path": "%s/b/source"}' % tmp_path, tmp_path)
    b = tool.normalize('x.json', '{"_meta": {"created": "2027-02-02T00:00:00Z"}, "path": "%s/b/source"}' % tmp_path, tmp_path)
    assert a == b and '<ROOT>' in a and '_meta' not in a
    assert tool.normalize('m.md', '<!-- cards extract 0.1.0 2026-01-01 -->\nbody\n', tmp_path) == 'body\n'
```

- [ ] **Step 4: Run it; expect failure** (`No such file`)

Run: `.venv/bin/python -m pytest -q tests/unit/test_cli_baseline.py`

- [ ] **Step 5: Implement `tests/tools/cli_baseline.py`**

It builds its own inputs in a temporary folder, runs the CLI as a subprocess (`[sys.executable, '-m', 'cards', ...]` with `PYTHONPATH` set to `src`), and snapshots the result.

Inputs it creates:
- `lecture.pdf`, three 960x540 pages made with PyMuPDF: page 1 a title, a "Learning objectives" list and two columns of text; page 2 a title and one embedded 1400x900 PNG that has eight text labels drawn with `ImageFont.load_default(size=28)`; page 3 a title and at least five vector drawings and no image.
- `notes.md`, a short Markdown source with two headings.
- Build folders `b_pdf` and `b_text`, each with a `build.json` of `{"source": {"path": "<source path>"}}`.
- Inside `b_pdf`: `decks.json` (`[]`), `regions.json` (three fractional rectangles for `p02_f1`), `present.jsonl` (two `{"id", "question", "answer"}` records), and, after the figure step, a `drafts.jsonl` holding two cloze notes plus the image-occlusion note the CLI appended. Use `tests/p3_helpers.py` (`note`, `drafts`, `dump`) for note shapes.

Commands, in this order, each captured as `{argv, exit_code, stdout}`:
`extract` on `b_pdf`; `extract` on `b_pdf` again (cache hit); `extract` on `b_text`; `source --slides 1-2`; `source --grep <a word on page 1>`; `source --page-image 2`; `source --figure p02_f1`; `target --existing-decks decks.json --course MED241 --number 6 --title "Baseline Lecture"`; `figures --summary`; `figures --fig p02_f1 --regions regions.json --mode one`; `check`; `render`; `render --only <first note id>`; `render --anki-html present.jsonl`.

Snapshot: every `.json`, `.jsonl`, `.md`, `.html` and `.txt` under both build folders, passed through `normalize`, plus the captured commands, plus each `.png` recorded as `"<width>x<height>"`. `log.jsonl` is left out (it holds durations).

`normalize` removes `_meta` keys from JSON objects and `_meta` lines from JSONL, drops a first line that starts with `<!-- cards `, and replaces the temporary root path with `<ROOT>`.

`record <dir>` writes the snapshot as one JSON file in `<dir>`. `compare <dir>` builds a fresh snapshot and diffs it against that file.

- [ ] **Step 6: Run the unit test; expect pass**

- [ ] **Step 7: Record the baseline from unmodified code, and prove it is stable**

```bash
.venv/bin/python tests/tools/cli_baseline.py record builds/_cli-baseline
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: `IDENTICAL (...)`. If it differs, the snapshot still contains noise; fix `normalize` (never the CLI) and record again. `builds/` is git-ignored, so the baseline is not committed. It must not be re-recorded after this step.

- [ ] **Step 8: Commit**

```bash
git add AGENTS.md tests/tools/cli_baseline.py tests/unit/test_cli_baseline.py
git commit -m "test: record-and-compare baseline for the cards CLI; note the freeze lift"
```

---

### Task 2: Public names for writing, regions and lint

**Files:**
- Modify: `src/cards/common/files.py`, `src/cards/figures.py`, `src/cards/check/lint.py`
- Modify: `src/ankiplusmcp/store.py`, `src/ankiplusmcp/cards.py`, `src/ankiplusmcp/sources.py`
- Test: `tests/unit/test_core_api.py` (create), `tests/mcp/test_cards.py`

**Interfaces:**
- Produces: `cards.common.files.atomic_write(path, text) -> None`; `_write` stays as the same object.
- Produces: `cards.figures.parse_regions(raw: list, keep: str | None) -> list[dict]`, `occlusion_markup(regions: list[dict], mode: str) -> str`, `write_images(image, regions, media: Path, preview: Path) -> None`; `_regions`, `_occlusion`, `_images` stay as the same objects.
- Produces: `cards.check.lint.lint(n: dict, enumeration: bool = False, tag_root: str = '#ColdRecall') -> list[dict]`. Rule L10 flags a tag that does not start with `tag_root + '::'`.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_core_api.py`

```python
def test_public_names_are_the_private_ones():
    from cards.common import files
    from cards import figures
    assert files._write is files.atomic_write
    assert figures._regions is figures.parse_regions
    assert figures._occlusion is figures.occlusion_markup
    assert figures._images is figures.write_images

def test_lint_tag_root():
    from cards.check.lint import lint
    note = {'id': 'n001', 'fields': {'Text': '{{c1::Sodium}} crosses', 'Extra': ''}, 'tags': ['#AnkiPlus::T']}
    codes = lambda **kw: {f['code'] for f in lint(note, **kw)}
    assert 'L10' in codes()
    assert 'L10' not in codes(tag_root='#AnkiPlus')
    assert 'L10' in {f['code'] for f in lint({**note, 'tags': ['#AnkiPlusX::T']}, tag_root='#AnkiPlus')}
```

and in `tests/mcp/test_cards.py`:

```python
def test_house_style_uses_the_profile_tag_root(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])  # default profile: tag root #AnkiPlus
    w = s.store.create('cards')['id']
    card = {'id': 'n1', 'fields': {'Text': '{{c1::Sodium}} crosses', 'Extra': ''}, 'tags': ['#AnkiPlus::T']}
    s.save_cards(w, [card], 0)
    assert 'L10' not in {f['code'] for f in s.check_cards(w, house_style=True)['findings']}
    s.save_cards(w, [{**card, 'tags': ['#Other::T']}], 1)
    assert 'L10' in {f['code'] for f in s.check_cards(w, house_style=True)['findings']}
    s.close()
```

- [ ] **Step 2: Run them; expect failures** (`AttributeError: atomic_write`, unexpected keyword `tag_root`, `L10` present)

Run: `.venv/bin/python -m pytest -q tests/unit/test_core_api.py tests/mcp/test_cards.py`

- [ ] **Step 3: Implement in `src/cards/`**

Rename each function to its public name and add the old name as an alias on the next line (`_write = atomic_write`). Callers inside `src/cards/` may keep using either. In `lint`, replace the fixed `'#ColdRecall::'` with `tag_root + '::'`.

- [ ] **Step 4: Rewire `src/ankiplusmcp/`**

`store.py` and `cards.py` import `atomic_write`. `sources.build_occlusion` imports the three public names. `cards.check_cards` calls `lint(card, tag_root=self.profile.tag_root)`.

- [ ] **Step 5: Run the tests and the baseline**

```bash
./scripts/check-mcp.sh
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: all pass; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add src/cards/common/files.py src/cards/figures.py src/cards/check/lint.py src/ankiplusmcp tests
git commit -m "refactor: public names for atomic write, occlusion regions and lint tag root"
```

---

### Task 3: Typed extraction and page image

**Files:**
- Modify: `src/cards/extract/__init__.py`, `src/cards/source.py`
- Modify: `src/ankiplusmcp/sources.py`, `src/ankiplusmcp/store.py`
- Test: `tests/unit/test_core_api.py`, `tests/mcp/test_sources.py`

**Interfaces:**
- Produces, in `cards.extract`:

```python
class ExtractionCancelled(Exception): ...

@dataclass(frozen=True)
class Extraction:
    slide_count: int
    figure_count: int
    flagged: int            # slides with at least one flag
    objective_count: int
    objective_flags: bool
    cached: bool            # on a cache hit only slide_count, cached and map are meaningful
    map: Path               # <out_dir>/source/map.md

def extract_source(source: Path, out_dir: Path, slides: str | None = None, *,
                   on_progress: Callable[[str, int, int | None], None] | None = None,
                   should_cancel: Callable[[], bool] | None = None) -> Extraction
```

  It writes `source/slides.json`, `source/objectives.json`, `source/slides_summary.json`, `source/map.md` and `source/figures/` under `out_dir`, exactly as `run` does today, and reads no `build.json`. `on_progress('slides', done, None)` is called after each slide is read and `on_progress('figures', done, total)` after each figure's OCR. `should_cancel` is asked after each slide and before each figure's OCR; when it returns true the function raises `ExtractionCancelled` and leaves no `slides.json`.
- Produces, in `cards.source`: `page_image(pdf: Path, out: Path, page: int) -> Path`, with today's 1,000-pixel longest side and today's `E23` errors.
- Tasks 5 and 6 add keyword arguments to `extract_source`; they do not change these.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_core_api.py`

```python
def test_extract_source_needs_no_build_json(tmp_path):
    from cards.extract import extract_source
    src = tmp_path/'notes.md'; src.write_text('# Membrane\n\nSodium crosses channels.\n')
    out = tmp_path/'out'
    first = extract_source(src, out)
    assert first.slide_count >= 1 and not first.cached and first.map == out/'source/map.md'
    assert (out/'source/slides.json').is_file() and not (out/'build.json').exists()
    assert extract_source(src, out).cached

def test_extract_source_cancel_leaves_no_manifest(tmp_path):
    import pytest
    from cards.extract import extract_source, ExtractionCancelled
    src = tmp_path/'notes.md'; src.write_text('# A\n\ntext\n')
    with pytest.raises(ExtractionCancelled):
        extract_source(src, tmp_path/'out', should_cancel=lambda: True)
    assert not (tmp_path/'out/source/slides.json').exists()

def test_extract_source_reports_figure_progress(tmp_path):
    import io, pymupdf
    from PIL import Image
    from cards.extract import extract_source
    buf = io.BytesIO(); Image.new('RGB', (400, 300), 'white').save(buf, 'PNG')
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=960, height=540); page.insert_text((40, 40), 'Title')
        page.insert_image(pymupdf.Rect(100, 80, 860, 520), stream=buf.getvalue()); doc.save(pdf)
    seen = []
    extract_source(pdf, tmp_path/'out', on_progress=lambda *event: seen.append(event))
    assert ('figures', 1, 1) in seen and ('slides', 1, None) in seen

def test_page_image(tmp_path):
    import pymupdf
    from PIL import Image
    from cards.source import page_image
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc: doc.new_page(width=960, height=540); doc.save(pdf)
    out = page_image(pdf, tmp_path/'p01.png', 1)
    with Image.open(out) as im: assert max(im.size) == 1000
```

and in `tests/mcp/test_sources.py`:

```python
def test_workspace_has_no_fake_build_json(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])
    w = s.store.create('lecture', text='# A\n\nSodium crosses channels.\n')['id']
    wait(s, w, s.extract_source(w))
    assert not list((tmp_path/'work').rglob('build.json'))
    s.close()
```

- [ ] **Step 2: Run them; expect failures** (`ImportError: extract_source`, `page_image`; a `build.json` is found)

- [ ] **Step 3: Implement `extract_source` and `page_image`**

Move the body of `extract.run` into `extract_source`, taking the source path and output folder as arguments (`Build(out_dir)` internally). `run(args)` keeps `source_path(build)` and turns the returned `Extraction` into exactly today's `Result`: the `cache hit: N slides` line on a hit, otherwise the counts line with `FINDINGS`/`OK` and exit code as now. Do the same for the page-image branch of `source.run`.

- [ ] **Step 4: Rewire `src/ankiplusmcp/sources.py` and `store.py`**

`extract_source` calls `extract.extract_source(path, self.store.path(workspace, prefix), slides, should_cancel=cancel)` and turns `ExtractionCancelled` into `DomainError('CANCELLED', ...)`. `get_page_image` checks the page number against the extracted slides with `selection`, then calls `page_image` with the workspace's source copy. Remove both `build.json` writes (`sources.extract_source` and `Store.create`) and both `SimpleNamespace` uses.

- [ ] **Step 5: Run the tests and the baseline**

```bash
./scripts/check-mcp.sh
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: all pass; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add src/cards/extract/__init__.py src/cards/source.py src/ankiplusmcp tests
git commit -m "refactor: typed extract_source and page_image; MCP stops faking build.json"
```

---

### Task 4: Extraction outside the lock, with progress

**Files:**
- Modify: `src/ankiplusmcp/jobs.py`, `src/ankiplusmcp/sources.py`, `src/ankiplusmcp/cards.py`
- Test: `tests/mcp/test_sources.py`

**Interfaces:**
- Consumes: `cards.extract.extract_source` (Task 3).
- Produces: job callbacks are called as `callback(cancel, report)`. `report(text: str) -> None` stores `text` as the job's `progress`. All four existing callbacks (`extract_source`, `ocr_image`, `export_figures`, `render_cards`) take the second argument.
- Produces: the extraction job's `progress` reads `slides <n>` while slides are read and `figures <done>/<total>` during OCR.

New order of work inside the extraction job:
1. Under the workspace lock: read the manifest, check the source hash, return the cached result if the existing extraction still matches.
2. With no lock held: size limits, then `extract_source` into a fresh `extractions/<uuid>/engine` folder.
3. Under `store.edit`: check the source hash again (`SOURCE_CHANGED` if it moved), set `source_engine`, bump the revision once.

Two extractions of one workspace may run at once; each has its own folder and the later commit wins.

- [ ] **Step 1: Write the failing tests** in `tests/mcp/test_sources.py`

A shared helper replaces the core function with one that signals, waits, then defers to the real one:

```python
import threading
def gated(monkeypatch):
    from cards import extract
    real, started, release = extract.extract_source, threading.Event(), threading.Event()
    def slow(*args, **kwargs):
        if kwargs.get('on_progress'): kwargs['on_progress']('figures', 3, 10)
        started.set(); release.wait(10)
        if kwargs.get('should_cancel') and kwargs['should_cancel'](): raise extract.ExtractionCancelled()
        return real(*args, **kwargs)
    monkeypatch.setattr(extract, 'extract_source', slow)
    return started, release

def lecture(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])
    return s, s.store.create('lecture', text='# A\n\nSodium crosses channels.\n')['id']

def test_reads_do_not_wait_for_extraction(tmp_path, monkeypatch):
    started, release = gated(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    t = time.monotonic(); s.get_cards(w); assert time.monotonic() - t < 1
    assert s.jobs.get(w, job['id'])['progress'] == 'figures 3/10'
    release.set(); wait(s, w, job); s.close()

def test_cancel_mid_extraction_then_retry(tmp_path, monkeypatch):
    started, release = gated(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    s.jobs.cancel(w, job['id']); release.set()
    for _ in range(300):
        if s.jobs.get(w, job['id'])['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert s.jobs.get(w, job['id'])['status'] == 'cancelled'
    assert 'source_engine' not in s.store.get(w)
    release.set(); wait(s, w, s.extract_source(w)); assert 'Sodium' in s.read_source(w)['text']; s.close()

def test_source_changed_during_extraction_publishes_nothing(tmp_path, monkeypatch):
    from ankiplusmcp import sources
    s, w = lecture(tmp_path); real = sources.digest; calls = []
    def digest(path):          # the first check sees the real hash, the check at publish time does not
        calls.append(path)
        return real(path) if len(calls) == 1 else 'changed'
    monkeypatch.setattr(sources, 'digest', digest)
    job = s.extract_source(w)
    for _ in range(300):
        record = s.jobs.get(w, job['id'])
        if record['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert record['status'] == 'failed' and record['error']['code'] == 'SOURCE_CHANGED'
    assert 'source_engine' not in s.store.get(w); s.close()

def test_two_extractions_at_once_leave_one_complete_result(tmp_path):
    s, w = lecture(tmp_path)
    a, b = s.extract_source(w, slides='1'), s.extract_source(w)
    wait(s, w, a); wait(s, w, b)
    engine = s.store.get(w)['source_engine']
    assert s.store.read_json(w, engine + '/source/slides.json')['slide_count'] >= 1; s.close()
```

- [ ] **Step 2: Run them; expect failures** (`get_cards` blocks past one second; `progress` is `operation running`)

- [ ] **Step 3: Implement** the callback signature in `jobs.py`, the three-phase flow in `sources.extract_source` (passing an `on_progress` that calls `report` with the two formats above), and the extra parameter in the other three callbacks.

- [ ] **Step 4: Run** `./scripts/check-mcp.sh`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/ankiplusmcp tests/mcp/test_sources.py
git commit -m "fix: extraction no longer holds the workspace lock; jobs report progress"
```

---

### Task 5: OCR without repeated work

**Files:**
- Modify: `src/cards/extract/ocr.py`, `src/cards/extract/__init__.py`
- Modify: `src/ankiplusmcp/sources.py`
- Test: `tests/unit/test_ocr_speed.py` (create), `tests/mcp/test_sources.py`

**Interfaces:**
- Produces, in `cards.extract.ocr`: `tesseract_version() -> str` (first line of `tesseract --version`, cached for the process, `'unknown'` if it cannot run); `cached_extract(path: Path, cache_dir: Path | None) -> dict` (the same value `extract(path)` returns); `CACHE_LIMIT = 2000`; public aliases `binarise` and `words` for `_binarise` and `_words`.
- Produces, in `cards.extract`: `default_workers() -> int` (`os.cpu_count() or 4`); `ocr_figures(paths: list[Path], *, workers: int | None = None, cache_dir: Path | None = None, on_progress=None, should_cancel=None) -> dict[Path, dict]`; and two new keyword arguments on `extract_source`: `workers: int | None = None`, `ocr_cache: Path | None = None`.
- Cache entry name: `<sha256 of the image file>.<key>.json`, where `key` is the first 16 hex characters of the SHA-256 of `repr((tesseract_version(), PSM_MODES, 20, 2, 0.004, True))`. Entries are written with `atomic_write`. After a write, if the folder holds more than `CACHE_LIMIT` entries, the oldest by modification time are deleted down to the limit.
- The `cards` CLI passes no cache, so its behaviour is unchanged apart from the worker count.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_ocr_speed.py`

All of them replace `cards.extract.ocr.extract` with a counter, so Tesseract is not needed:

```python
import json
from pathlib import Path
import pytest
from cards import extract as ex
from cards.extract import ocr

@pytest.fixture
def counted(monkeypatch):
    calls = []
    monkeypatch.setattr(ocr, 'extract', lambda path, **kw: calls.append(Path(path).name) or {'regions': [{'text': Path(path).read_text()}], 'repeated': {}})
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 5.5.4')
    return calls

def files(tmp_path, *contents):
    out = []
    for i, text in enumerate(contents):
        p = tmp_path/f'f{i}.png'; p.write_text(text); out.append(p)
    return out

def test_identical_figures_are_read_once(tmp_path, counted):
    a, b, c = files(tmp_path, 'same', 'same', 'other')
    result = ex.ocr_figures([a, b, c], workers=2)
    assert len(counted) == 2 and result[a] == result[b] and result[a] is not result[b] and result[c] != result[a]

def test_cache_hit_skips_ocr(tmp_path, counted):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    first = ocr.cached_extract(a, cache); second = ocr.cached_extract(a, cache)
    assert len(counted) == 1 and first == second

def test_corrupt_cache_entry_is_a_miss(tmp_path, counted):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache)
    entry = next(cache.iterdir()); entry.write_text('{"regions": [')
    assert ocr.cached_extract(a, cache)['regions'] and len(counted) == 2
    json.loads(entry.read_text())

def test_cache_key_follows_the_tesseract_version(tmp_path, counted, monkeypatch):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache)
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 6.0.0')
    ocr.cached_extract(a, cache); assert len(counted) == 2

def test_cache_is_bounded(tmp_path, counted, monkeypatch):
    monkeypatch.setattr(ocr, 'CACHE_LIMIT', 3); cache = tmp_path/'cache'
    for p in files(tmp_path, *'abcde'): ocr.cached_extract(p, cache)
    assert len(list(cache.iterdir())) == 3

def test_default_workers(monkeypatch):
    import os
    monkeypatch.setattr(os, 'cpu_count', lambda: 6); assert ex.default_workers() == 6
    monkeypatch.setattr(os, 'cpu_count', lambda: None); assert ex.default_workers() == 4
```

and in `tests/mcp/test_sources.py`:

```python
def test_second_workspace_reuses_ocr_results(tmp_path, monkeypatch):
    import io, pymupdf
    from cards.extract import ocr
    calls = []
    monkeypatch.setattr(ocr, 'extract', lambda path, **kw: calls.append(1) or {'regions': [], 'repeated': {}})
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 5.5.4')
    buf = io.BytesIO(); Image.new('RGB', (400, 300), 'white').save(buf, 'PNG')
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=960, height=540); page.insert_text((40, 40), 'Title')
        page.insert_image(pymupdf.Rect(100, 80, 860, 520), stream=buf.getvalue()); doc.save(pdf)
    s = Service(tmp_path/'work', [tmp_path])
    for _ in range(2):
        w = s.store.create('lecture', source_path=str(pdf))['id']
        wait(s, w, s.extract_source(w))
    assert len(calls) == 1
    assert s.store.list()['total'] == 2      # the cache folder is not a workspace
    s.close()
```

- [ ] **Step 2: Run them; expect failures** (`AttributeError: ocr_figures`, `cached_extract`)

- [ ] **Step 3: Implement**

`ocr_figures` groups the paths by file hash, reads one path per group through `cached_extract` on a thread pool of `workers or default_workers()`, largest image first as now, and gives every path its own copy of its group's result. Progress counts figures, not groups: finishing a group of three identical figures advances `done` by three. `extract_source` uses it in place of its inline queue and passes `on_progress` and `should_cancel` through. In `src/ankiplusmcp/sources.py` pass `ocr_cache=self.store.root/'.cache'/'ocr'`.

- [ ] **Step 4: Run the tests and the baseline**

```bash
./scripts/check-mcp.sh
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: all pass; `IDENTICAL`.

- [ ] **Step 5: Commit**

```bash
git add src/cards/extract src/ankiplusmcp/sources.py tests
git commit -m "perf: OCR each distinct figure once, cache results, use every core"
```

---

### Task 6: Text first, labels after

**Files:**
- Modify: `src/cards/extract/__init__.py`
- Modify: `src/ankiplusmcp/sources.py`
- Test: `tests/unit/test_core_api.py`, `tests/mcp/test_sources.py`

**Interfaces:**
- Produces: `extract_source(..., on_text_ready: Callable[[dict], None] | None = None)`. Called once, after every slide is read and every figure crop is saved and before any OCR, with a dict of the same shape as `slides.json` (labels empty). Not called on a cache hit. The CLI does not pass it.
- Produces, in the MCP layer: while an extraction runs and the workspace has no published extraction, `read_source`, `search_source`, `list_figures` and `get_figure` answer from the text-ready data and add `"labels_pending": true` to their result. The marker is a file `source-partial.json` at the workspace root holding `{"prefix": ...}`; the data is `<prefix>/source/slides.partial.json`. Writing the marker does not bump the revision. The marker is removed when the extraction is published, fails or is cancelled. A published extraction always takes priority over a marker.
- Produces: job `progress` reads `text ready; figures <done>/<total>` once the text is ready.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_core_api.py`:

```python
def test_text_ready_fires_once_before_ocr_and_not_on_cache_hit(tmp_path):
    from cards.extract import extract_source
    src = tmp_path/'notes.md'; src.write_text('# A\n\nSodium crosses channels.\n'); seen = []
    extract_source(src, tmp_path/'out', on_text_ready=seen.append)
    assert len(seen) == 1 and seen[0]['slides'][0]['text']
    extract_source(src, tmp_path/'out', on_text_ready=seen.append)
    assert len(seen) == 1
```

In `tests/mcp/test_sources.py`, add a helper `gated_text_ready(monkeypatch)` that returns `(started, release)` like `gated` in Task 4, with a replacement core function that calls `on_text_ready` with one slide (`{'slide_count': 1, 'slides': [{'n': 1, 'title': 'A', 'text': 'Sodium crosses channels.', 'figures': [], 'flags': []}]}`), signals, waits for release, honours `should_cancel`, then defers to the real function:

```python
def test_source_is_readable_before_labels_finish(tmp_path, monkeypatch):
    started, release = gated_text_ready(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    early = s.read_source(w)
    assert 'Sodium' in early['text'] and early['labels_pending'] is True
    assert s.search_source(w, 'sodium')['labels_pending'] is True
    assert s.jobs.get(w, job['id'])['progress'].startswith('text ready')
    release.set(); wait(s, w, job)
    assert 'labels_pending' not in s.read_source(w)
    assert not s.store.path(w, 'source-partial.json').exists(); s.close()

def test_cancel_removes_the_partial_marker(tmp_path, monkeypatch):
    started, release = gated_text_ready(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    s.jobs.cancel(w, job['id']); release.set()
    for _ in range(300):
        if s.jobs.get(w, job['id'])['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert not s.store.path(w, 'source-partial.json').exists()
    with pytest.raises(DomainError): s.read_source(w)
    s.close()
```

- [ ] **Step 2: Run them; expect failures** (unexpected keyword `on_text_ready`; `read_source` raises while the job runs)

- [ ] **Step 3: Implement** the callback in `extract_source` and the marker handling in `sources.py`.

- [ ] **Step 4: Run the tests and the baseline**

```bash
./scripts/check-mcp.sh
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: all pass; `IDENTICAL`.

- [ ] **Step 5: Commit**

```bash
git add src/cards/extract/__init__.py src/ankiplusmcp/sources.py tests
git commit -m "feat: lecture text is readable while figure labels are still being read"
```

---

### Task 7: Typed rendering

**Files:**
- Modify: `src/cards/render/__init__.py`
- Modify: `src/ankiplusmcp/cards.py`, `src/ankiplusmcp/variants.py`
- Test: `tests/unit/test_core_api.py`, `tests/mcp/test_cards.py`

**Interfaces:**
- Produces, in `cards.render`:
  - `launch_options(browser: str) -> dict`: `{}` for `'chromium'`, `{'channel': 'chrome'}` for `'chrome'`, `{'executable_path': browser}` for anything else.
  - `render_rows(rows: list[dict], out_dir: Path, *, css: str | None = None, per_sheet: int = 8, browser: str = 'chromium') -> list[dict]`. `rows` are `{'id', 'question', 'answer'}` records, the same as an `--anki-html` file. `css=None` means the bundled stylesheet. It writes `renders/cards/` and `renders/sheets/` under `out_dir` and `renders/sheets.json`, and returns the sheets list (`fronts`, `backs`, `notes`) that the manifest holds.
  - `_render(build, prepared, selected, browser='chromium')`, passing `**launch_options(browser)` to the browser launch.
- `run(args)` keeps its own build-folder bookkeeping (`--only`, stale-file cleanup, model snapshot) and shares `note_pages`, `_render` and the sheet-tiling step with `render_rows`. It always uses `'chromium'`.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_core_api.py`:

```python
def test_launch_options():
    from cards.render import launch_options
    assert launch_options('chromium') == {}
    assert launch_options('chrome') == {'channel': 'chrome'}
    assert launch_options('/opt/chrome/chrome') == {'executable_path': '/opt/chrome/chrome'}

def test_render_rows(tmp_path):
    import json
    from pathlib import Path
    from cards.render import render_rows
    rows = [{'id': 'a', 'question': 'Q1', 'answer': 'A1'}, {'id': 'b', 'question': 'Q2', 'answer': 'A2'}]
    sheets = render_rows(rows, tmp_path, css='.card{color:red}')
    assert [s['notes'] for s in sheets] == [['a', 'b']]
    assert all(Path(s[side]).is_absolute() and Path(s[side]).is_file() for s in sheets for side in ('fronts', 'backs'))
    assert json.loads((tmp_path/'renders/sheets.json').read_text())['sheets'] == sheets
    assert not (tmp_path/'model').exists() and not list(tmp_path.glob('*.jsonl'))
```

In `tests/mcp/test_cards.py`: after a `render_cards` job completes, the preview folder (`result['prefix']`) contains no `input.jsonl` and no `model/` folder, and `result['sheets'][0]['fronts']` is a readable image through `image_bytes`.

- [ ] **Step 2: Run them; expect failures** (`ImportError: launch_options`, `render_rows`; `input.jsonl` exists)

- [ ] **Step 3: Implement** `launch_options`, `render_rows` and the `browser` parameter; factor the sheet-tiling loop out of `run` so both paths use it.

- [ ] **Step 4: Rewire the MCP layer**

`cards.render_cards` calls `render.render_rows(rows, build, css=css, per_sheet=per_sheet, browser='chromium')` and no longer writes `input.jsonl` or a `model/` folder. `variants.samples` takes a `browser` argument and launches with `**launch_options(browser)`. Task 8 replaces the literal `'chromium'`.

- [ ] **Step 5: Run the tests and the baseline**

```bash
./scripts/check-mcp.sh
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
```

Expected: all pass; `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add src/cards/render/__init__.py src/ankiplusmcp tests
git commit -m "refactor: typed render_rows; MCP stops building a fake render folder"
```

---

### Task 8: Use the system's Chrome when there is no bundled Chromium

**Files:**
- Modify: `src/ankiplusmcp/settings.py`, `doctor.py`, `__main__.py`, `service.py`, `cards.py`, `server.py`
- Modify: `launcher/cli.mjs` (usage text only)
- Test: `tests/mcp/test_settings.py`, `tests/mcp/test_doctor.py`, `tests/mcp/test_cards.py`

**Interfaces:**
- Consumes: `render_rows(..., browser=)`, `launch_options` (Task 7).
- Produces, in `settings`: `'browser'` is an allowed config key; `load_browser(flag: str | None, config_path: Path | None, env) -> str` returns the flag, else the config file's `browser`, else `'auto'`. Valid values: `auto`, `chromium`, `chrome`, or an absolute path to an existing file. Anything else raises `ValueError` naming the four forms.
- Produces: `ankiplusmcp serve --browser <value>`; `Service(root, source_roots, profile=None, browser='auto')` with attribute `browser`.
- Produces, in `doctor`:
  - `system_chrome() -> Path | None`: the first that exists of the macOS application binary under `/Applications/Google Chrome.app`, `shutil.which('google-chrome')`, `shutil.which('google-chrome-stable')`, and on Windows `Google/Chrome/Application/chrome.exe` under `PROGRAMFILES`, `PROGRAMFILES(X86)` and `LOCALAPPDATA`.
  - `resolve_browser(configured: str) -> str | None`: `'chromium'` gives `'chromium'` if the bundled one is installed; `'chrome'` gives `'chrome'` if `system_chrome()`; a path gives itself if the file exists; `'auto'` prefers bundled Chromium, then system Chrome. Otherwise `None`.
  - `require_browser(configured: str) -> str`: the resolved value, or `DomainError('DEPENDENCY', ...)` whose message says which browser was asked for and whose remedy offers both fixes (run `setup`, or install Google Chrome).
- `doctor`'s check is still named `chromium`. It is `ok` when a browser resolves; its detail reads `bundled Chromium`, `system Chrome at <path>` or the configured path. `setup` downloads nothing when a browser already resolves, and says which one is in use. `setup --json` and `capabilities` add `"browser": <resolved or null>`; `chromium_available` becomes "a browser resolves".

- [ ] **Step 1: Write the failing tests**

`tests/mcp/test_settings.py`:

```python
def test_load_browser(tmp_path, monkeypatch):
    import pytest
    from ankiplusmcp import settings
    monkeypatch.setattr(settings, 'default_config_path', lambda: tmp_path/'absent.toml')  # never the real user's file
    assert settings.load_browser(None, None, {}) == 'auto'
    cfg = tmp_path/'c.toml'; cfg.write_text('browser = "chrome"\n')
    assert settings.load_browser(None, cfg, {}) == 'chrome'
    assert settings.load_browser('chromium', cfg, {}) == 'chromium'
    exe = tmp_path/'chrome'; exe.write_text('')
    assert settings.load_browser(str(exe), None, {}) == str(exe)
    for bad in ('firefox', 'relative/chrome', str(tmp_path/'missing')):
        with pytest.raises(ValueError): settings.load_browser(bad, None, {})
    assert settings.load_profile(None, cfg, {}).name == 'default'   # the key is accepted
```

`tests/mcp/test_doctor.py`:

```python
import pytest
from ankiplusmcp import doctor
from ankiplusmcp.store import DomainError

@pytest.mark.parametrize('bundled,chrome,configured,expected', [
    (True,  True,  'auto',     'chromium'),
    (False, True,  'auto',     'chrome'),
    (False, False, 'auto',     None),
    (True,  False, 'chrome',   None),
    (False, True,  'chromium', None),
])
def test_resolve_browser(monkeypatch, bundled, chrome, configured, expected):
    monkeypatch.setattr(doctor, 'have', lambda name: bundled if name == 'chromium' else True)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome' if chrome else None)
    assert doctor.resolve_browser(configured) == expected

def test_missing_browser_is_a_dependency_error(monkeypatch):
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: None)
    with pytest.raises(DomainError) as caught: doctor.require_browser('chrome')
    assert caught.value.code == 'DEPENDENCY' and 'Chrome' in caught.value.message and 'setup' in caught.value.remedy

def test_doctor_and_setup_accept_system_chrome(monkeypatch, tmp_path, capsys):
    import json, subprocess
    monkeypatch.setattr(doctor, 'have', lambda name: name == 'tesseract')
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome')
    check = next(c for c in doctor.run_checks(tmp_path) if c['name'] == 'chromium')
    assert check['status'] == 'ok' and 'system Chrome' in check['detail']
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('setup must not download'))
    assert doctor.setup_main(['--yes', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['browser'] == 'chrome'
```

`tests/mcp/test_cards.py`: `Service(tmp_path/'work', [tmp_path], browser='chrome')` with `doctor.system_chrome` and `doctor.have` patched to "nothing installed": `render_cards` raises `DomainError` with code `DEPENDENCY` before any job is created. And, skipped unless `doctor.system_chrome()` is truthy, a real render with `browser='chrome'` that completes and returns a readable sheet.

- [ ] **Step 2: Run them; expect failures**

- [ ] **Step 3: Implement** the setting, the flag, the resolver, the `doctor`/`setup`/`capabilities` changes, and pass `doctor.require_browser(self.browser)` to `render_rows` and `variants.samples` in place of `doctor.require('chromium')` and the literal. Add `--browser VALUE` to the "Server flags" line in `launcher/cli.mjs`.

- [ ] **Step 4: Run** `./scripts/check-mcp.sh` and `npm test`. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/ankiplusmcp launcher/cli.mjs tests/mcp
git commit -m "feat: previews can use the system's Chrome; no download needed when it is present"
```

---

### Task 9: Handshake version, adapter guard, timing and documents

**Files:**
- Modify: `src/ankiplusmcp/server.py`
- Create: `tests/mcp/test_adapters.py`, `tests/tools/time_extract.py`
- Modify: `tests/mcp/test_protocol.py`, `docs/ARCHITECTURE.md`, `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: `.venv/bin/python tests/tools/time_extract.py <empty folder>` prints seconds per figure for rendering and for OCR, and the wall time of a full `extract_source` on a 12-page synthetic PDF, cold and then repeated.

- [ ] **Step 1: Write the failing tests**

In `tests/mcp/test_protocol.py`, add `import importlib.metadata` at the top and, inside the existing stdio test, replace `await session.initialize()` with:

```python
                init = await session.initialize()
                assert init.serverInfo.version == importlib.metadata.version('ankiplusmcp')
```

`tests/mcp/test_adapters.py`:

```python
import ast
from pathlib import Path
SRC = Path(__file__).resolve().parents[2]/'src/ankiplusmcp'

def test_no_private_imports_from_cards():
    for file in SRC.glob('*.py'):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or '').split('.')[0] == 'cards':
                assert not [a.name for a in node.names if a.name.startswith('_')], file.name

def test_no_faked_arguments_or_build_json():
    text = {f.name: f.read_text() for f in SRC.glob('*.py')}
    assert not any('build.json' in body for body in text.values())
    # measure_usage is the one remaining use; it leaves the MCP in 3b.
    assert sum(body.count('SimpleNamespace(') for body in text.values()) == 1
    assert 'SimpleNamespace(' in text['sources.py']
```

- [ ] **Step 2: Run them.** The adapter tests should already pass if Tasks 2, 3 and 7 were done fully; fix any leftover they find. The version assertion fails with `1.30.0`.

- [ ] **Step 3: Set the handshake version** in `create_server`: after constructing `FastMCP`, set `server._mcp_server.version = importlib.metadata.version('ankiplusmcp')`.

- [ ] **Step 4: Add `tests/tools/time_extract.py`** and run it

It generates the same kind of 12-page PDF as the measurement in the spec (one 1400x900 labelled image per page), then prints: render seconds per figure; OCR seconds per figure; wall seconds for `extract_source` cold with an empty cache; wall seconds for a second run into a new output folder with the same cache.

Run: `.venv/bin/python tests/tools/time_extract.py "$(mktemp -d)"`
Record the four numbers, the machine's core count and the Tesseract version.

- [ ] **Step 5: Update the documents**

`docs/ARCHITECTURE.md`: in section 6 and the "Performance" entry of section 13, replace the 220 s statement with the numbers from Step 4, labelled as synthetic, and say what is still unmeasured (real lectures; label recall is unchanged by construction because OCR settings did not change). Add one paragraph naming the typed functions as the interface the MCP uses. `README.md`: document `--browser` and the `browser` config key, and that `setup` is not needed when Google Chrome is installed.

- [ ] **Step 6: Full verification**

```bash
./scripts/check-mcp.sh
npm test
CARDS_PUBLIC_CI=1 PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/contract
.venv/bin/python tests/tools/cli_baseline.py compare builds/_cli-baseline
.venv/bin/python scripts/check_privacy.py && .venv/bin/python scripts/check_versions.py
git diff --stat main -- src/cards tests/contract .codex .agents .claude
```

Expected: all suites pass; the contract run shows `261 passed, 24 skipped`; `IDENTICAL`; both scripts exit 0; the diff lists only the seven permitted files under `src/cards/` and nothing under `tests/contract`, `.codex`, `.agents` or `.claude`.

- [ ] **Step 7: Commit**

```bash
git add src/ankiplusmcp/server.py tests docs/ARCHITECTURE.md README.md
git commit -m "fix: handshake reports the package version; guard the adapters; record timings"
```

- [ ] **Step 8: Stop and ask the owner**

Report what was built and the numbers from Step 4, then ask for two things. Do not skip either and do not proceed without an answer.

1. The private fixtures in `tests/fixtures/private/` (the L006 and L007 lecture PDFs, `l006_v1_drafts.jsonl`, `transcripts/l006`, `l007_labels.json`). With them in place run:

```bash
PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/contract
PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q -o python_functions='char_*' tests/characterization
```

   Expected: no skips, no failures; label recall at or above 85%. Report the cold extraction time of the L006 lecture.
2. Whether to release: the version bump, the tag and the push are the owner's to approve.
