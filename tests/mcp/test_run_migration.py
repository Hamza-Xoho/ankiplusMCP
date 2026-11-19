import hashlib
import json


def test_legacy_import_retains_caller_evidence_without_modifying_originals(tmp_path):
    from ankiplusmcp.runs import RunStore
    legacy = tmp_path / 'legacy'
    (legacy / 'write/plan1').mkdir(parents=True)
    (legacy / 'workspace.json').write_text(json.dumps({'id': 'w1', 'source': {'sha256': 'b' * 64}}))
    (legacy / 'write/plan1/plan.json').write_text(json.dumps({'created': 2}))
    (legacy / 'write/plan1/external-results.json').write_text(json.dumps({
        'evidence_origin': 'caller_supplied', 'independently_verified': False,
        'results': [{'operation': 'create', 'status': 'success', 'note_ids': [101, 102], 'card_ids': []}]}))
    before = {str(p.relative_to(legacy)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in legacy.rglob('*') if p.is_file()}
    store = RunStore(tmp_path / 'data')
    runs = store.import_legacy('w1', legacy)
    assert len(runs) == 1
    receipt = next(e for e in runs[0].events if e.kind == 'legacy_result')
    assert receipt.payload['evidence_origin'] == 'caller_supplied'
    assert receipt.payload['independently_verified'] is False
    assert receipt.payload['note_ids'] == [101, 102]
    assert 'draft_id' not in receipt.payload
    after = {str(p.relative_to(legacy)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in legacy.rglob('*') if p.is_file()}
    assert before == after
    assert [r.id for r in store.import_legacy('w1', legacy)] == [runs[0].id]


def test_legacy_cards_workspace_does_not_invent_source_hash(tmp_path):
    from ankiplusmcp.runs import RunStore
    legacy = tmp_path / 'legacy'
    legacy.mkdir()
    (legacy / 'workspace.json').write_text('{"id":"w1","source":null}')
    run = RunStore(tmp_path / 'data').import_legacy('w1', legacy)[0]
    assert run.selection.source_hash is None
    assert run.config_version is None
    assert run.events[-1].kind == 'legacy_import'


def test_import_preserves_old_projection_shape_and_identity(tmp_path):
    from ankiplusmcp.runs import RunStore
    legacy = tmp_path / 'legacy'
    plan = legacy / 'write/plan1'
    plan.mkdir(parents=True)
    (legacy / 'workspace.json').write_text('{"id":"w1","source":null}')
    (plan / 'plan.json').write_text('{"created":1}')
    original = {'results': [{'operation': 'create', 'status': 'success', 'note_ids': [101]}]}
    (plan / 'external-results.json').write_text(json.dumps(original))
    store = RunStore(tmp_path / 'history')
    run = store.import_legacy('w1', legacy)[0]
    snapshots = list((store.directory / run.id / 'snapshots').glob('*.json'))
    assert len(snapshots) == 1
    assert json.loads(snapshots[0].read_text())['results'] == original
