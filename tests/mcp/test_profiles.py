import pytest
from ankiplusmcp import settings
from ankiplusmcp.service import Service

CARD = [{'id': 'a', 'fields': {'Text': 'x {{c1::y}}'}}]


def service(tmp_path, name):
    return Service(tmp_path, [tmp_path], settings.PROFILES[name])


@pytest.mark.parametrize('name,note,root', [('default', 'Cloze', '#AnkiPlus'), ('coldrecall', 'ColdRecall Cloze', '#ColdRecall')])
def test_profile_sets_note_type_and_tag_root(tmp_path, name, note, root):
    s = service(tmp_path, name)
    try:
        w = s.store.create('cards')['id']; s.save_cards(w, CARD, 0)
        assert s.get_cards(w)['cards'][0]['notetype'] == note
        t = s.resolve_target(course='BIO101', number=3, title='Membranes')
        assert t['source_tag'].startswith(root + '::') and t['note_type'] == note
    finally: s.close()


def test_explicit_note_type_is_kept(tmp_path):
    s = service(tmp_path, 'default')
    try:
        w = s.store.create('cards')['id']; s.save_cards(w, [dict(CARD[0], notetype='Basic')], 0)
        assert s.get_cards(w)['cards'][0]['notetype'] == 'Basic'
    finally: s.close()


def test_config_file_precedence_and_errors(tmp_path):
    cfg = tmp_path/'config.toml'; cfg.write_text('profile = "coldrecall"\ntag_root = "#Mine"\n')
    p = settings.load_profile(None, cfg, {})
    assert (p.note_type, p.tag_root) == ('ColdRecall Cloze', '#Mine')
    assert settings.load_profile('default', cfg, {}).tag_root == '#AnkiPlus'
    cfg.write_text('profile = "nope"\n')
    with pytest.raises(ValueError, match='nope'): settings.load_profile(None, cfg, {})
    cfg.write_text('colour = "red"\n')
    with pytest.raises(ValueError, match='colour'): settings.load_profile(None, cfg, {})


def test_capabilities_report_the_profile(tmp_path):
    from ankiplusmcp.server import API
    s = service(tmp_path, 'coldrecall')
    try:
        assert API(s).capabilities()['profile'] == {'name': 'coldrecall', 'note_type': 'ColdRecall Cloze', 'tag_root': '#ColdRecall'}
    finally: s.close()
