from ankiplusmcp.service import Service


def test_reporting_second_batch_preserves_first_batch_and_replay_does_not_double_count(tmp_path):
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        s.save_cards(workspace, [{'id': 'n1', 'fields': {'Text': '{{c1::Nucleus}}'}}], 0)
        plan = s.prepare_write(workspace, 1)
        first = {'operation': 'create', 'status': 'success', 'note_ids': [101], 'batch_artifact': 'batch-one.json'}
        second = {'operation': 'create', 'status': 'success', 'note_ids': [102], 'batch_artifact': 'batch-two.json'}
        s.record_external_results(workspace, plan['plan_id'], [first], 1)
        s.record_external_results(workspace, plan['plan_id'], [second], 2)
        s.record_external_results(workspace, plan['plan_id'], [first], 3)
        evidence = s.store.read_json(workspace, f"write/{plan['plan_id']}/external-results.json")
        assert [r['note_ids'] for r in evidence['results']] == [[101], [102]]
        assert evidence['independently_verified'] is False
        assert s.get_report(workspace)['reported_successes'] == 2
        journal = list(s.store.path(workspace, f"write/{plan['plan_id']}/result-events").glob('*.json'))
        assert len(journal) == 3
    finally:
        s.close()


def test_journal_recovers_receipt_published_before_projection_crash(tmp_path, monkeypatch):
    from ankiplusmcp import payloads
    import pytest
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        s.save_cards(workspace, [{'id': 'n1', 'fields': {'Text': '{{c1::Nucleus}}'}}], 0)
        plan = s.prepare_write(workspace, 1)
        original = payloads._publish
        def interrupt(path, value):
            if path.name == 'external-results.json':
                raise OSError('interrupted projection')
            return original(path, value)
        monkeypatch.setattr(payloads, '_publish', interrupt)
        first = {'operation': 'create', 'status': 'success', 'note_ids': [101]}
        with pytest.raises(OSError):
            s.record_external_results(workspace, plan['plan_id'], [first], 1)
        monkeypatch.setattr(payloads, '_publish', original)
        second = {'operation': 'create', 'status': 'success', 'note_ids': [102]}
        s.record_external_results(workspace, plan['plan_id'], [second], 1)
        result = s.store.read_json(workspace, f"write/{plan['plan_id']}/external-results.json")
        assert {tuple(row['note_ids']) for row in result['results']} == {(101,), (102,)}
        assert result['independently_verified'] is False
    finally:
        s.close()
