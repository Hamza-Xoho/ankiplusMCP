import importlib.metadata
import tomllib
from pathlib import Path
from ankiplusmcp.service import Service
from ankiplusmcp.server import API

ROOT = Path(__file__).parents[2]


def test_version_comes_from_metadata(tmp_path):
    s = Service(tmp_path, [tmp_path])
    try:
        assert API(s).capabilities()['version'] == importlib.metadata.version('ankiplusmcp') == '0.3.0'
    finally:
        s.close()


def test_pins_and_extras():
    project = tomllib.loads((ROOT/'pyproject.toml').read_text())['project']
    assert not any('==' in d for d in project['dependencies'])
    assert {'ocr', 'render', 'all', 'dev'} <= set(project['optional-dependencies'])
    names = ' '.join(project['dependencies']).lower()
    assert 'playwright' not in names and 'pytesseract' not in names
    assert 'platformdirs' in names and 'filelock' in names
