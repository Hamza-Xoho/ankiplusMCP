"""Renderer contracts exercise real CLI and Chromium screenshots."""
import json
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p3_helpers import convert_v1


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'cards', *map(str, args)], capture_output=True, text=True)


def write_notes(build, notes):
    build.mkdir(parents=True, exist_ok=True)
    (build/'drafts.jsonl').write_text(''.join(json.dumps(n)+'\n' for n in notes))
    return build


@pytest.fixture
def l006(tmp_path, private_fixture):
    notes = convert_v1(private_fixture('l006_v1_drafts.jsonl'))
    assert len(notes) == 40
    return write_notes(tmp_path/'build', notes)


def manifest(build):
    return json.loads((build/'renders/sheets.json').read_text())


def test_fr12_l006_sheet_pairs(l006):
    result = cli('render', '--build', l006)
    assert result.returncode == 0, result.stdout + result.stderr
    data = manifest(l006)
    assert data['_meta']['tool'] == 'cards render'
    assert len(data['sheets']) == 5
    assert [s['notes'] for s in data['sheets']] == [[f'n{n:03}' for n in range(i, i+8)] for i in range(1, 41, 8)]
    assert len(list((l006/'renders/sheets').glob('*_fronts.png'))) == 5
    assert len(list((l006/'renders/sheets').glob('*_backs.png'))) == 5
    assert len(list((l006/'renders/cards').glob('*_back.png'))) == 40
    for png in (l006/'renders/cards').glob('*.png'):
        with Image.open(png) as image:
            assert image.width == 390 and image.height > 40
    # Repeating the command preserves all image bytes and manifest apart from provenance.
    before = {p.relative_to(l006): p.read_bytes() for p in (l006/'renders').rglob('*.png')}
    assert cli('render', '--build', l006).returncode == 0
    assert before == {p.relative_to(l006): p.read_bytes() for p in (l006/'renders').rglob('*.png')}
    assert manifest(l006)['sheets'] == data['sheets']


def test_fr12_only_rerenders_listed(l006):
    assert cli('render', '--build', l006).returncode == 0
    before = {p.relative_to(l006): (p.read_bytes(), p.stat().st_mtime_ns) for p in (l006/'renders').rglob('*.png')}
    old = manifest(l006)['sheets']
    result = cli('render', '--build', l006, '--only', 'n007,n015')
    assert result.returncode == 0, result.stdout + result.stderr
    assert manifest(l006)['sheets'] == old
    for relative, (content, modified) in before.items():
        path = l006/relative
        if path.parent.name == 'cards':
            selected = path.name.startswith(('n007_', 'n015_'))
        else:
            selected = path.name.startswith(('sheet_01_', 'sheet_02_'))
        assert (path.stat().st_mtime_ns > modified) == selected, relative
        assert path.read_bytes() == content


def test_fr12_scripts_stripped(l006):
    notes = [json.loads(line) for line in (l006/'drafts.jsonl').read_text().splitlines()]
    notes = notes[:1]
    notes[0]['fields']['Extra'] += '<script>document.body.textContent="EXECUTED"</script><img src="https://invalid.example/a.png" onerror="alert(1)">'
    write_notes(l006, notes)
    model = l006/'model'
    model.mkdir()
    assets = Path('.claude/skills/anki/assets/coldrecall-cloze')
    for name in ('front.html', 'back.html', 'style.css'):
        (model/name).write_bytes((assets/name).read_bytes())
    with (model/'front.html').open('a') as stream:
        stream.write('<script src="https://invalid.example/script.js"></script>')
    result = cli('render', '--build', l006)
    assert result.returncode == 0, result.stdout + result.stderr
    html_files = list((l006/'renders/cards').glob('*.html'))
    assert html_files
    for path in html_files:
        output = path.read_text().lower()
        assert '<script' not in output and 'onerror=' not in output
        assert 'https://invalid.example' not in output and 'executed' not in output
        assert 'night_mode' in output


def test_fr12_default_model_from_assets(l006):
    notes = [json.loads(line) for line in (l006/'drafts.jsonl').read_text().splitlines()][:1]
    write_notes(l006, notes)
    assert not (l006/'model').exists()
    result = cli('render', '--build', l006)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'assets' in result.stdout.lower() and 'model' in result.stdout.lower()
    for name in ('front.html', 'back.html', 'style.css'):
        assert (Path('.claude/skills/anki2/assets/coldrecall-cloze')/name).read_bytes() == (Path('.claude/skills/anki/assets/coldrecall-cloze')/name).read_bytes()
    html = (l006/'renders/cards/n001_back.html').read_text()
    assert '<div id="extra">' in html and '<span class="cloze"' in html
    assert Path('.claude/skills/anki/assets/coldrecall-cloze/style.css').read_text() in html


@pytest.mark.parametrize('attack', ['../escape', '/tmp/escape'])
def test_fr12_note_paths_contained(l006, attack):
    notes = [json.loads(line) for line in (l006/'drafts.jsonl').read_text().splitlines()][:1]
    notes[0]['id'] = attack
    write_notes(l006, notes)
    result = cli('render', '--build', l006)
    assert result.returncode == 2 and result.stdout.startswith('ERROR\n')
    assert not (l006/'escape_back.png').exists()


