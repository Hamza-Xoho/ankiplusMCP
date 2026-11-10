import os
from pathlib import Path
import pytest
from ankiplusmcp import settings
from ankiplusmcp.store import Store, DomainError


def test_workspace_default_is_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = settings.default_workspace_root()
    assert root.name == 'workspaces' and 'ankiplusmcp' in root.parts and tmp_path not in root.parents


def test_flags_beat_env_and_empty_entries_are_dropped(tmp_path):
    env = {'ANKIPLUS_SOURCE_ROOTS': os.pathsep.join(['', str(tmp_path), ''])}
    assert settings.configured_source_roots(['/a b'], env) == ([Path('/a b')], 'flags')
    assert settings.configured_source_roots(None, env) == ([tmp_path], 'env')
    assert settings.configured_source_roots(None, {}) is None


def test_cwd_is_refused_at_root_and_home(tmp_path):
    assert settings.safe_cwd_root(Path('/'), tmp_path) is None
    assert settings.safe_cwd_root(tmp_path, tmp_path) is None
    assert settings.safe_cwd_root(tmp_path/'proj', tmp_path) == tmp_path/'proj'


def test_no_roots_gives_source_error_naming_the_flag(tmp_path):
    store = Store(tmp_path/'w', None); store.set_source_roots([], 'none')
    f = tmp_path/'a.txt'; f.write_text('x')
    with pytest.raises(DomainError) as e: store.source(str(f))
    assert e.value.code == 'SOURCE' and '--source-root' in e.value.remedy
