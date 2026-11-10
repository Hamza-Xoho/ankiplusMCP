"""P4 re-render must survive review drops: a dropped note is listed in changed_ids but is gone from drafts."""
import json

import pytest

from cards import build
from cards.common.errors import CardsError
from cards.common.paths import Build


@pytest.fixture
def folder(tmp_path):
    rows = [{'_meta': {'tool': 'cards apply'}}, {'id': 'n001'}, {'id': 'n002'}]
    (tmp_path / 'drafts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    return Build(tmp_path)


def fake_render(calls):
    def run(args):
        calls.append(args.only)
        if args.only and not set(args.only.split(',')) <= {'n001', 'n002'}:
            raise CardsError('E50', 'only: line 1 field id unknown', 'choose active note ids')
    return run


def test_rerender_with_a_dropped_id_falls_back_to_a_full_render(folder, monkeypatch):
    calls = []
    monkeypatch.setattr(build.render, 'run', fake_render(calls))
    build._rerender(folder, ['n001', 'n099'])
    assert calls == [None]


def test_rerender_with_only_dropped_ids_renders_everything(folder, monkeypatch):
    calls = []
    monkeypatch.setattr(build.render, 'run', fake_render(calls))
    build._rerender(folder, ['n099'])
    assert calls == [None]


def test_rerender_with_live_ids_stays_scoped(folder, monkeypatch):
    calls = []
    monkeypatch.setattr(build.render, 'run', fake_render(calls))
    build._rerender(folder, ['n002'])
    assert calls == ['n002']
