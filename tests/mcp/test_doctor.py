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
    assert out.returncode == 0 and out.stdout.strip() == 'ankiplusmcp 0.2.0'


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
