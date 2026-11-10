"""Failure and preservation behavior for image occlusion authoring."""
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from cards.common.errors import CardsError, Refused


@pytest.fixture
def figure_build(tmp_path):
    source = tmp_path/'source/figures'
    source.mkdir(parents=True)
    Image.new('RGB', (200, 100), 'white').save(source/'p01_f1.png')
    labels = [dict(text='Label', left=.1, top=.1, width=.2, height=.1),
              dict(text='label.', left=.5, top=.5, width=.2, height=.1)]
    (tmp_path/'source/slides.json').write_text(json.dumps({'slides': [dict(
        n=1, title='Diagram', text='Figure source', figures=[dict(
            fig_id='p01_f1', file='figures/p01_f1.png', ocr_labels=labels)])]}))
    (tmp_path/'target.json').write_text(json.dumps(dict(deck='Diagram', number=1,
        source_tag='#ColdRecall::#Source::TEST::L001',
        tier_tags={'1': '#ColdRecall::!Tier::1'}, base_tags=[])))
    return tmp_path


def run(build, **kwargs):
    from cards.figures import run as figures
    return figures(SimpleNamespace(build=build, fig='p01_f1', regions=None,
                                   keep=None, mode='one', **kwargs))


def test_repeated_text_without_explicit_group(figure_build):
    run(figure_build)
    note = json.loads((figure_build/'drafts.jsonl').read_text().splitlines()[1])
    assert note['fields']['Occlusion'].count('{{c1::') == 2
    assert '{{c2::' not in note['fields']['Occlusion']


@pytest.mark.parametrize('region', [None, {}, {'left': float('nan')},
    dict(left=-.1, top=.1, width=.2, height=.1),
    dict(left=.1, top=.1, width=0, height=.1),
    dict(left=.9, top=.1, width=.2, height=.1)])
def test_invalid_regions_do_not_write_drafts(figure_build, region):
    from cards.figures import run as figures
    (figure_build/'regions.json').write_text(json.dumps({'regions': [region]}))
    with pytest.raises(CardsError):
        figures(SimpleNamespace(build=figure_build, fig='p01_f1',
                regions='regions.json', keep=None, mode='one'))
    assert not (figure_build/'drafts.jsonl').exists()


def test_empty_labels_asks_for_estimated_rectangles(figure_build):
    path = figure_build/'source/slides.json'
    data = json.loads(path.read_text())
    data['slides'][0]['figures'][0]['ocr_labels'] = []
    path.write_text(json.dumps(data))
    result = run(figure_build)
    assert result.status == 'FINDINGS' and result.exit_code == 1
    assert 'estimate' in ' '.join(result.lines).lower()
    assert not (figure_build/'drafts.jsonl').exists()


def summaries(build):
    from types import SimpleNamespace
    from cards.figures import run as figures
    return figures(SimpleNamespace(build=build, summary=True))


def test_summary_lists_labels_without_images(figure_build):
    (figure_build / 'target.json').unlink()
    result = summaries(figure_build)
    text = '\n'.join(result.lines)
    assert result.status == 'OK' and 'p01_f1' in text and 'Label' in text
    markdown = (figure_build / 'source/figures_summary.md').read_text()
    assert '## p01_f1' in markdown and 'labels:' in markdown
    assert not (figure_build / 'source/figures/p01_f1_io.png').exists()
    from cards.common.output import render
    output = render(result)
    assert len(output) <= 2000 and len(output.splitlines()) <= 40


def test_summary_marks_existing_occlusion(figure_build):
    run(figure_build)
    assert 'draft n001' in '\n'.join(summaries(figure_build).lines)


def test_existing_edited_draft_is_preserved(figure_build):
    run(figure_build)
    path = figure_build/'drafts.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1]['status'] = 'dropped'
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    before = path.read_bytes()
    with pytest.raises(Refused):
        run(figure_build)
    assert path.read_bytes() == before


def test_existing_unknown_preview_is_preserved(figure_build):
    # A figure command must not replace an unrelated file at its output path.
    output = figure_build/'source/figures/p01_f1_io_preview.png'
    output.write_bytes(b'keep this file')
    with pytest.raises(Refused):
        run(figure_build)
    assert output.read_bytes() == b'keep this file'


def test_malformed_output_provenance_does_not_crash(figure_build):
    output = figure_build/'source/figures/p01_f1_io_preview.png'
    output.write_bytes(b'keep this file')
    output.with_suffix('.png.json').write_text('{"_meta": []}')
    with pytest.raises(CardsError):
        run(figure_build)
    assert output.read_bytes() == b'keep this file'


def test_media_name_matches_anki_normalization(figure_build):
    run(figure_build)
    note = json.loads((figure_build/'drafts.jsonl').read_text().splitlines()[1])
    assert note['media'][0]['filename'] == 'l001_p01_f1.png'
    assert note['fields']['Image'] == '<img src="l001_p01_f1.png">'
