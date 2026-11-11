"""Record and compare a byte-level snapshot of the `cards` CLI.

    cli_baseline.py record <dir>    write <dir>/cli_baseline.json
    cli_baseline.py compare <dir>   rebuild the snapshot and diff it against that file

The tool builds its own inputs in a temporary folder, runs the CLI as a
subprocess and snapshots stdout, exit codes and every file the CLI writes.
Run-to-run noise (timestamps, the temporary root, durations) is removed by
`normalize`, never by changing the CLI.
"""
import difflib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT = 'cli_baseline.json'
TEXT_SUFFIXES = {'.json', '.jsonl', '.md', '.html', '.txt'}
SKIP_NAMES = {'log.jsonl'}


# ---------------------------------------------------------------- normalize

def _strip_meta(value):
    if isinstance(value, dict):
        return {k: _strip_meta(v) for k, v in value.items() if k != '_meta'}
    if isinstance(value, list):
        return [_strip_meta(v) for v in value]
    return value


def _mask(text, root):
    root = Path(root)
    # Longest first, so the resolved form is not half-replaced.
    for form in sorted({str(root), str(root.resolve())}, key=len, reverse=True):
        text = text.replace(form, '<ROOT>')
        text = text.replace(form.replace('/', '\\/'), '<ROOT>')
    return text


def normalize(name: str, text: str, root: Path) -> str:
    suffix = Path(name).suffix
    if suffix == '.json':
        try:
            text = json.dumps(_strip_meta(json.loads(text)), ensure_ascii=False, indent=2) + '\n'
        except ValueError:
            pass
    elif suffix == '.jsonl':
        lines = []
        for line in text.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                lines.append(line)
                continue
            if isinstance(row, dict) and '_meta' in row:
                row = {k: v for k, v in row.items() if k != '_meta'}
                if not row:
                    continue
            lines.append(json.dumps(_strip_meta(row), ensure_ascii=False))
        text = ''.join(line + '\n' for line in lines)
    elif suffix in ('.md', '.html', '.txt'):
        first, _, rest = text.partition('\n')
        if first.startswith('<!-- cards '):
            text = rest
    return _mask(text, root)


# ------------------------------------------------------------------- inputs

def _make_pdf(path):
    import io
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont
    doc = pymupdf.open()
    page = doc.new_page(width=960, height=540)
    page.insert_text((40, 60), 'Baseline Lecture Overview', fontsize=32)
    page.insert_text((40, 110), 'Learning objectives', fontsize=22)
    for i, line in enumerate(['Describe the nucleus and its envelope',
                              'Explain ribosome function in protein synthesis',
                              'Compare smooth and rough endoplasmic reticulum']):
        page.insert_text((60, 145 + 26 * i), f'{i + 1}. {line}', fontsize=16)
    left = ['The nucleus stores DNA.', 'Nucleoli assemble ribosomes.', 'Pores regulate transport.']
    right = ['Rough ER carries ribosomes.', 'Smooth ER makes lipids.', 'Golgi sorts proteins.']
    for i, (a, b) in enumerate(zip(left, right)):
        page.insert_text((40, 300 + 30 * i), a, fontsize=18)
        page.insert_text((520, 300 + 30 * i), b, fontsize=18)
    page = doc.new_page(width=960, height=540)
    page.insert_text((40, 60), 'Cell Diagram', fontsize=32)
    image = Image.new('RGB', (1400, 900), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=28)
    labels = ['Nucleus', 'Ribosome', 'Golgi', 'Lysosome', 'Vesicle', 'Membrane', 'Cytoplasm', 'Mitochondrion']
    for i, label in enumerate(labels):
        x, y = 80 + (i % 2) * 650, 60 + (i // 2) * 200
        draw.rectangle([x - 10, y - 10, x + 330, y + 60], outline='black', width=3)
        draw.text((x, y), label, fill='black', font=font)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    page.insert_image(pymupdf.Rect(80, 100, 880, 514), stream=buffer.getvalue())
    page = doc.new_page(width=960, height=540)
    page.insert_text((40, 60), 'Vector Drawing', fontsize=32)
    for i in range(6):
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(80 + i * 130, 150, 160 + i * 130, 230 + (i % 2) * 40))
        shape.finish(color=(0, 0, 0), fill=(0.8, 0.9, 1) if i % 2 else (1, 0.9, 0.8), width=2)
        shape.commit()
    for i in range(4):
        shape = page.new_shape()
        shape.draw_line((80, 340 + i * 30), (860, 360 + i * 30))
        shape.finish(color=(0.2, 0.2, 0.2), width=2)
        shape.commit()
    # Dates and the trailer ID would change source_sha256 on every run.
    doc.set_metadata({'creationDate': '', 'modDate': ''})
    doc.save(path, no_new_id=True)
    doc.close()


def _dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def _make_inputs(root):
    pdf = root / 'lecture.pdf'
    _make_pdf(pdf)
    notes = root / 'notes.md'
    notes.write_text('# Cell Basics\nThe cell is the unit of life.\n\n'
                     '# Organelles\nThe nucleus stores DNA.\nMitochondria make ATP.\n', encoding='utf-8')
    for name, source in (('b_pdf', pdf), ('b_text', notes)):
        _dump(root / name / 'build.json', {'source': {'path': str(source)}})
    pdf_build = root / 'b_pdf'
    _dump(pdf_build / 'decks.json', [])
    _dump(pdf_build / 'regions.json', [
        {'left': 0.05, 'top': 0.05, 'width': 0.25, 'height': 0.08, 'group': 1, 'text': 'Nucleus'},
        {'left': 0.50, 'top': 0.05, 'width': 0.25, 'height': 0.08, 'group': 2, 'text': 'Ribosome'},
        {'left': 0.05, 'top': 0.25, 'width': 0.25, 'height': 0.08, 'group': 3, 'text': 'Golgi'}])
    (pdf_build / 'present.jsonl').write_text(
        ''.join(json.dumps(r) + '\n' for r in (
            {'id': 'q1', 'question': '<b>What stores DNA?</b>', 'answer': 'The <i>nucleus</i>.'},
            {'id': 'q2', 'question': 'Where are ribosomes bound?', 'answer': 'Rough ER.'})),
        encoding='utf-8')
    return pdf_build, root / 'b_text'


