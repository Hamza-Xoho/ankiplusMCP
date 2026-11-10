"""Build native Anki image occlusions from extracted or estimated rectangles."""
import html
import math
import re

from .common.errors import CardsError, Refused
from .common.files import read_json, read_jsonl, write_json, write_jsonl, write_text
from .common.output import Result
from .common.paths import Build
from .common.source_data import slides_data
from .extract.ocr import _norm

TOOL = 'cards figures'


def _labels(figure):
    """Unique OCR label texts, in reading order."""
    return list(dict.fromkeys(
        region.get('text', '').strip() for region in figure.get('ocr_labels') or []
        if isinstance(region, dict) and region.get('text', '').strip()))


def _kind(labels):
    return 'anatomy_diagram' if len(labels) >= 5 else ('diagram' if labels else 'image')


def _summary(build):
    """Text-only figure listing: the agent never reads a full-resolution PNG."""
    data = slides_data(build)
    drafts = build.path('drafts.jsonl')
    drafts = list(read_jsonl(drafts)) if drafts.is_file() else []
    occluded = {row.get('group'): row.get('id') for row in drafts
                if isinstance(row, dict) and row.get('kind') == 'io'}
    rows = []
    for slide in data['slides']:
        for figure in slide.get('figures') or []:
            if not isinstance(figure, dict):
                continue
            labels = _labels(figure)
            regions = [region for region in figure.get('ocr_labels') or []
                       if isinstance(region, dict) and isinstance(region.get('group'), int)]
            seen = {}
            for region in regions:
                seen.setdefault(region['group'], region.get('text', '').strip())
            rows.append({'id': figure.get('fig_id'), 'slide': slide['n'],
                         'labels': labels, 'kind': _kind(labels),
                         'groups': [f'{key} {value}' for key, value in sorted(seen.items())],
                         'draft': occluded.get(figure.get('fig_id'))})
    parts = ['# Figure candidates', '',
             'Text only: decide from these labels, then run `cards figures --fig <id>`.',
             'Inspect the extracted figure to choose masks; check generated `*_preview.png` after masking.', '']
    for row in rows:
        parts.append(f"## {row['id']} — slide {row['slide']} · {row['kind']} · "
                     f"{len(row['labels'])} labels")
        if row['groups']:
            parts.append('groups: ' + '; '.join(row['groups']))
        else:
            parts.append('labels: ' + (', '.join(row['labels']) or 'none (estimate regions)'))
        if row['draft']:
            parts.append(f'occluded draft: {row["draft"]}')
        parts.append('')
    path = build.path('source/figures_summary.md')
    write_text(path, '\n'.join(parts), TOOL)
    lines = [f"{len(rows)} figure candidates · "
             f"{sum(1 for row in rows if row['labels'])} with OCR labels"]
    for row in rows[:8]:
        draft = f" · draft {row['draft']}" if row['draft'] else ''
        lines.append(f"{row['id']} · slide {row['slide']} · {row['kind']} · "
                     f"{len(row['labels'])} labels{draft}")
        if row['labels']:
            more = '' if len(row['labels']) <= 6 else ', …'
            lines.append('  ' + ', '.join(row['labels'][:6]) + more)
    if len(rows) > 8:
        lines.append(f'… {len(rows)-8} more in source/figures_summary.md')
    if rows:
        lines.append('Next: cards figures --build <build> --fig <id> (preview only)')
    return Result(lines=lines, files=[path])


def _invalid(field, remedy='repair the figure input and retry'):
    return CardsError('E51', f'figures: line 1 field {field} invalid', remedy)


