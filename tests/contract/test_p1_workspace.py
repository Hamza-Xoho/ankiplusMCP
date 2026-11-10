import json
from test_p0_foundations import ROOT

def test_fr25_cards_settings_lean():
    d=json.loads((ROOT/'.claude/settings.json').read_text())
    assert d.get('disableClaudeAiConnectors') is True
    assert '~/.claude/CLAUDE.md' in d.get('claudeMdExcludes',[])
    names={x['serverName'] for x in d.get('deniedMcpServers',[])}
    assert {'claude-flow','flow-nexus'} <= names
    assert 'anki' not in names
    assert d['enabledMcpjsonServers'] == ['anki']
    assert d['permissions']['allow'] and d['permissions']['ask'] and d['permissions']['deny']
