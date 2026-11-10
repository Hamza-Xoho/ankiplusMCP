from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('check_privacy', Path(__file__).parents[2]/'scripts/check_privacy.py')
cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)


def write(tmp_path, text):
    p = tmp_path/'f.md'; p.write_text(text); return [p]


def test_flags_named_home_paths_and_emails(tmp_path):
    assert cp.find_leaks(write(tmp_path, 'see /home/alice/projects/x'))
    assert cp.find_leaks(write(tmp_path, 'see /Users/bob/Code/x'))
    assert cp.find_leaks(write(tmp_path, 'mail carol@example.org'))


def test_allows_placeholders_and_decorators(tmp_path):
    ok = '/Users/<name>/x /home/<name>/x /home/user/x /absolute/path\n+@pytest.mark.skip\nnoreply@anthropic.com'
    assert cp.find_leaks(write(tmp_path, ok)) == []
