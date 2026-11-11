import ast
from pathlib import Path
SRC = Path(__file__).resolve().parents[2]/'src/ankiplusmcp'

def test_no_private_imports_from_cards():
    for file in SRC.glob('*.py'):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or '').split('.')[0] == 'cards':
                assert not [a.name for a in node.names if a.name.startswith('_')], file.name

def test_no_faked_arguments_or_build_json():
    text = {f.name: f.read_text() for f in SRC.glob('*.py')}
    assert not any('build.json' in body for body in text.values())
    # measure_usage is the one remaining use; it leaves the MCP in 3b.
    assert sum(body.count('SimpleNamespace(') for body in text.values()) == 1
    assert 'SimpleNamespace(' in text['sources.py']
