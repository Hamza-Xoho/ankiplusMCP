import pytest
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def card(**changes):
    return dict({'id':'n1','kind':'cloze','notetype':'ColdRecall Cloze','deck':'Test','fields':{'Text':'<b>Sodium</b> crosses {{c1::channels}}','Extra':''},'tags':[]}, **changes)


def test_standalone_cards_review_and_payload(tmp_path):
    s = Service(tmp_path/'work',[tmp_path]); w = s.store.create('cards')['id']
    result = s.save_cards(w,[card()],0)
    assert result['revision'] == 1
    assert not s.check_cards(w)['blockers']
    with pytest.raises(DomainError): s.save_cards(w,[card(),card()],1)
    review = s.prepare_review(w,scope='visual')
    assert 'cards' not in review
    submitted = s.submit_review(w,'reviewer',[{'card_id':'n1','verdict':'fix','message':'Use singular','rewrite':{'Text':'<b>Sodium</b> crosses a {{c1::channel}}'}}],1)
    assert s.get_cards(w)['cards'][0]['fields']['Text'].endswith('channels}}')
    diff = s.apply_changes(w,submitted['review_id'],2,apply=False)
    assert diff['changes']
    s.apply_changes(w,submitted['review_id'],2,apply=True)
    plan = s.prepare_write(w,3)
    assert plan['created'] == 1 and plan['updated'] == 0
    assert plan['performed_anki_operations'] == 0
    report = s.get_report(w)
    assert report['reported_successes'] == 0
    s.save_cards(w,[card()],3)
    with pytest.raises(DomainError,match='stale'): s.record_external_results(w,plan['plan_id'],[],4)
    s.close()


def test_existing_custom_fields_render(tmp_path):
    s = Service(tmp_path/'work',[tmp_path]); w = s.store.create('cards')['id']
    s.save_cards(w,[card(kind='basic',notetype='Custom',fields={'Prompt':'Ion?','Answer':'Sodium'},note_id=123,card_ids=[456],action='update')],0)
    assert not s.check_cards(w)['blockers']
    output = wait(s,w,s.render_cards(w))
    assert s.image_bytes(w,output['sheets'][0]['fronts']).startswith(b'\x89PNG')
    plan = s.prepare_write(w,2)
    assert plan['updated'] == 1
    assert s.store.read_json(w,plan['artifact'])['updates'][0]['note_id'] == 123
    s.close()


def test_validation_and_results_are_honest(tmp_path):
    s = Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    with pytest.raises(Exception): s.save_cards(w,[card(action='update')],0)
    s.save_cards(w,[card()],0)
    with pytest.raises(DomainError): s.check_cards(w,coverage=True)
    plan = s.prepare_write(w,1)
    s.record_external_results(w,plan['plan_id'],[{'operation':'create','status':'success','note_ids':[111],'card_ids':[222]}],1)
    report=s.get_report(w)
    assert report['reported_successes'] == 1
    assert report['evidence_origin'] == 'caller_supplied'
    assert report['independently_verified'] is False
    s.close()


def test_render_leaves_no_fake_build_inputs(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[card()],0)
    result=wait(s,w,s.render_cards(w,css='.card{color:red}'))
    folder=s.store.path(w,result['prefix'])
    assert (folder/'input.json').is_file()
    assert not (folder/'input.jsonl').exists() and not (folder/'model').exists()
    assert s.image_bytes(w,result['sheets'][0]['fronts']).startswith(b'\x89PNG')
    s.close()


def test_visual_review_uses_card_hash_not_unrelated_revision(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[card()],0)
    wait(s,w,s.render_cards(w))
    s.submit_review(w,'reviewer',[{'card_id':'n1','verdict':'pass'}],2)
    assert 'sheets' in s.prepare_review(w,scope='visual')
    s.save_cards(w,[card(fields={'Text':'{{c1::New}} content'})],3)
    assert s.prepare_review(w,scope='visual')['status']=='stale_previews'
    s.close()


def test_invalid_zero_cloze_is_a_blocker(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[card(fields={'Text':'{{c0::Sodium}}'})],0)
    assert s.check_cards(w)['blockers']
    s.close()


def test_desktop_and_light_samples(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[card()],0)
    result=wait(s,w,s.render_cards(w,desktop_sample=1,light=True))
    assert len(result['samples'])==2
    from PIL import Image
    with Image.open(s.store.path(w,result['samples'][0])) as im: assert im.width==1024
    s.close()


def test_get_cards_revision_matches_snapshot(tmp_path):
    import threading
    import time
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[card(fields={'Text':'{{c1::revision1}}'})],0)
    event=threading.Event(); original=s._select
    def delayed(*args):
        result=original(*args); event.set(); time.sleep(.05); return result
    s._select=delayed
    def writer():
        event.wait(2); s.save_cards(w,[card(fields={'Text':'{{c1::revision2}}'})],1)
    thread=threading.Thread(target=writer); thread.start()
    result=s.get_cards(w)
    thread.join(2)
    assert result['cards'][0]['fields']['Text']=='{{c1::revision'+str(result['revision'])+'}}'
    s.close()


def test_house_style_uses_the_profile_tag_root(tmp_path):
    s = Service(tmp_path/"work", [tmp_path])  # default profile: tag root #AnkiPlus
    w = s.store.create("cards")["id"]
    c = card(tags=["#AnkiPlus::T"])
    s.save_cards(w, [c], 0)
    assert "L10" not in {f["code"] for f in s.check_cards(w, house_style=True)["findings"]}
    s.save_cards(w, [{**c, "tags": ["#Other::T"]}], 1)
    assert "L10" in {f["code"] for f in s.check_cards(w, house_style=True)["findings"]}
    s.close()