def _regions(raw, keep):
    if not isinstance(raw, list):
        raise _invalid('regions')
    regions = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise _invalid(f'regions[{i}]')
        values = {}
        for name in ('left', 'top', 'width', 'height'):
            value = item.get(name)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 1):
                raise _invalid(f'regions[{i}].{name}', 'use fractional coordinates between 0 and 1')
            values[name] = float(value)
        if (values['width'] <= 0 or values['height'] <= 0
                or values['left'] + values['width'] > 1.0001
                or values['top'] + values['height'] > 1.0001):
            raise _invalid(f'regions[{i}].bounds', 'keep each rectangle inside the figure')
        group = item.get('group')
        if group is not None and (isinstance(group, bool) or not isinstance(group, int) or group < 1):
            raise _invalid(f'regions[{i}].group', 'use positive integer group IDs')
        text = item.get('text', '')
        if not isinstance(text, str):
            raise _invalid(f'regions[{i}].text')
        # Explicit OCR groups retain v1 behavior. Estimated rectangles can omit
        # them; matching label text then supplies the shared group automatically.
        key = ('group', group) if group is not None else (
            ('text', _norm(text)) if _norm(text) else ('solo', i))
        regions.append({**values, 'key': key, 'group': group, 'text': text})
    if keep is not None:
        if not isinstance(keep, str) or not re.fullmatch(r'\s*\d+(?:\s*,\s*\d+)*\s*', keep):
            raise _invalid('keep', 'use comma-separated positive group IDs')
        groups = {int(x.strip()) for x in keep.split(',')}
        present = {r['group'] for r in regions}
        if not groups <= present:
            raise _invalid('keep', 'choose group IDs present in the regions')
        regions = [r for r in regions if r['group'] in groups]
    remap = {}
    for region in regions:
        key = region.pop('key')
        region['index'] = remap.setdefault(key, len(remap) + 1)
    return regions


def _fmt(value):
    text = f'{value:.4f}'.rstrip('0').rstrip('.')
    return text[1:] if text.startswith('0.') else text or '0'


def _occlusion(regions, mode):
    parts = []
    for region in regions:
        coordinates = ':'.join(f'{key}={_fmt(region[key])}'
                               for key in ('left', 'top', 'width', 'height'))
        parts.append('{{c%d::image-occlusion:rect:%s:oi=%d}}' %
                     (region['index'], coordinates, mode == 'one'))
    return '<br>'.join(parts) + '<br>'


def _check_output(path):
    sidecar = path.with_suffix(path.suffix + '.json')
    if path.exists() or sidecar.exists():
        owned = False
        if sidecar.is_file():
            data = read_json(sidecar)
            metadata = data.get('_meta') if isinstance(data, dict) else None
            owned = isinstance(metadata, dict) and metadata.get('tool') == TOOL
        if not owned:
            raise Refused('E52', f'{path}: line 1 field output already exists',
                          'move the unrelated file before generating this occlusion')
    return sidecar


def _images(image, regions, media, preview):
    from PIL import ImageDraw
    image.save(media, format='PNG')
    preview_image = image.copy()
    draw = ImageDraw.Draw(preview_image)
    palette = [(220, 30, 30), (0, 140, 255), (0, 170, 70),
               (200, 120, 0), (150, 0, 200), (0, 150, 150)]
    width, height = image.size
    for region in regions:
        index = region['index']
        color = palette[(index - 1) % len(palette)]
        box = [region['left'] * width, region['top'] * height,
               (region['left'] + region['width']) * width,
               (region['top'] + region['height']) * height]
        draw.rectangle(box, outline=color, width=4)
        draw.text((box[0], max(0, box[1] - 13)), f'c{index}', fill=color)
    preview_image.save(preview, format='PNG')


