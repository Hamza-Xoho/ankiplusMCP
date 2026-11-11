"""Source extraction orchestration; no model or network calls."""
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import os
import threading
from pathlib import Path
from ..common.paths import Build
from ..common.files import read_json, write_json, write_text
from ..common.errors import CardsError
from ..common.output import Result
from ..common.source_data import source_path, selection
from . import text_source, objectives, mapgen, summary

CACHE_VERSION = 5

class ExtractionCancelled(Exception):
    """Raised when `should_cancel` returns true; no `slides.json` is left behind."""

@dataclass(frozen=True)
class Extraction:
    slide_count: int
    figure_count: int
    flagged: int
    objective_count: int
    objective_flags: bool
    cached: bool            # on a cache hit only slide_count, cached and map are meaningful
    map: Path

def run(args):
    build = Build(args.build)
    path, state = source_path(build)
    found = extract_source(path, build.root, args.slides)
    if found.cached:
        return Result(lines=[f"cache hit: {found.slide_count} slides"], files=[found.map])
    findings = bool(found.flagged or found.objective_flags)
    return Result('FINDINGS' if findings else 'OK',
        [f"{found.slide_count} slides · {found.figure_count} figures · {found.flagged} flagged · {found.objective_count} objectives"],
        [found.map],1 if findings else 0)

def default_workers() -> int:
    return os.cpu_count() or 4

class OcrFailure(Exception):
    """OCR of one image failed; `path` names it and `__cause__` holds the error."""
    def __init__(self, path):
        super().__init__(str(path))
        self.path = path

def ocr_figures(paths: list[Path], *, workers: int | None = None, cache_dir: Path | None = None,
                on_progress: Callable[[int, int], None] | None = None,
                should_cancel: Callable[[], bool] | None = None) -> dict[Path, dict]:
    """OCR each distinct image once (by content) on a thread pool, largest first.

    Every path gets its own copy of its group's result. on_progress(done, total) counts figures and
    is called from the calling thread only. Raises OcrFailure (naming the first path of the failed
    group) or ExtractionCancelled."""
    import copy
    from concurrent.futures import as_completed
    from PIL import Image
    from . import ocr
    groups: dict[str, list[Path]] = {}
    for p in paths:
        groups.setdefault(hashlib.sha256(Path(p).read_bytes()).hexdigest(), []).append(p)
    def area(group):
        try:
            with Image.open(group[0]) as image:
                return image.width*image.height
        except Exception:
            return Path(group[0]).stat().st_size
    ordered = sorted(groups.values(), key=area, reverse=True)
    stop = threading.Event()
    def work(group):
        if stop.is_set(): return None
        if should_cancel and should_cancel():
            stop.set()
            raise ExtractionCancelled()
        try:
            return ocr.cached_extract(group[0], cache_dir)
        except Exception as exc:
            stop.set()
            raise OcrFailure(group[0]) from exc
    results: dict[Path, dict] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers or default_workers())) as pool:
        futures = {pool.submit(work, group): group for group in ordered}
        try:
            for future in as_completed(futures):
                found = future.result()
                if found is None: continue
                for p in futures[future]:
                    results[p] = copy.deepcopy(found)
                done += len(futures[future])
                if on_progress: on_progress(done, len(paths))
        except BaseException:
            stop.set()
            raise
    return {p: results[p] for p in paths}

def extract_source(source: Path, out_dir: Path, slides: str | None = None, *,
                   on_progress: Callable[[str, int, int | None], None] | None = None,
                   should_cancel: Callable[[], bool] | None = None,
                   workers: int | None = None, ocr_cache: Path | None = None) -> Extraction:
    """Extract `source` into `out_dir/source`; reads no build.json.

    on_progress('slides', done, None) follows each slide read; on_progress('figures', done, total)
    follows each finished OCR group, where total is the number of figures. should_cancel is asked
    after each slide and before each figure's OCR (from worker threads, so it must be thread-safe
    and quick); on_progress is only ever called from the calling thread. workers sets the OCR thread
    count (default: every core); ocr_cache is a folder that remembers OCR results by image content."""
    path = Path(source)
    build = Build(out_dir)
    spec = slides
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise CardsError('E21',f'{path}: line 1 field source unreadable','make it available offline, then re-run') from exc
    cache = build.path('source/slides.json')
    if cache.is_file():
        old = read_json(cache)
        if isinstance(old,dict) and (old.get('source_sha256'),old.get('selection'),old.get('cache_version')) == (digest,spec,CACHE_VERSION) and all(build.path('source/'+f['file']).is_file() for s in old['slides'] for f in s['figures']) and build.path('source/map.md').is_file() and build.path('source/objectives.json').is_file() and build.path('source/slides_summary.json').is_file():
            return Extraction(old['slide_count'],0,0,0,False,True,build.path('source/map.md'))
    # Invalidate the manifest before replacing any associated figure crops.
    cache.unlink(missing_ok=True)
    if path.suffix.lower()=='.pdf':
        from . import pdf
        slides = pdf.read(path,build,spec)
    elif path.suffix.lower() in ('.txt','.md','.markdown'):
        slides = text_source.read(path)
        chosen = selection(spec,[s['n'] for s in slides])
        slides = [s for s in slides if s['n'] in chosen]
    else:
        raise CardsError('E21',f'{path}: line 1 field source.kind unsupported','use PDF, markdown or text')
    records = []
    for slide in slides:
        records.append(slide)
        if on_progress: on_progress('slides',len(records),None)
        if should_cancel and should_cancel():
            raise ExtractionCancelled()
    slides = records
    figures = {build.path('source/'+f['file']): f for s in slides for f in s['figures']}
    try:
        found = ocr_figures(list(figures), workers=workers, cache_dir=ocr_cache,
                            on_progress=(lambda done, total: on_progress('figures',done,total)) if on_progress else None,
                            should_cancel=should_cancel)
    except OcrFailure as failure:
        figure = figures[failure.path]
        raise CardsError('E24',f"{path}: field {figure['fig_id']} OCR failed: {failure.__cause__}",'install Tesseract and retry extraction') from failure.__cause__
    for figure_path, figure in figures.items():
        figure['ocr_labels'] = found[figure_path]['regions']
        figure['repeated_labels'] = list(found[figure_path]['repeated'])
    if not slides:
        raise CardsError('E21',f'{path}: line 1 field text empty','supply a non-empty lecture source')
    figs = [f for s in slides for f in s['figures']]
    previous = None
    for s in slides:
        s['word_count'] = len(s['text'].split())
        if s['word_count']<15: s['flags'].append('low_text')
        if s['title'] and s['title']==previous: s['flags'].append('repeated_title')
        previous = s['title']
    objs = objectives.find(slides)
    import re
    identity = re.match(r'([A-Za-z]+\d+)[_ -]+L(\d+)', path.stem, re.I)
    lecture = f'{identity[1].upper()}-L{int(identity[2]):03d}' if identity else path.stem
    data = {'lecture':lecture,'slide_count':len(slides),'source_sha256':digest,
            'selection':spec,'cache_version':CACHE_VERSION,'slides':slides}
    write_json(cache,data,'cards extract')
    write_json(build.path('source/objectives.json'),objs,'cards extract')
    write_json(build.path('source/slides_summary.json'),summary.build(lecture,slides,objs['objectives']),'cards extract')
    write_text(build.path('source/map.md'),mapgen.generate(lecture,slides,objs['objectives']),'cards extract')
    flagged = sum(bool(s['flags']) for s in slides)
    return Extraction(len(slides),len(figs),flagged,len(objs['objectives']),bool(objs['flags']),False,build.path('source/map.md'))
