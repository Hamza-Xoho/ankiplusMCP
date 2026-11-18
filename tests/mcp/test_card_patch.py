import pytest

from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError


def setup(tmp_path):
    service = Service(tmp_path / 'work', [tmp_path])
    workspace = service.store.create('cards')['id']
    service.save_cards(workspace, [{'id': 'a', 'fields': {'Text': '{{c1::Nucleus}}', 'Extra': 'Keep this context'}, 'tags': ['one']},
                                    {'id': 'b', 'fields': {'Text': '{{c1::Golgi}}'}, 'tags': ['two']}], 0)
    return service, workspace


def test_patching_one_field_preserves_other_cards_and_fields(tmp_path):
    service, workspace = setup(tmp_path)
    try:
        before = service.get_cards(workspace)['cards']
        result = service.patch_cards(workspace, [{'id': 'a', 'changes': {'fields': {'Text': '{{c1::Membrane}}'}}}], 1)
        after = service.get_cards(workspace)['cards']
        assert result == {'revision': 2, 'changed_ids': ['a']}
        assert after[0]['fields'] == {'Text': '{{c1::Membrane}}', 'Extra': 'Keep this context'}
        assert after[0]['tags'] == ['one']
        assert after[1] == before[1]
    finally:
        service.close()


def test_stale_duplicate_unknown_and_invalid_patches_never_partially_apply(tmp_path):
    service, workspace = setup(tmp_path)
    try:
        original = service.store.path(workspace, 'cards.json').read_bytes()
        bad = [[{'id': 'a', 'changes': {'fields': {'Text': '{{c1::New}}'}}}, {'id': 'missing', 'changes': {'tier': 1}}],
               [{'id': 'a', 'changes': {'tier': 1}}, {'id': 'a', 'changes': {'tier': 2}}],
               [{'id': 'a', 'changes': {'id': 'different'}}],
               [{'id': 'a', 'changes': {'tier': 99}}]]
        for patches in bad:
            with pytest.raises((DomainError, ValueError)):
                service.patch_cards(workspace, patches, 1)
            assert service.store.path(workspace, 'cards.json').read_bytes() == original
        with pytest.raises(DomainError, match='STALE'):
            service.patch_cards(workspace, [{'id': 'a', 'changes': {'tier': 1}}], 0)
    finally:
        service.close()


def test_noop_patch_does_not_invalidate_review_or_advance_revision(tmp_path):
    service, workspace = setup(tmp_path)
    try:
        result = service.patch_cards(workspace, [{'id': 'a', 'changes': {'tags': ['one']}}], 1)
        assert result == {'revision': 1, 'changed_ids': []}
    finally:
        service.close()


def test_changing_fields_invalidates_cached_anki_question_answer(tmp_path):
    service, workspace = setup(tmp_path)
    try:
        service.patch_cards(workspace, [{'id': 'a', 'changes': {'question': 'old question', 'answer': 'old answer'}}], 1)
        service.patch_cards(workspace, [{'id': 'a', 'changes': {'fields': {'Text': '{{c1::New}}'}}}], 2)
        card = service.get_cards(workspace, ids=['a'])['cards'][0]
        assert card['question'] is None and card['answer'] is None
    finally:
        service.close()


def test_concurrent_edit_between_patch_snapshot_and_save_is_preserved(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    service, workspace = setup(tmp_path)
    entered, release = Event(), Event()
    original = service.save_cards
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(*args, **kwargs)
    monkeypatch.setattr(service, 'save_cards', delayed)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(service.patch_cards, workspace, [{'id': 'a', 'changes': {'tier': 1}}], 1)
            assert entered.wait(2)
            cards = service.get_cards(workspace)['cards']
            cards[1]['fields']['Text'] = '{{c1::Concurrent}} change'
            original(workspace, cards, 1)
            release.set()
            with pytest.raises(DomainError, match='STALE'):
                future.result(timeout=2)
        after = service.get_cards(workspace)['cards']
        assert after[0]['tier'] is None
        assert after[1]['fields']['Text'] == '{{c1::Concurrent}} change'
    finally:
        release.set()
        service.close()
