from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('cv', ROOT/'scripts/check_versions.py')
cv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cv)


def test_repo_versions_agree():
    v = cv.versions(ROOT)
    assert v['package.json'] == v['pyproject.toml'] == '0.2.0'


def test_mismatch_is_reported(tmp_path):
    (tmp_path/'package.json').write_text(json.dumps({'version': '1.0.0'}))
    (tmp_path/'pyproject.toml').write_text('[project]\nversion = "1.0.1"\n')
    assert len(set(cv.versions(tmp_path).values())) == 2
    assert cv.main(tmp_path) == 1
