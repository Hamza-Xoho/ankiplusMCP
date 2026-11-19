import json
import os
from pathlib import Path
import subprocess
import sys

from ankiplusmcp.runs import RunEvent, RunStore, SourceSelection


def cli(root, *args):
    return subprocess.run([sys.executable, '-m', 'ankiplusmcp', 'history', *args, '--workspace-root', str(root)],
                          capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(Path(__file__).parents[2] / 'src')})


def test_history_can_find_runs_by_card_and_show_persisted_decisions(tmp_path):
    store = RunStore(tmp_path)
    run = store.start('lecture1', SourceSelection(source_hash='a' * 64, label='Connective tissue'), 1)
    store.append(run.id, RunEvent(kind='operation_result', payload={'note_ids': [101], 'card_ids': [201], 'outcome': 'confirmed'}))
    result = cli(tmp_path, 'list', '--card-id', '201', '--json')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['runs'][0]['id'] == run.id
    assert cli(tmp_path, 'list').stdout.find('Connective tissue') >= 0
    shown = cli(tmp_path, 'show', run.id, '--json')
    assert json.loads(shown.stdout)['events'][1]['payload']['card_ids'] == [201]
    assert cli(tmp_path, 'rebuild').returncode == 0


def test_history_export_never_overwrites_an_existing_file(tmp_path):
    run = RunStore(tmp_path).start('lecture1', SourceSelection(label='Textbook'), 1)
    output = tmp_path / 'summary.md'
    first = cli(tmp_path, 'export', run.id, '--output', str(output))
    assert first.returncode == 0, first.stderr
    original = output.read_bytes()
    assert b'Textbook' in original
    second = cli(tmp_path, 'export', run.id, '--output', str(output))
    assert second.returncode == 2
    assert output.read_bytes() == original


def test_history_errors_are_structured_without_starting_stdio(tmp_path):
    result = cli(tmp_path, 'show', '../outside', '--json')
    assert result.returncode == 2
    assert json.loads(result.stdout)['error']['code'] == 'RUN'
    assert 'Traceback' not in result.stderr


def test_history_cli_finds_actual_student_coordinator_runs(tmp_path):
    from ankiplusmcp.service import Service
    from ankiplusmcp.coordinator import Coordinator
    s=Service(tmp_path,[tmp_path])
    try:
        workspace=s.store.create('cards')['id'];run=Coordinator(s).start(workspace)
        result=cli(tmp_path,'list','--json')
        assert result.returncode==0,result.stderr
        assert any(row['id']==run.id for row in json.loads(result.stdout)['runs'])
    finally:s.close()
