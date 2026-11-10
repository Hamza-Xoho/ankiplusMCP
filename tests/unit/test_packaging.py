"""The installed package must carry the reviewer templates and note-type assets."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def files(root):
    return {path.relative_to(root): path.read_bytes()
            for path in root.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_packaged_templates_match_skill_copy():
    assert files(ROOT/'src/cards/templates/review') == files(ROOT/'.claude/skills/anki2/templates/review')


def test_packaged_assets_match_skill_copy():
    assert files(ROOT/'src/cards/assets/coldrecall-cloze') == files(ROOT/'.claude/skills/anki2/assets/coldrecall-cloze')


def test_codex_install_replaces_stale_skill_without_touching_other_skills(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location('package_ankiv2', ROOT/'scripts/package_ankiv2.py')
    package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    monkeypatch.setattr(package, 'HOME', tmp_path/'home')
    monkeypatch.setattr(package, 'DIST', tmp_path/'dist/ankiv2')
    source = package.DIST/'skill'
    source.mkdir(parents=True)
    (source/'SKILL.md').write_text('current skill')
    target = package.HOME/'.agents/skills/ankiv2'
    target.mkdir(parents=True)
    (target/'SKILL.md').write_text('stale skill')
    other = target.parent/'other'
    other.mkdir()
    (other/'SKILL.md').write_text('keep')
    package.install('codex')
    assert (target/'SKILL.md').read_text() == 'current skill'
    assert (other/'SKILL.md').read_text() == 'keep'
