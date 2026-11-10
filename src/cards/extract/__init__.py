"""Source extraction orchestration; no model or network calls."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
from ..common.paths import Build
from ..common.files import read_json, write_json, write_text
from ..common.errors import CardsError
from ..common.output import Result
from ..common.source_data import source_path, selection
from . import text_source, objectives, mapgen, summary

CACHE_VERSION = 5

def run(args):
    build = Build(args.build)
    path, state = source_path(build)
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise CardsError('E21',f'{path}: line 1 field source unreadable','make it available offline, then re-run') from exc
    cache = build.path('source/slides.json')
    if cache.is_file():
        old = read_json(cache)
        if isinstance(old,dict) and (old.get('source_sha256'),old.get('selection'),old.get('cache_version')) == (digest,args.slides,CACHE_VERSION) and all(build.path('source/'+f['file']).is_file() for s in old['slides'] for f in s['figures']) and build.path('source/map.md').is_file() and build.path('source/objectives.json').is_file() and build.path('source/slides_summary.json').is_file():
            return Result(lines=[f"cache hit: {old['slide_count']} slides"], files=[build.path('source/map.md')])
    # Invalidate the manifest before replacing any associated figure crops.
    cache.unlink(missing_ok=True)
    if path.suffix.lower()=='.pdf':
        from . import pdf
        slides = pdf.read(path,build,args.slides)
    elif path.suffix.lower() in ('.txt','.md','.markdown'):
        slides = text_source.read(path)
        chosen = selection(args.slides,[s['n'] for s in slides])
        slides = [s for s in slides if s['n'] in chosen]
    else:
        raise CardsError('E21',f'{path}: line 1 field source.kind unsupported','use PDF, markdown or text')
    # Tesseract subprocesses use one OpenMP thread (set per subprocess in OCR).
    from .ocr import extract
    def work(f):
        try:
            result = extract(build.path('source/'+f['file']))
            f['ocr_labels'] = result['regions']
            f['repeated_labels'] = list(result['repeated'])
        except Exception as exc:
            raise CardsError('E24',f"{path}: field {f['fig_id']} OCR failed: {exc}",'install Tesseract and retry extraction') from exc
    # Render only on the main thread; OCR workers take the largest queued
    # crops first, avoiding a tail of large late-lecture figures.
    from queue import PriorityQueue
    from PIL import Image
    queue = PriorityQueue()
    records = []
    def worker():
        while True:
            _, _, figure = queue.get()
            if figure is None:
                return
            work(figure)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(worker) for _ in range(4)]
        index = 0
        try:
            for slide in slides:
                records.append(slide)
                for figure in slide['figures']:
                    with Image.open(build.path('source/'+figure['file'])) as image:
                        area = image.width*image.height
                    queue.put((-area,index,figure))
                    index += 1
        finally:
            for sentinel in range(4):
                queue.put((float('inf'),sentinel,None))
        for future in futures:
            future.result()
    slides = records
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
            'selection':args.slides,'cache_version':CACHE_VERSION,'slides':slides}
    write_json(cache,data,'cards extract')
    write_json(build.path('source/objectives.json'),objs,'cards extract')
    write_json(build.path('source/slides_summary.json'),summary.build(lecture,slides,objs['objectives']),'cards extract')
    write_text(build.path('source/map.md'),mapgen.generate(lecture,slides,objs['objectives']),'cards extract')
    flagged = sum(bool(s['flags']) for s in slides)
    return Result('FINDINGS' if flagged or objs['flags'] else 'OK',
        [f"{len(slides)} slides · {len(figs)} figures · {flagged} flagged · {len(objs['objectives'])} objectives"],
        [build.path('source/map.md')],1 if flagged or objs['flags'] else 0)
