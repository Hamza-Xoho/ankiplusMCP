import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from cards.common.errors import CardsError
from cards.common.files import write_json, write_jsonl, write_text, read_json, read_jsonl
from cards.common.paths import Build
from cards.common.size import tokens


def test_provenance_roundtrip(tmp_path):
    write_json(tmp_path/'x.json', {'value': 'α<sub>2</sub>'}, 'cards state')
    assert read_json(tmp_path/'x.json')['value'] == 'α<sub>2</sub>'
    write_jsonl(tmp_path/'x.jsonl', [{'value': 'β'}], 'cards state')
    assert list(read_jsonl(tmp_path/'x.jsonl')) == [{'value': 'β'}]
    write_text(tmp_path/'x.md', '# α', 'cards state')
    assert (tmp_path/'x.md').read_text().startswith('<!-- cards state 0.1.0 ')
    assert tokens('α'*5) == 2 and tokens('') == 0


def test_state_init_refuses_merged_source(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path/'MED241_L029-L044_action-potentials.txt'
    source.write_text('lecture')
    env = dict(os.environ, PYTHONPATH=str(root/'src'))
    result = subprocess.run([sys.executable, '-m', 'cards', 'state', 'init', str(source)],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'one lecture' in result.stdout
    assert not (tmp_path/'builds').exists()

def test_state_init_honours_explicit_builds_root(tmp_path):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path/'MED241_L006_test.txt'
    source.write_text('lecture')
    store = tmp_path/'store'
    env = dict(os.environ, CARDS_BUILDS=str(store), PYTHONPATH=str(root/'src'))
    result = subprocess.run([sys.executable, '-m', 'cards', 'state', 'init', str(source)],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (store/'.current').is_file() and list(store.glob('*/build.json'))
    assert not (tmp_path/'builds').exists()

def test_build_blocks_traversal_and_symlink(tmp_path):
    root = tmp_path/'build'
    root.mkdir()
    (root/'escape').symlink_to(tmp_path, target_is_directory=True)
    for name in ['../outside', 'escape/outside', str(tmp_path/'outside')]:
        with pytest.raises(CardsError):
            Build(root).path(name)