def _write_drafts(build):
    target = json.loads((build / 'target.json').read_text(encoding='utf-8'))
    rows = []
    for i, (text, tier) in enumerate((('The <b>nucleus</b> stores {{c1::DNA}}', 1),
                                      ('Rough ER carries {{c1::ribosomes}}', 3)), 1):
        rows.append({'id': f'n{i:03d}', 'kind': 'cloze', 'notetype': target['note_type'],
                     'deck': target['deck'],
                     'fields': {'Text': text, 'Extra': '<div class="src">slide 1</div>'},
                     'tags': [target['source_tag'], target['tier_tags'][str(tier)]],
                     'tier': tier, 'objective': None, 'source_ref': [1], 'group': f'g{i:02d}',
                     'action': 'create', 'nid': None, 'status': 'draft'})
    (build / 'drafts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    (build / 'skipped.jsonl').write_text('', encoding='utf-8')
    return rows


# ----------------------------------------------------------------- commands

def _run(root, argv):
    env = dict(os.environ, PYTHONPATH=str(REPO / 'src'), PYTHONDONTWRITEBYTECODE='1')
    done = subprocess.run([sys.executable, '-m', 'cards', *map(str, argv)], cwd=root,
                          capture_output=True, text=True, env=env)
    return {'argv': ['cards', *[_mask(str(a), root) for a in argv]],
            'exit_code': done.returncode,
            'stdout': _mask(done.stdout, root),
            'stderr': _mask(done.stderr, root)}


def _commands(root, pdf, text):
    results = []

    def go(*argv):
        results.append(_run(root, argv))

    b = ['--build', pdf]
    go('extract', *b)
    go('extract', *b)
    go('extract', '--build', text)
    go('source', *b, '--slides', '1-2')
    go('source', *b, '--grep', 'nucleus')
    go('source', *b, '--page-image', 2)
    go('source', *b, '--figure', 'p02_f1')
    go('target', *b, '--existing-decks', pdf / 'decks.json', '--course', 'MED241',
       '--number', 6, '--title', 'Baseline Lecture')
    rows = _write_drafts(pdf)
    go('figures', *b, '--summary')
    go('figures', *b, '--fig', 'p02_f1', '--regions', 'regions.json', '--mode', 'one')
    go('check', *b)
    go('render', *b)
    go('render', *b, '--only', rows[0]['id'])
    go('render', *b, '--anki-html', 'present.jsonl')
    return results


def _snapshot_files(root, builds):
    from PIL import Image
    files, pngs = {}, {}
    for build in builds:
        for path in sorted(build.rglob('*')):
            if not path.is_file() or path.name in SKIP_NAMES:
                continue
            rel = path.relative_to(root).as_posix()
            if path.suffix in TEXT_SUFFIXES:
                files[rel] = normalize(path.name, path.read_text(encoding='utf-8'), root)
            elif path.suffix == '.png':
                with Image.open(path) as image:
                    pngs[rel] = f'{image.width}x{image.height}'
    return files, pngs


def build_snapshot():
    with tempfile.TemporaryDirectory(prefix='cli-baseline-') as tmp:
        root = Path(tmp).resolve()
        pdf, text = _make_inputs(root)
        commands = _commands(root, pdf, text)
        files, pngs = _snapshot_files(root, (pdf, text))
    return {'commands': commands, 'files': files, 'pngs': pngs}


def _entries(snapshot):
    entries = {}
    for i, command in enumerate(snapshot['commands'], 1):
        label = f"command {i:02d}: {' '.join(command['argv'][:2])}"
        entries[label] = json.dumps(command, indent=2, ensure_ascii=False) + '\n'
    for name, text in snapshot['files'].items():
        entries['file ' + name] = text
    for name, size in snapshot['pngs'].items():
        entries['png ' + name] = size + '\n'
    return entries


def _count(snapshot):
    return len(snapshot['files']) + len(snapshot['pngs'])


def record(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot()
    (directory / SNAPSHOT).write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"recorded {_count(snapshot)} files, {len(snapshot['commands'])} commands")
    return 0


def compare(directory):
    path = Path(directory) / SNAPSHOT
    if not path.is_file():
        print(f'no baseline at {path}; run record first')
        return 2
    old = _entries(json.loads(path.read_text(encoding='utf-8')))
    snapshot = build_snapshot()
    new = _entries(snapshot)
    differing = False
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        differing = True
        diff = difflib.unified_diff(
            (a or '').splitlines(keepends=True), (b or '').splitlines(keepends=True),
            fromfile=f'baseline/{key}' + ('' if a is not None else ' (missing)'),
            tofile=f'current/{key}' + ('' if b is not None else ' (missing)'))
        sys.stdout.write(''.join(diff))
        sys.stdout.write('\n')
    if differing:
        return 1
    print(f"IDENTICAL ({_count(snapshot)} files, {len(snapshot['commands'])} commands)")
    return 0


def main(argv):
    if len(argv) != 2 or argv[0] not in ('record', 'compare'):
        print(__doc__)
        return 2
    return (record if argv[0] == 'record' else compare)(argv[1])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
