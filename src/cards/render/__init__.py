"""Render inert, phone-width ColdRecall cards in real Chromium."""
from pathlib import Path

from PIL import Image
import re
import tempfile

from cards.common.errors import CardsError, Refused
from cards.common.files import read_json, read_jsonl, write_json, write_text
from cards.common.output import Result
from cards.common.paths import Build
from .occlusion import bodies as occlusion_bodies
from .sheets import tile
from .templates import CLOZE, fill, page

ASSETS = Path(__file__).resolve().parents[1] / 'assets/coldrecall-cloze'


def artifact_meta(build, relative):
    path = build.path(str(relative) + '.json')
    previous = read_json(path) if path.exists() else {}
    write_json(path, {'_meta': previous['_meta']} if '_meta' in previous else {}, 'cards render')


def note_pages(build, note, front_template, back_template, css, anki_html):
    nid = str(note.get('id', ''))
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', nid):
        raise CardsError('E50', f'drafts.jsonl: line 1 field id {nid!r} unsafe', 'use a stable alphanumeric note id')
    if not anki_html and (not isinstance(note.get('fields'), dict)
                          or not all(isinstance(value, str) for value in note['fields'].values())):
        raise CardsError('E50', 'drafts.jsonl: line 1 field fields invalid', 'supply string fields in a JSON object')
    media = {}
    for item in note.get('media', []):
        path = build.path(item['path'])
        media[item['filename']] = str(path)
    if anki_html:
        fronts = [(nid, note['question'])]
        back = note['answer']
    elif note.get('kind') == 'io':
        io_fronts, back = occlusion_bodies(build, note['fields'], media)
        fronts = [(f'{nid}_c{number}', body) for number, body in io_fronts]
    else:
        fields, tags = note['fields'], note.get('tags', [])
        if note.get('kind') == 'basic' and '{{cloze:Text}}' in front_template:
            raise CardsError('E50', 'drafts.jsonl: line 1 field model does not match basic fields',
                             'supply the basic note type snapshot in build/model')
        numbers = sorted({int(m[1]) for m in CLOZE.finditer(fields.get('Text', ''))}) or [1]
        fronts = [(f'{nid}_c{number}', fill(front_template, fields, tags, number, 'front')) for number in numbers]
        back = fill(back_template, fields, tags, None, 'back', fronts[0][1])
    documents = [(label + '_front', page(css, body, build, media)) for label, body in fronts]
    documents.append((nid + '_back', page(css, back, build, media)))
    return nid, documents


def _render(build, prepared, selected):
    try:
        from playwright.sync_api import sync_playwright, Error
    except ImportError as exc:
        raise CardsError('E50', 'renderer unavailable', 'install dependencies and run playwright install chromium') from exc
    try:
        with tempfile.TemporaryDirectory(prefix='.chromium-', dir=build.path('renders')) as profile:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=profile, headless=True, java_script_enabled=False,
                    viewport={'width':390, 'height':40}, service_workers='block',
                    accept_downloads=False, downloads_path=profile, traces_dir=profile)
                try:
                    context.route('**/*', lambda route: route.abort())
                    browser_page = context.pages[0] if context.pages else context.new_page()
                    for nid, documents in prepared:
                        if nid not in selected:
                            continue
                        for label, document in documents:
                            html_path = build.path(f'renders/cards/{label}.html')
                            png_path = build.path(f'renders/cards/{label}.png')
                            # Keep unchanged HTML, including provenance, byte-identical on resume.
                            existing = html_path.read_text(encoding='utf-8') if html_path.exists() else ''
                            if existing.partition('\n')[2] != document:
                                write_text(html_path, document, 'cards render')
                            browser_page.set_content(document, wait_until='load')
                            browser_page.screenshot(path=str(png_path), full_page=True, animations='disabled')
                            # Full-page Chromium screenshots include horizontal overflow. A phone
                            # shows only the 390 px viewport; crop that overflow without changing CSS.
                            with Image.open(png_path) as screenshot:
                                if screenshot.width > 390:
                                    screenshot.crop((0, 0, 390, screenshot.height)).save(png_path)
                            artifact_meta(build, f'renders/cards/{label}.png')
                finally:
                    context.close()
    except Error as exc:
        raise CardsError('E50', f'Chromium render failed: {str(exc).splitlines()[0]}',
                         'run playwright install chromium and check renderer dependencies') from exc


