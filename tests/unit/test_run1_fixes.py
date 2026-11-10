import json, shutil
from pathlib import Path
from cards.check.schema import validate_skips
from cards.meter import transcript

ROOT = Path(__file__).resolve().parents[2]


def test_rejected_in_review_skip_is_valid():
    rows = [(1, {'slide': 2, 'item': 'x', 'reason': 'rejected_in_review', 'note': 'n'})]
    findings, valid = validate_skips(rows, {2}, set(), 'skipped.jsonl')
    assert findings == [] and len(valid) == 1


def test_subagent_meta_without_isfork(tmp_path):
    src = ROOT / 'tests/fixtures/transcripts/w8'
    dst = tmp_path / 'sess'
    shutil.copytree(src, dst)
    # session() takes <id>.jsonl with sibling <id>/subagents; reuse the subagent as main too
    main = tmp_path / 'sess.jsonl'
    shutil.copy(dst / 'subagents/agent-review.jsonl', main)
    meta = dst / 'subagents/agent-review.meta.json'
    meta.write_text(json.dumps({'agentType': 'anki-student', 'description': 'd', 'toolUseId': 't', 'spawnDepth': 1}))
    out = transcript.session(main)
    assert out['subagents'][0]['type'] == 'anki-student'
    assert out['subagents'][0]['is_fork'] is False
    meta.write_text(json.dumps({'agentType': 'fork'}))
    assert transcript.session(main)['subagents'][0]['is_fork'] is True


def test_report_format_states_code_families():
    t = (ROOT / '.claude/skills/anki2/templates/review/maintainer/report-format.md').read_text()
    assert 'note records use A1' in t and 'set records use S1' in t
