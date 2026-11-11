import json
import subprocess
import sys
import pytest
from ankiplusmcp import doctor
from ankiplusmcp.store import DomainError
from ankiplusmcp.service import Service

RUN = [sys.executable, '-m', 'ankiplusmcp']


def test_version_line():
    out = subprocess.run(RUN + ['--version'], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == 'ankiplusmcp 0.3.0'


def test_doctor_json_shape_and_exit_codes(tmp_path):
    out = subprocess.run(RUN + ['doctor', '--json', '--workspace-root', str(tmp_path)], capture_output=True, text=True)
    data = json.loads(out.stdout)
    assert {'ok', 'version', 'checks'} <= set(data)
    assert {c['name'] for c in data['checks']} >= {'python', 'mcp', 'pymupdf', 'pillow', 'workspace_root', 'tesseract', 'chromium'}
    assert all({'name', 'status', 'required', 'detail', 'fix'} <= set(c) for c in data['checks'])
    assert out.returncode in (0, 1) and data['ok'] is True


def test_doctor_exit_codes_follow_required_and_optional(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    assert doctor.doctor_main(['--workspace-root', str(tmp_path)]) == 1
    assert 'brew install tesseract' in capsys.readouterr().out
    blocked = tmp_path/'file'; blocked.write_text('x')
    assert doctor.doctor_main(['--workspace-root', str(blocked/'under-a-file')]) == 2


def test_missing_tools_are_dependency_errors_with_fixes(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: None)
    s = Service(tmp_path, [tmp_path])
    try:
        w = s.store.create('cards')['id']
        with pytest.raises(DomainError) as e: s.ocr_image(w, 'media/none.png')
        assert e.value.code == 'DEPENDENCY' and 'tesseract' in e.value.remedy.lower()
        s.save_cards(w, [{'id': 'a', 'fields': {'Text': '{{c1::y}}'}}], 0)
        with pytest.raises(DomainError) as e: s.render_cards(w)
        assert e.value.code == 'DEPENDENCY' and 'setup' in e.value.remedy
    finally: s.close()


def test_setup_without_tty_or_yes_exits_3():
    out = subprocess.run(RUN + ['setup'], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert out.returncode == 3 and '--yes' in out.stderr and out.stdout == ''


@pytest.mark.parametrize('bundled,chrome,configured,expected', [
    (True,  True,  'auto',     'chromium'),
    (False, True,  'auto',     'chrome'),
    (False, False, 'auto',     None),
    (True,  False, 'chrome',   None),
    (False, True,  'chromium', None),
])
def test_resolve_browser(monkeypatch, bundled, chrome, configured, expected):
    monkeypatch.setattr(doctor, 'have', lambda name: bundled if name == 'chromium' else True)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome' if chrome else None)
    assert doctor.resolve_browser(configured) == expected


def test_resolve_browser_path(monkeypatch, tmp_path):
    exe = tmp_path/'chrome'; exe.write_text('')
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: None)
    assert doctor.resolve_browser(str(exe)) == str(exe)
    assert doctor.resolve_browser(str(tmp_path/'gone')) is None


def test_missing_browser_is_a_dependency_error(monkeypatch):
    monkeypatch.setattr(doctor, 'have', lambda name: False)
    monkeypatch.setattr(doctor, 'system_chrome', lambda: None)
    with pytest.raises(DomainError) as caught: doctor.require_browser('chrome')
    assert caught.value.code == 'DEPENDENCY' and 'Chrome' in caught.value.message and 'setup' in caught.value.remedy


def test_doctor_and_setup_accept_system_chrome(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(doctor, 'have', lambda name: name == 'tesseract')
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome')
    check = next(c for c in doctor.run_checks(tmp_path) if c['name'] == 'chromium')
    assert check['status'] == 'ok' and 'system Chrome' in check['detail']
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('setup must not download'))
    assert doctor.setup_main(['--yes', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['browser'] == 'chrome'


def _config(tmp_path, text):
    path = tmp_path/'config.toml'; path.write_text(text)
    return str(path)


def test_setup_uses_the_configured_browser(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv('ANKIPLUS_CONFIG', raising=False)
    monkeypatch.setattr(doctor, 'have', lambda name: name == 'tesseract')
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome')
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: calls.append(a) or subprocess.CompletedProcess(a, 0))
    config = _config(tmp_path, 'browser = "chromium"\n')
    assert doctor.setup_main(['--yes', '--config', config]) == 0
    assert calls and 'roughly 150 MB' in capsys.readouterr().err
    calls.clear()
    assert doctor.setup_main(['--yes', '--browser', 'chrome', '--config', config]) == 0
    err = capsys.readouterr().err
    assert not calls and 'nothing to download' in err and '150 MB' not in err


def test_doctor_reads_config_and_reports_a_bad_browser(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv('ANKIPLUS_CONFIG', raising=False)
    monkeypatch.setattr(doctor, 'have', lambda name: name == 'tesseract')
    monkeypatch.setattr(doctor, 'system_chrome', lambda: '/x/chrome')
    good = _config(tmp_path, 'browser = "chromium"\n')
    assert doctor.doctor_main(['--json', '--workspace-root', str(tmp_path), '--config', good]) == 1
    check = next(c for c in json.loads(capsys.readouterr().out)['checks'] if c['name'] == 'chromium')
    assert check['status'] == 'missing'          # chromium was asked for, and Chrome does not count
    (tmp_path/'bad').mkdir()
    bad = _config(tmp_path/'bad', 'browser = "firefox"\n')
    assert doctor.doctor_main(['--json', '--workspace-root', str(tmp_path), '--config', bad]) == 1
    check = next(c for c in json.loads(capsys.readouterr().out)['checks'] if c['name'] == 'chromium')
    assert check['status'] == 'missing' and 'firefox' in check['detail'] and check['fix']