def run(args):
    build = Build(args.build)
    per_sheet = getattr(args, 'per_sheet', 8)
    if per_sheet < 1:
        raise CardsError('E50', 'per-sheet: line 1 field value must be positive', 'use --per-sheet 8')
    anki_html = getattr(args, 'anki_html', None)
    source = build.path(anki_html) if anki_html else build.path('drafts.jsonl')
    if not source.is_file():
        raise Refused('E50', f'{source}: line 1 field drafts missing', 'write drafts.jsonl before rendering')
    try:
        notes = list(read_jsonl(source))
    except TypeError as exc:
        raise CardsError('E50', f'{source}: line 1 field record invalid', 'supply JSON objects in JSONL') from exc
    for index, note in enumerate(notes, 1):
        if not isinstance(note, dict):
            raise CardsError('E50', f'{source}: line {index} field record invalid', 'supply JSON objects in JSONL')
    notes = [note for note in notes if note.get('status') != 'dropped']
    if not notes:
        raise Refused('E50', f'{source}: line 1 field drafts empty', 'provide at least one active draft')
    model = build.path('model')
    bundled = not model.exists()
    if bundled:
        model = ASSETS
    def model_file(name):
        path = model/name if bundled else build.path('model/' + name)
        if not path.is_file():
            raise CardsError('E50', f'{path}: line 1 field model missing', 'supply front.html, back.html and style.css')
        return path.read_text(encoding='utf-8')
    front_template, back_template, css = [model_file(name) for name in ('front.html', 'back.html', 'style.css')]
    try:
        prepared = [note_pages(build, note, front_template, back_template, css, bool(anki_html)) for note in notes]
    except (KeyError, TypeError) as exc:
        raise CardsError('E50', f'{source}: line 1 field renderer input invalid', 'run cards check and repair draft fields') from exc
    ids = [nid for nid, _ in prepared]
    if len(ids) != len(set(ids)):
        raise CardsError('E50', f'{source}: line 1 field id duplicated', 'use unique note ids')
    only = getattr(args, 'only', None)
    selected = set(only.split(',')) if only else set(ids)
    if not selected <= set(ids):
        raise CardsError('E50', 'only: line 1 field id unknown', 'choose active note ids from drafts.jsonl')
    sheets = []
    for start in range(0, len(ids), per_sheet):
        index = len(sheets) + 1
        sheets.append({'fronts':str(build.path(f'renders/sheets/sheet_{index:02d}_fronts.png')),
                       'backs':str(build.path(f'renders/sheets/sheet_{index:02d}_backs.png')),
                       'notes':ids[start:start+per_sheet]})
    manifest_path = build.path('renders/sheets.json')
    previous = read_json(manifest_path) if manifest_path.exists() else {}
    if only:
        if previous.get('sheets') != sheets:
            raise Refused('E50', f'{manifest_path}: line 1 field sheets changed or missing',
                          'run cards render without --only to create the current sheet mapping')
        for nid, documents in prepared:
            if nid not in selected and any(not build.path(f'renders/cards/{label}.png').is_file() for label, _ in documents):
                raise Refused('E50', f'renders/cards: line 1 field {nid} image missing', 'run cards render without --only first')
    build.path('renders/cards').mkdir(parents=True, exist_ok=True)
    build.path('renders/sheets').mkdir(parents=True, exist_ok=True)
    _render(build, prepared, selected)
    # A changed cloze count must not leave obsolete fronts in a review folder.
    for nid, documents in prepared:
        if nid not in selected:
            continue
        desired = {label + suffix for label, _ in documents for suffix in ('.png', '.html', '.png.json')}
        generated = re.compile(re.escape(nid) + r'(?:_c[0-9]+)?_(?:front|back)\.(?:png|html|png\.json)$')
        for candidate in build.path('renders/cards').iterdir():
            if generated.fullmatch(candidate.name) and candidate.name not in desired:
                build.path(candidate).unlink()
    by_id = dict(prepared)
    for sheet in sheets:
        if not set(sheet['notes']) & selected:
            continue
        fronts, backs = [], []
        for nid in sheet['notes']:
            for label, _ in by_id[nid]:
                item = (label.removesuffix('_front').removesuffix('_back'), build.path(f'renders/cards/{label}.png'))
                (backs if label.endswith('_back') else fronts).append(item)
        for side, images in [('fronts', fronts), ('backs', backs)]:
            path = build.path(sheet[side])
            tile(images, path)
            artifact_meta(build, str(path.relative_to(build.root)))
    if not only:
        current = {Path(sheet[side]).name for sheet in sheets for side in ('fronts', 'backs')}
        for candidate in build.path('renders/sheets').iterdir():
            if re.fullmatch(r'sheet_[0-9]+_(?:fronts|backs)\.png(?:\.json)?', candidate.name):
                name = candidate.name.removesuffix('.json')
                if name not in current:
                    build.path(candidate).unlink()
    data = {'sheets':sheets}
    if '_meta' in previous:
        data['_meta'] = previous['_meta']
    write_json(manifest_path, data, 'cards render')
    total_fronts = sum(len(documents)-1 for nid, documents in prepared if nid in selected)
    model_notice = 'bundled assets' if bundled else 'build/model snapshot'
    return Result('OK', [f'{len(selected)} notes, {total_fronts} fronts; {len(sheets)} sheet pairs (model: {model_notice})'], [manifest_path])
