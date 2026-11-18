"""Guard comparator sensitivity and real artifact capture, not model output."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

_spec = importlib.util.spec_from_file_location('public_baseline', Path(__file__).parents[1] / 'tools/cli_baseline.py')
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)


@pytest.mark.parametrize('before,after', [
    ('{"Text":"nucleus","tier":1}', '{"Text":"membrane","tier":1}'),
    ('{"tags":["source"],"tier":1}', '{"tags":["other"],"tier":1}'),
    ('{"tags":["source"],"tier":1}', '{"tags":["source"],"tier":3}'),
])
def test_public_baseline_detects_payload_change(tmp_path, monkeypatch, before, after):
    old = {'commands': [], 'files': {'drafts.jsonl': before}, 'pngs': {}}
    (tmp_path / tool.SNAPSHOT).write_text(json.dumps(old))
    new = copy.deepcopy(old)
    new['files']['drafts.jsonl'] = after
    monkeypatch.setattr(tool, 'build_snapshot', lambda: new)
    assert tool.compare(tmp_path) == 1


def test_snapshot_detects_changed_media_with_same_dimensions(tmp_path):
    build = tmp_path / 'build'
    build.mkdir()
    path = build / 'figure.png'
    Image.new('RGB', (20, 20), 'red').save(path)
    first = tool._snapshot_files(tmp_path, (build,))[1]
    Image.new('RGB', (20, 20), 'blue').save(path)
    second = tool._snapshot_files(tmp_path, (build,))[1]
    assert first != second, 'changed media bytes must not pass merely because dimensions match'


def test_deterministic_mode_routes_ocr_through_fixture(monkeypatch, tmp_path):
    seen = []
    def inspect_snapshot():
        import os
        import subprocess
        version = subprocess.check_output(['tesseract', '--version'], env=os.environ, text=True)
        seen.append(version)
        return {'commands': [], 'files': {}, 'pngs': {}}
    monkeypatch.setattr(tool, 'build_snapshot', inspect_snapshot)
    assert tool.main(['record', str(tmp_path), '--deterministic']) == 0
    assert seen == ['tesseract fixture-1\n']


def test_record_refuses_dependency_failure_as_golden(tmp_path, monkeypatch):
    snapshot = {'commands': [{'argv': ['cards', 'render'], 'exit_code': 2,
                             'stdout': 'ERROR\nChromium unavailable\n', 'stderr': ''}],
                'files': {}, 'pngs': {}}
    monkeypatch.setattr(tool, 'build_snapshot', lambda: snapshot)
    with pytest.raises(RuntimeError, match='render'):
        tool.record(tmp_path)
    assert not (tmp_path / tool.SNAPSHOT).exists()
