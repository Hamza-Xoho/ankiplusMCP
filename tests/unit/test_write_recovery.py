import json

from test_build_command import cli, prepared, state


def test_count_mismatch_does_not_finish_p6_or_record_success(tmp_path):
    folder = prepared(tmp_path, 'P6', 'P5')
    (folder / 'write').mkdir()
    (folder / 'gate.json').write_text('{"status":"passed"}')
    (folder / 'write/expected.json').write_text('{"created":2,"updated":0,"suspend_notes":0}')
    (folder / 'write/receipts.json').write_text(json.dumps({'batches': [{'status': 'success', 'created': 1, 'failed': 0}]}))
    result = cli('build', '--continue', '--build', folder, cwd=tmp_path)
    assert result.returncode == 3
    assert 'counts differ' in result.stdout
    saved = state(folder)
    assert saved['phase'] == 'P6'
    assert saved['write'].get('status') != 'done'
    assert not any(h['phase'] == 'P6' and h['status'] == 'done' for h in saved['history'])
