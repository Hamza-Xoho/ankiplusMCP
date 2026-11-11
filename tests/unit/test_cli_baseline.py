import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('cli_baseline', Path(__file__).parents[1]/'tools/cli_baseline.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

def test_normalize_removes_run_to_run_noise(tmp_path):
    a = tool.normalize('x.json', '{"_meta": {"created": "2026-01-01T00:00:00Z"}, "path": "%s/b/source"}' % tmp_path, tmp_path)
    b = tool.normalize('x.json', '{"_meta": {"created": "2027-02-02T00:00:00Z"}, "path": "%s/b/source"}' % tmp_path, tmp_path)
    assert a == b and '<ROOT>' in a and '_meta' not in a
    assert tool.normalize('m.md', '<!-- cards extract 0.1.0 2026-01-01 -->\nbody\n', tmp_path) == 'body\n'
