"""Supplemental blind-exposure packet mechanics, never a reviewer execution claim."""
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('staged_student', ROOT / 'scripts/staged-student.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fixture(tmp_path):
    source = tmp_path / 'original'
    source.mkdir()
    (source / 'sheets').mkdir()
    for side in ('fronts', 'backs'):
        Image.new('RGB', (10, 10), 'white' if side == 'fronts' else 'black').save(source / 'sheets' / f'{side}.png')
    (source / 'sheets.json').write_text(json.dumps({'sheets': [{'notes': ['n001', 'n002'],
        'fronts': 'sheets/fronts.png', 'backs': 'sheets/backs.png'}], 'previews': []}))
    for name in ('brief.md', 'rubric.md', 'report-format.md'):
        (source / name).write_bytes((ROOT / 'src/cards/templates/review/student' / name).read_bytes())
    (source / 'EXPECTATIONS.md').write_text('SECRET ANSWER KEY')
    return source


def test_packet_exposes_only_fronts_before_committed_attempts(tmp_path):
    m = module()
    source = fixture(tmp_path)
    result = m.prepare(source, tmp_path / 'experiment')
    packet = Path(result['packet'])
    manifest = json.loads((packet / 'fronts.json').read_text())
    assert manifest['tile_ids'] == ['n001_c1', 'n002_c1']
    assert (packet / manifest['image']).read_bytes() == (source / 'sheets/fronts.png').read_bytes()
    assert not (packet / 'backs.png').exists()
    assert not (packet / 'sheets.json').exists()
    assert not (packet / 'EXPECTATIONS.md').exists()
    assert result['reviewer_execution'] == 'not_run'
    assert result['continuation_support'] == 'not_verified'
    for name in ('brief.md', 'rubric.md', 'report-format.md'):
        assert (packet / name).read_bytes() == (source / name).read_bytes()
    with pytest.raises(FileExistsError):
        m.prepare(source, tmp_path / 'experiment')


@pytest.mark.parametrize('attempts', [{}, {'n001_c1': 'alpha'},
    {'n001_c1': 'alpha', 'n002_c1': ''}, {'n001_c1': 'alpha', 'n002_c1': 'beta', 'extra': 'x'}])
def test_release_refuses_incomplete_answers_without_exposing_backs(tmp_path, attempts):
    m = module()
    packet = Path(m.prepare(fixture(tmp_path), tmp_path / 'experiment')['packet'])
    (packet / 'front-attempts.json').write_text(json.dumps(attempts))
    with pytest.raises(ValueError):
        m.release(packet.parent)
    assert not (packet / 'backs.png').exists()


def test_release_durably_commits_exact_answers_before_backs_and_detects_rewrites(tmp_path):
    m = module()
    experiment = tmp_path / 'experiment'
    packet = Path(m.prepare(fixture(tmp_path), experiment)['packet'])
    attempts = b'{"n001_c1":"alpha", "n002_c1":"don\u0027t know"}\n'
    (packet / 'front-attempts.json').write_bytes(attempts)
    receipt = m.release(experiment)
    assert (experiment / 'supervisor/committed-attempts.json').read_bytes() == attempts
    assert (packet / 'backs.png').is_file()
    assert m.release(experiment) == receipt
    (packet / 'front-attempts.json').write_text('{"n001_c1":"changed", "n002_c1":"beta"}')
    with pytest.raises(ValueError, match='changed'):
        m.release(experiment)


def test_release_refuses_tampered_front_or_back_bytes(tmp_path):
    m = module()
    experiment = tmp_path / 'experiment'
    packet = Path(m.prepare(fixture(tmp_path), experiment)['packet'])
    (packet / 'front-attempts.json').write_text('{"n001_c1":"a", "n002_c1":"b"}')
    (packet / 'fronts.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        m.release(experiment)
    assert not (packet / 'backs.png').exists()


def test_prepare_refuses_symlink_images_and_nonfixture_inputs(tmp_path):
    m = module()
    source = fixture(tmp_path)
    front = source / 'sheets/fronts.png'
    front.unlink()
    front.symlink_to(source / 'sheets/backs.png')
    with pytest.raises(ValueError):
        m.prepare(source, tmp_path / 'experiment')
