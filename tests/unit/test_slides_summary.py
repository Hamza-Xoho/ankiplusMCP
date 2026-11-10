"""Extraction must pre-digest slides so a drafter cannot miss a plain fact."""
from pathlib import Path
from types import SimpleNamespace

from cards import extract, state
from cards.common.files import read_json
from cards.common.paths import Build
from cards.extract import summary

SOURCE = """Muscles of the Arm

Objectives
1. Identify muscles within anterior and posterior compartments
2. Describe muscle attachments, nerve supply, and actions

Biceps Brachii
Long head originates from the supraglenoid tubercle
Short head originates from the coracoid process
Insertion: radial tuberosity
Innervated by musculocutaneous nerve (C5-C6)
Action: flexes the elbow and supinates the forearm

The biceps brachii is a two-headed muscle of the anterior compartment.
"""


def extracted(tmp_path, monkeypatch):
    monkeypatch.setenv('CARDS_BUILDS', str(tmp_path / 'builds'))
    source = tmp_path / 'MED241_L015_arm.txt'
    source.write_text(SOURCE)
    made = state.init(SimpleNamespace(source=str(source), job='build'))
    build = Build(Path(made.files[0]).parent)
    extract.run(SimpleNamespace(build=str(build.root), slides=None))
    return build


def test_summary_and_cache(tmp_path, monkeypatch):
    build = extracted(tmp_path, monkeypatch)
    data = read_json(build.path('source/slides_summary.json'))
    assert data['lecture'] == 'MED241-L015' and data['title'] == 'Muscles of the Arm'
    assert [item['id'] for item in data['objectives']] == ['ILO1', 'ILO2']
    assert all(isinstance(slide['page'], int) for slide in data['slides'])
    facts = [fact for slide in data['slides'] for fact in slide['key_facts']]
    texts = [fact['text'] for fact in facts]
    assert 'Long head originates from the supraglenoid tubercle' in texts
    assert 'Innervated by musculocutaneous nerve (C5-C6)' in texts
    origin = next(fact for fact in facts if fact['text'].startswith('Long head'))
    assert origin['type'] == 'origin' and origin['tier'] == 1 and origin['group']
    assert 'Muscles of the Arm' not in texts  # the title is not a fact
    assert extract.run(SimpleNamespace(build=str(build.root), slides=None)).lines[0].startswith('cache hit')


def test_summary_is_regenerated_when_missing(tmp_path, monkeypatch):
    build = extracted(tmp_path, monkeypatch)
    build.path('source/slides_summary.json').unlink()
    result = extract.run(SimpleNamespace(build=str(build.root), slides=None))
    assert not result.lines[0].startswith('cache hit')
    assert build.path('source/slides_summary.json').is_file()


def test_figure_labels_are_digested_without_images():
    slide = {'n': 5, 'title': 'Biceps Brachii', 'text': '', 'word_count': 0, 'flags': [],
             'figures': [{'fig_id': 'p05_f1', 'file': 'figures/p05_f1.png',
                          'ocr_labels': [{'text': text} for text in
                                         ['Biceps brachii', 'Musculocutaneous nerve', 'Median nerve',
                                          'Brachialis', 'Brachial artery', 'Biceps brachii']]}]}
    data = summary.build('MED241-L015', [slide], [])
    figure = data['slides'][0]['figures'][0]
    assert figure['id'] == 'p05_f1' and figure['label_count'] == 5
    assert figure['type'] == 'anatomy_diagram'
    assert figure['label_summary'].startswith('Biceps brachii, Musculocutaneous nerve')