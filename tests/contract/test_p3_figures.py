"""Figure contracts exercise real CLI output and extracted L007 evidence."""
import json
import re
import subprocess
import sys

import pytest
from PIL import Image, ImageChops


def cli(*args):
    return subprocess.run([sys.executable, '-m', 'cards', *map(str, args)],
                          capture_output=True, text=True)


def records(build):
    return [row for line in (build/'drafts.jsonl').read_text().splitlines()
            if '_meta' not in (row := json.loads(line))]


@pytest.fixture
def real_figure(tmp_path, private_fixture):
    source = private_fixture('MED241_L007_2026-09-14_anatomy-of-the-pectoral-region.pdf')
    build = tmp_path/'build'
    build.mkdir()
    (build/'build.json').write_text(json.dumps({'source': {'path': str(source)}}))
    result = cli('extract', '--build', build, '--slides', '7')
    assert result.returncode in (0, 1), result.stdout + result.stderr
    slides = json.loads((build/'source/slides.json').read_text())
    figure = next(f for s in slides['slides'] for f in s['figures'] if f['ocr_labels'])
    (build/'target.json').write_text(json.dumps({
        'deck': 'Pectoral region', 'number': 7, 'course': 'MED241',
        'note_type': 'ColdRecall Cloze',
        'source_tag': '#ColdRecall::#Source::MED241::L007_Pectoral_region',
        'tier_tags': {'1': '#ColdRecall::!Tier::1'},
        'base_tags': ['#ColdRecall::#Source::MED241::L007_Pectoral_region'],
    }))
    return build, figure


def test_fr10_occlusion_record_d6(real_figure):
    # Missing D-6 fields, broken media links, or a duplicated draft must fail.
    build, figure = real_figure
    original = (build/'source'/figure['file']).read_bytes()
    result = cli('figures', '--build', build, '--fig', figure['fig_id'])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith('OK\n')
    assert len(result.stdout) <= 2000 and len(result.stdout.splitlines()) <= 40
    notes = records(build)
    assert len(notes) == 1
    note = notes[0]
    assert re.fullmatch(r'n\d{3,}', note['id'])
    assert {'id', 'kind', 'notetype', 'deck', 'fields', 'tags', 'tier',
            'objective', 'source_ref', 'group', 'action', 'nid', 'status',
            'media', 'preview'} <= note.keys()
    assert note['kind'] == 'io' and note['notetype'] == 'Image Occlusion'
    assert note['source_ref'] == [7] and note['tier'] == 1
    assert note['action'] == 'create' and note['nid'] is None and note['status'] == 'draft'
    assert note['deck'] == 'Pectoral region'
    assert '#ColdRecall::!Tier::1' in note['tags']
    assert note['fields']['Image'] == f'<img src="{note["media"][0]["filename"]}">'
    assert 'image-occlusion:rect:' in note['fields']['Occlusion']
    assert ':oi=1}}' in note['fields']['Occlusion']
    for path in (note['media'][0]['path'], note['preview']):
        artifact = build/path
        assert artifact.is_file() and artifact.resolve().is_relative_to(build.resolve())
    with Image.open(build/note['preview']) as preview, Image.open(build/'source'/figure['file']) as image:
        assert preview.size == image.size
        assert ImageChops.difference(preview.convert('RGB'), image.convert('RGB')).getbbox()
    assert (build/'source'/figure['file']).read_bytes() == original
    assert json.loads((build/'drafts.jsonl').read_text().splitlines()[0])['_meta']['tool'] == 'cards figures'
    checked = cli('check', '--build', build)
    assert checked.returncode in (0, 1), checked.stdout + checked.stderr
    findings = json.loads((build/'checks/check.json').read_text())['findings']
    assert not [f for f in findings if f['code'].startswith('S')], findings
    assert cli('figures', '--build', build, '--fig', figure['fig_id']).returncode == 0
    assert records(build) == notes


def test_fr10_repeated_labels_share_index(real_figure):
    # Dropping shared groups or leaving index gaps after --keep must fail.
    build, figure = real_figure
    regions = [dict(figure['ocr_labels'][0], group=4),
               dict(figure['ocr_labels'][1], group=9),
               dict(figure['ocr_labels'][0], group=4, top=.7)]
    (build/'regions.json').write_text(json.dumps({'regions': regions}))
    result = cli('figures', '--build', build, '--fig', figure['fig_id'],
                 '--regions', 'regions.json', '--keep', '4', '--mode', 'all')
    assert result.returncode == 0, result.stdout + result.stderr
    masks = records(build)[0]['fields']['Occlusion']
    assert re.findall(r'\{\{c(\d+)::', masks) == ['1', '1']
    assert masks.count(':oi=0}}') == 2
    for name, value in re.findall(r'(left|top|width|height)=([.\d]+)', masks):
        assert 0 <= float(value) <= 1, name