def test_fr12_anki_html_and_media_contained(tmp_path):
    build = tmp_path/'build'
    build.mkdir()
    (build/'present.jsonl').write_text(json.dumps({'id':'post1','question':'<b>Question</b><script>alert(1)</script>', 'answer':'Answer'})+'\n')
    result = cli('render','--build',build,'--anki-html',build/'present.jsonl')
    assert result.returncode == 0, result.stdout+result.stderr
    assert (build/'renders/cards/post1_front.png').exists()
    assert '<script' not in (build/'renders/cards/post1_front.html').read_text()
    (build/'present.jsonl').write_text(json.dumps({'id':'post1','question':'<img src="../private.png">','answer':'Answer'})+'\n')
    result = cli('render','--build',build,'--anki-html',build/'present.jsonl')
    assert result.returncode == 2 and 'escapes build' in result.stdout


def test_fr12_io_masks_render_over_image(tmp_path):
    build = tmp_path/'build'
    build.mkdir()
    image = build/'figure.png'
    Image.new('RGB', (300, 150), 'white').save(image)
    write_notes(build, [{'id':'n001','kind':'io','notetype':'Image Occlusion',
        'fields':{'Image':'<img src="figure.png">','Header':'', 'Back Extra':'',
                  'Occlusion':'{{c1::image-occlusion:rect:left=.1:top=.1:width=.2:height=.2:oi=1}}<br>'
                              '{{c2::image-occlusion:rect:left=.6:top=.1:width=.2:height=.2:oi=1}}'},
        'media':[{'path':'figure.png','filename':'figure.png'}]}])
    result = cli('render','--build',build)
    assert result.returncode == 0, result.stdout+result.stderr
    assert len(list((build/'renders/cards').glob('*_front.png'))) == 2
    with Image.open(build/'renders/cards/n001_c1_front.png') as front, Image.open(build/'renders/cards/n001_back.png') as back:
        # The covered image differs from the fully revealed image.
        from PIL import ImageChops
        assert front.size == back.size
        assert ImageChops.difference(front.convert('RGB'), back.convert('RGB')).getbbox()
    output = (build/'renders/cards/n001_c1_front.html').read_text()
    assert 'data:image/png;base64,' in output
    assert 'image-occlusion:rect:' not in output
    assert 'data-ordinal="1"' in output


@pytest.mark.parametrize('bad', [None, [], 'invalid'])
def test_fr12_malformed_record_is_located_error(tmp_path, bad):
    build = write_notes(tmp_path/'build', [bad])
    result = cli('render','--build',build)
    assert result.returncode == 2 and result.stdout.startswith('ERROR\n')
    assert 'drafts.jsonl' in result.stdout and 'line 1' in result.stdout and 'field' in result.stdout
    assert not result.stderr


def test_fr12_basic_requires_matching_template(tmp_path):
    build = write_notes(tmp_path/'build', [{'id':'n001','kind':'basic','notetype':'Basic',
                                          'fields':{'Front':'Question','Back':'Answer'}}])
    result = cli('render','--build',build)
    assert result.returncode == 2 and 'model' in result.stdout.lower()
    model = build/'model'
    model.mkdir()
    (model/'front.html').write_text('{{Front}}')
    (model/'back.html').write_text('{{FrontSide}}<hr>{{Back}}')
    (model/'style.css').write_text('body { background: #333B45; color: white; }')
    result = cli('render','--build',build)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'Question' in (build/'renders/cards/n001_c1_front.html').read_text()
    assert 'Answer' in (build/'renders/cards/n001_back.html').read_text()


def test_fr12_changed_cloze_removes_stale_selected_front(l006):
    notes = [json.loads(line) for line in (l006/'drafts.jsonl').read_text().splitlines()][:2]
    write_notes(l006, notes)
    assert cli('render','--build',l006).returncode == 0
    assert (l006/'renders/cards/n001_c2_front.png').is_file()
    untouched = l006/'renders/cards/n002_c1_front.png'
    before = (untouched.read_bytes(), untouched.stat().st_mtime_ns)
    # Keep fixture prose verbatim; un-cloze one answer to simulate a round-2 edit.
    notes[0]['fields']['Text'] = notes[0]['fields']['Text'].replace('{{c2::outer nuclear membrane}}', 'outer nuclear membrane')
    write_notes(l006, notes)
    assert cli('render','--build',l006,'--only','n001').returncode == 0
    assert not (l006/'renders/cards/n001_c2_front.png').exists()
    assert not (l006/'renders/cards/n001_c2_front.html').exists()
    assert (untouched.read_bytes(), untouched.stat().st_mtime_ns) == before


def test_fr12_per_sheet_rebuild_removes_old_pairs(l006):
    notes = [json.loads(line) for line in (l006/'drafts.jsonl').read_text().splitlines()][:2]
    write_notes(l006, notes)
    assert cli('render','--build',l006,'--per-sheet','1').returncode == 0
    assert len(manifest(l006)['sheets']) == 2
    assert cli('render','--build',l006,'--per-sheet','2').returncode == 0
    assert len(manifest(l006)['sheets']) == 1
    assert len(list((l006/'renders/sheets').glob('*.png'))) == 2