def run(args):
    build = Build(args.build)
    if getattr(args, 'summary', False):
        return _summary(build)
    data = slides_data(build)
    ident = getattr(args, 'fig', None) or getattr(args, 'figure', None)
    if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
        raise _invalid('fig', 'choose --fig <fig_id> or --summary')
    matches = [(slide['n'], fig) for slide in data['slides'] for fig in slide['figures']
               if isinstance(fig, dict) and fig.get('fig_id') == ident]
    if len(matches) != 1:
        raise _invalid('fig', 'choose one unique fig_id from source/slides.json')
    slide_number, figure = matches[0]
    relative = figure.get('file')
    if not isinstance(relative, str):
        raise _invalid('figure.file')
    source = build.path('source/' + relative)
    if not source.is_file():
        raise Refused('E52', f'{source}: line 1 field figure missing', 'run cards extract first')
    target_path = build.path('target.json')
    if not target_path.is_file():
        raise Refused('E52', f'{target_path}: line 1 field target missing', 'run cards target first')
    target = read_json(target_path)
    if not isinstance(target, dict):
        raise _invalid('target')
    deck, source_tag = target.get('deck'), target.get('source_tag')
    tiers = target.get('tier_tags')
    tier_tag = tiers.get('1') if isinstance(tiers, dict) else None
    base_tags = target.get('base_tags', [])
    note_type = target.get('io_note_type', 'Image Occlusion')
    if (not isinstance(deck, str) or not deck.strip() or '::' in deck
            or not isinstance(source_tag, str) or not source_tag.startswith('#ColdRecall::#Source::')
            or not isinstance(tier_tag, str) or not tier_tag.startswith('#ColdRecall::!Tier::')
            or not isinstance(base_tags, list)
            or not all(isinstance(t, str) and t.startswith('#ColdRecall::') and not any(c.isspace() for c in t)
                       for t in [*base_tags, source_tag, tier_tag])
            or not isinstance(note_type, str) or not note_type.strip()):
        raise _invalid('target', 'run cards target and supply valid source/tier tags')
    mode = getattr(args, 'mode', 'one')
    if mode not in ('one', 'all'):
        raise _invalid('mode', 'choose one or all')
    region_arg = getattr(args, 'regions', None)
    raw = read_json(build.path(region_arg)) if region_arg else figure.get('ocr_labels', [])
    if isinstance(raw, dict):
        raw = raw.get('regions')
    regions = _regions(raw, getattr(args, 'keep', None))
    if not regions:
        return Result('FINDINGS', ['OCR found no labels; estimate rectangles by eye and supply --regions.'], [], 1)
    media_relative = f'source/figures/{ident}_io.png'
    preview_relative = f'source/figures/{ident}_io_preview.png'
    media, preview = build.path(media_relative), build.path(preview_relative)
    if source in (media, preview):
        raise _invalid('figure.file', 'keep extracted input separate from generated occlusions')
    try:
        number = int(target.get('number', 0))
    except (ValueError, TypeError) as exc:
        raise _invalid('target.number') from exc
    # AnkiMCP normalizes stored media names to lowercase. Use the same name
    # before rendering and gating so writes need no field repair.
    filename = (f'l{number:03d}_{ident}.png' if number > 0 else f'{ident}.png').lower()
    note = {'kind': 'io', 'notetype': note_type, 'deck': deck,
            'fields': {'Occlusion': _occlusion(regions, mode),
                       'Image': f'<img src="{html.escape(filename, quote=True)}">',
                       'Header': '', 'Back Extra': f'<div class="src">{html.escape(source_tag)}, slide {slide_number}</div>',
                       'Comments': ''},
            'tags': list(dict.fromkeys([*base_tags, source_tag, tier_tag])),
            'tier': 1, 'objective': None, 'source_ref': [slide_number],
            'group': ident, 'action': 'create', 'nid': None, 'status': 'draft',
            'media': [{'path': media_relative, 'filename': filename}],
            'preview': preview_relative}
    drafts_path = build.path('drafts.jsonl')
    drafts = list(read_jsonl(drafts_path)) if drafts_path.exists() else []
    if not all(isinstance(row, dict) for row in drafts):
        raise _invalid('drafts', 'repair drafts.jsonl before appending')
    existing = [row for row in drafts if row.get('kind') == 'io' and row.get('group') == ident]
    used = [int(row['id'][1:]) for row in drafts
            if isinstance(row.get('id'), str) and re.fullmatch(r'n\d{3,}', row['id'])]
    note['id'] = existing[0].get('id') if existing else f'n{max(used, default=0)+1:03d}'
    if existing and (len(existing) != 1 or existing[0] != note):
        raise Refused('E52', f'{drafts_path}: line 1 field {note["id"]} already exists',
                      'preserve the existing draft; explicitly resolve the conflicting figure draft')
    sidecars = [_check_output(path) for path in (media, preview)]
    if not existing or not all(path.is_file() for path in (media, preview)):
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(source) as image:
                image = image.convert('RGB')
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            raise _invalid('figure.image', 'run cards extract to restore a readable image') from exc
        media.parent.mkdir(parents=True, exist_ok=True)
        _images(image, regions, media, preview)
        for path, sidecar in zip((media, preview), sidecars):
            write_json(sidecar, {'file': str(path.relative_to(build.root)),
                       'figure': ident, 'source': str(source.relative_to(build.root)),
                       'mode': mode, 'regions': regions}, TOOL)
    if not existing:
        write_jsonl(drafts_path, [*drafts, note], TOOL)
    return Result(lines=[f'{note["id"]}: {len(regions)} masks, {len({r["index"] for r in regions})} cards'],
                  files=[drafts_path, preview])
