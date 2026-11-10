"""Phase 2 behavioral contracts: all calls cross the real CLI boundary."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

L006 = 'MED241_L006_2026-09-13_endoplasmic-reticulum-mitochondria-and-golgi-apparatus.pdf'
L007 = 'MED241_L007_2026-09-14_anatomy-of-the-pectoral-region.pdf'

def cli(*args):
    return subprocess.run([sys.executable, '-m', 'cards', *map(str, args)],
                          capture_output=True, text=True)

def build_at(root, source):
    root.mkdir(parents=True, exist_ok=True)
    (root/'build.json').write_text(json.dumps({'source': {'path': str(source.resolve()),
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}, 'facts': {}}))
    return root

def load(build, name='slides'):
    return json.loads((build/'source'/f'{name}.json').read_text())

_lectures = {}
@pytest.fixture
def lecture(tmp_path_factory, private_fixture):
    path = private_fixture(L006)
    key = str(tmp_path_factory.getbasetemp())
    if key in _lectures:
        return _lectures[key]
    b = build_at(tmp_path_factory.mktemp('l006'), path)
    r = cli('extract', '--build', b)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    _lectures[key] = b
    return b

@pytest.fixture
def synthetic(tmp_path):
    import pymupdf as fitz
    from PIL import Image, ImageDraw
    import io
    doc = fitz.open()
    p = doc.new_page(width=600, height=400)
    p.insert_text((25,40), 'Cell biology', fontsize=24)
    # Interleave insertion order deliberately.
    p.insert_text((330,110), 'Right first')
    p.insert_text((30,110), 'Left first')
    p.insert_text((330,150), 'Right second')
    p.insert_text((30,150), 'Left second')
    p = doc.new_page(width=600, height=400)
    p.insert_text((25,40), 'Cell biology', fontsize=24)
    p.insert_text((25,90), 'More material here')
    p = doc.new_page(width=600, height=400)
    im = Image.new('RGB', (1200,800), 'white')
    ImageDraw.Draw(im).text((60,60), 'IMAGE ONLY SLIDE', fill='black', font_size=48)
    buffer = io.BytesIO()
    im.save(buffer, format='PNG')
    p.insert_image(p.rect, stream=buffer.getvalue())
    path = tmp_path/'MED241_L001_2026-01-01_cell-biology.pdf'
    doc.save(path)
    doc.close()
    b = build_at(tmp_path/'build', path)
    r = cli('extract', '--build', b)
    assert r.returncode in (0,1), r.stdout+r.stderr
    return b, path

def test_fr3_l006_slide_count(lecture):
    d = load(lecture)
    assert d['slide_count'] == 24
    assert [s['n'] for s in d['slides']] == list(range(1,25))

def test_fr3_reading_order_two_columns(synthetic):
    text = load(synthetic[0])['slides'][0]['text']
    assert text.index('Left first') < text.index('Left second') < text.index('Right first') < text.index('Right second')

def test_fr3_flags_image_only_and_repeated_title(synthetic):
    s = load(synthetic[0])['slides']
    assert 'repeated_title' in s[1]['flags']
    assert {'image_only','scan'} <= set(s[2]['flags'])
    assert 'IMAGE' in s[2]['title'].upper()
    assert s[2]['word_count'] > 0

def test_fr3_source_unchanged(synthetic):
    b,p = synthetic
    (b/'source/slides.json').unlink()
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    assert cli('extract', '--build', b).returncode in (0,1)
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before

def test_fr3_unreadable_source_exit2(tmp_path):
    b = build_at(tmp_path/'b', Path(__file__))
    (b/'build.json').write_text(json.dumps({'source': {'path': str(tmp_path/'missing.pdf')}}))
    r = cli('extract','--build',b)
    assert r.returncode == 2
    assert 'E2' in r.stdout and 'offline' in r.stdout

def test_fr3_objectives_never_invented(synthetic):
    assert load(synthetic[0], 'objectives')['objectives'] == []
    assert 'no_objectives' in load(synthetic[0], 'objectives')['flags']

def test_fr3_l006_objectives_found(lecture):
    items = load(lecture, 'objectives')['objectives']
    assert len(items) == 2
    assert [o['slide'] for o in items] == [2,2]
    assert 'Enumerate membranous' in items[0]['text']
    assert 'Describe LM & EM' in items[1]['text']
    assert 'body).' in items[1]['text']
    for item in items:
        assert 1 <= item['slide'] <= 24
        assert item['text'] in next(s['text'] for s in load(lecture)['slides'] if s['n']==item['slide'])

def test_fr4_map_one_line_per_slide(lecture):
    rows = [l for l in (lecture/'source/map.md').read_text().splitlines() if re.match(r'^\d+ \|',l)]
    assert len(rows) == 24
    assert [int(l.split(' |')[0]) for l in rows] == list(range(1,25))
    assert '# ' in (lecture/'source/map.md').read_text()
    assert all(len(l)<=110 for l in rows)

def test_fr4_l006_map_small(lecture):
    assert len((lecture/'source/map.md').read_text()) <= 10000

def test_fr5_slice_exact(lecture):
    r = cli('source','--build',lecture,'--slides','10-12')
    assert r.returncode == 0
    assert re.findall(r'^## Slide (\d+) ', r.stdout, re.M) == ['10','11','12']
    for slide in load(lecture)['slides']:
        if slide['n'] in (10,11,12):
            assert slide['text'] in r.stdout
        elif slide['n']==2:
            assert slide['text'] not in r.stdout

def test_fr5_out_of_range_exit2(lecture):
    r = cli('source','--build',lecture,'--slides','25')
    assert r.returncode == 2 and 'range' in r.stdout

def test_fr5_grep_slide_refs(lecture):
    r = cli('source','--build',lecture,'--grep','the')
    hits = r.stdout.splitlines()[1:]
    assert r.returncode == 0 and 0 < len(hits) <= 20
    assert all(re.match(r'Slide \d+:', l) for l in hits)

def test_fr5_all_l006_small(lecture):
    r = cli('source','--build',lecture,'--all')
    assert r.returncode == 0 and len(r.stdout) <= 24000
    assert len(re.findall(r'^## Slide ',r.stdout,re.M)) == 24

def test_fr5_page_image_small(lecture):
    from PIL import Image
    r = cli('source','--build',lecture,'--page-image','10')
    assert r.returncode == 0
    with Image.open(lecture/'source/pages/p10.png') as im:
        assert 0 < max(im.size) <= 1000

def test_fr6_cache_hit(lecture):
    p = lecture/'source/slides.json'
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    r = cli('extract','--build',lecture)
    assert r.returncode in (0,1) and 'cache' in r.stdout.lower()
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before

def test_fr7_text_source_sections(tmp_path):
    p = tmp_path/'notes.md'
    p.write_text('# First\nAlpha content\n\n# Second\nBeta content\n')
    b = build_at(tmp_path/'b',p)
    assert cli('extract','--build',b).returncode in (0,1)
    assert [(s['title'],s['text']) for s in load(b)['slides']] == [('First','Alpha content'),('Second','Beta content')]

@pytest.fixture(params=['extract','source','target'])
def command(request, tmp_path):
    p = tmp_path/'MED241_L003_topic.md'
    p.write_text('# A useful title\nA useful body\n')
    b = build_at(tmp_path/'b',p)
    cli('extract','--build',b)
    decks = b/'decks.json'
    decks.write_text('[]')
    args = [request.param,'--build',str(b)]
    if request.param == 'source': args += ['--all']
    if request.param == 'target': args += ['--existing-decks',str(decks)]
    return args,b,p

def test_g3_status_line_first(command):
    r = cli(*command[0])
    assert r.stdout.splitlines()[0] in ('OK','FINDINGS','ERROR')

def test_g3_stdout_budget(command):
    r = cli(*command[0])
    if command[0][0] != 'source':
        assert len(r.stdout) <= 2000 and len(r.stdout.splitlines()) <= 40

def test_g4_exit_codes_mapped(command):
    r = cli(*command[0])
    assert r.returncode in (0,1)
    assert r.stdout.startswith('OK\n' if r.returncode==0 else 'FINDINGS\n')
    bad = cli(*command[0], '--bogus')
    assert bad.returncode == 2 and bad.stdout.startswith('ERROR\n')

def test_g5_rerun_identical(command):
    args,b,_ = command
    cli(*args)
    files = [p for p in b.rglob('*') if p.is_file() and p.name!='log.jsonl']
    def normalized(p):
        return re.sub(r'("created": ")[^"]+',r'\1TIME',p.read_text())
    before = {p: normalized(p) for p in files}
    cli(*args)
    after_files = [p for p in b.rglob('*') if p.is_file() and p.name!='log.jsonl']
    assert before == {p: normalized(p) for p in after_files}

def test_g6_no_writes_outside_build(command):
    args,b,p = command
    if args[0]=='extract':
        import shutil
        shutil.rmtree(b/'source')
    p.chmod(0o444)
    def snapshot():
        return {str(f.relative_to(b.parent)):(f.read_bytes(),f.stat().st_mtime_ns)
                for f in b.parent.rglob('*') if f.is_file() and not f.is_relative_to(b)}
    before=snapshot()
    mode=b.parent.stat().st_mode & 0o777
    b.parent.chmod(0o555)
    try:
        r=cli(*args)
        assert r.returncode in (0,1)
        assert snapshot()==before
    finally:
        b.parent.chmod(mode)


def test_g7_provenance_present(command):
    args,b,_ = command
    cli(*args)
    names = {'extract':'source/slides.json','target':'target.json'}
    if args[0] in names:
        meta = json.loads((b/names[args[0]]).read_text())['_meta']
        assert meta['tool']=='cards '+args[0] and meta['version'] and meta['created']
        if args[0]=='extract':
            meta=json.loads((b/'source/objectives.json').read_text())['_meta']
            assert meta['tool']=='cards extract' and meta['version'] and meta['created']
            assert re.match(r'<!-- cards extract \S+ \S+ -->', (b/'source/map.md').read_text())
    else:
        r = cli('source','--build',b,'--slides','1')
        assert r.stdout.startswith('OK\n## Slide 1')

def test_g10_help_short(command):
    r = cli(command[0][0],'--help')
    assert r.returncode == 0 and len(r.stdout.splitlines()) <= 20

def test_g4_refused_before_extraction(tmp_path):
    b=build_at(tmp_path/'b',Path(__file__))
    for command in (['source','--all'], ['target','--existing-decks',str(b/'decks.json')]):
        r=cli(*command,'--build',b)
        assert r.returncode==3 and r.stdout.startswith('ERROR\n') and 'extract' in r.stdout

def test_fr3_first_extraction_preserves_source(tmp_path):
    p=tmp_path/'MED241_L001_topic.txt'
    p.write_text('Real lecture content')
    b=build_at(tmp_path/'build',p)
    before=(p.read_bytes(),p.stat().st_mtime_ns)
    assert cli('extract','--build',b).returncode in (0,1)
    assert before==(p.read_bytes(),p.stat().st_mtime_ns)
