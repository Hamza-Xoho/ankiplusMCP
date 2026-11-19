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


def test_student_setup_starts_from_launch_style_and_confirmed_defaults_drive_future_cards(tmp_path):
    from ankiplusmcp.coordinator import Coordinator
    s=service(tmp_path,'coldrecall')
    try:
        c=Coordinator(s)
        cfg=c.config.read()
        assert cfg.note_type=='ColdRecall Cloze' and cfg.tag_root=='#ColdRecall'
        c.config.confirm(c.config.propose({'note_type':'Basic','tag_root':'#Mine'},cfg.config_version).id)
        w=s.store.create('cards')['id']
        s.save_cards(w,[{'id':'new','kind':'basic','fields':{'Front':'Question','Back':'Answer'}}],0)
        assert s.get_cards(w)['cards'][0]['notetype']=='Basic'
        assert s.resolve_target(course='BIO101',number=3,title='Cells')['source_tag'].startswith('#Mine::')
    finally:s.close()


def test_one_save_uses_a_consistent_default_profile_snapshot(tmp_path,monkeypatch):
    s=service(tmp_path,'default');calls=0
    def changing(instance):
        nonlocal calls
        calls+=1
        return settings.PROFILES['default'] if calls==1 else settings.PROFILES['coldrecall']
    monkeypatch.setattr(Service,'profile',property(changing))
    try:
        w=s.store.create('cards')['id'];s.save_cards(w,[{'id':'a','fields':{'Text':'{{c1::a}}'}},{'id':'b','fields':{'Text':'{{c1::b}}'}}],0)
        assert [c['notetype'] for c in s.get_cards(w)['cards']]==['Cloze','Cloze']
    finally:s.close()


def test_target_identity_uses_one_profile_snapshot(tmp_path,monkeypatch):
    s=service(tmp_path,'default');calls=0
    def changing(instance):
        nonlocal calls
        calls+=1
        return settings.PROFILES['default'] if calls==1 else settings.PROFILES['coldrecall']
    monkeypatch.setattr(Service,'profile',property(changing))
    try:
        result=s.resolve_target(course='BIO101',number=3,title='Cells')
        assert result['note_type']=='Cloze' and result['source_tag'].startswith('#AnkiPlus::')
    finally:s.close()


def test_house_style_check_uses_one_profile_snapshot(tmp_path,monkeypatch):
    s=service(tmp_path,'default');w=s.store.create('cards')['id']
    s.save_cards(w,[{'id':'a','fields':{'Text':'{{c1::a}}'},'tags':['#AnkiPlus::Synthetic']},{'id':'b','fields':{'Text':'{{c1::b}}'},'tags':['#AnkiPlus::Synthetic']}],0)
    calls=0
    def changing(instance):
        nonlocal calls
        calls+=1
        return settings.PROFILES['default'] if calls==1 else settings.PROFILES['coldrecall']
    monkeypatch.setattr(Service,'profile',property(changing))
    try:assert s.check_cards(w,house_style=True)['blockers']==0
    finally:s.close()
