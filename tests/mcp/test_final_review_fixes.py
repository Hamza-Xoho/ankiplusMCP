"""Material whole-product review regressions; no real collection or host access."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import base64
import io
import re
import pytest
from PIL import Image
from ankiplusmcp.store import DomainError
from ankiplusmcp.quality import QualityGate
from test_coordinator import workflow, covered, existing, run


def test_contradiction_survives_a_shorter_valid_citation(workflow):
    c,s,e,r,d=workflow
    d['source_disagreement']=True;covered(workflow)
    d['source_disagreement']=False;d['source_refs'][0]['quote']='Fibroblasts'
    covered(workflow)
    assert run(c.stage(r.id)).decisions[0]['disposition']=='pending'


def test_contradiction_folds_retained_legacy_reference_keys(workflow):
    c,s,e,r,d=workflow
    c.event(r.id,'source_contradiction',{'token':'retained-token','source_key':'old-reference-specific-key',
        'concept_id':d['concept_id'],'source_refs':deepcopy(d['source_refs'])})
    d['source_refs'][0]['quote']='Fibroblasts'
    covered(workflow)
    assert run(c.stage(r.id)).decisions[0]['disposition']=='pending'
    c.event(r.id,'source_contradiction_resolved',{'tokens':['retained-token']})
    covered(workflow)
    assert run(c.stage(r.id)).decisions[0]['disposition']=='propose_create'


def test_serve_restart_cannot_restore_confirmed_revoked_roots(tmp_path,monkeypatch):
    from ankiplusmcp import __main__ as entry
    from ankiplusmcp.service import Service
    from ankiplusmcp.server import API
    source=tmp_path/'source';source.mkdir();secret=source/'revoked.md';secret.write_text('synthetic')
    root=tmp_path/'data';s=Service(root,[source]);api=API(s)
    cfg=api.get_student_setup()['configuration']
    change=api.propose_preferences({'source_roots':[]},cfg['config_version']);api.confirm_preferences(change['id']);s.close()
    observed=[]
    def server(service):
        observed.append(service.store.source_roots_origin)
        with pytest.raises(DomainError):service.store.source(str(secret))
        return SimpleNamespace(run=lambda **_:None)
    monkeypatch.setattr('ankiplusmcp.server.create_server',server)
    entry.serve(['--workspace-root',str(root),'--source-root',str(source)])
    assert observed==['preferences']


def rows_for(c,p,workspace,tmp_path):
    with patch('cards.render.render_rows',lambda rows,*a,**kw:rows),patch('ankiplusmcp.doctor.require_browser',lambda *a:'synthetic'):
        return QualityGate(c)._render(p,tmp_path/'render',workspace)


def test_update_quality_renders_retained_actual_tags(workflow,tmp_path):
    c,s,e,r,d=workflow;existing(workflow)
    e.model['tmpls']=[{'qfmt':'{{Tags}} {{Front}}','afmt':'{{Back}}'}]
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'action':'update','note_id':101}}],1)
    d['disposition']='explicit_update';covered(workflow);p=run(c.stage(r.id))
    rows=rows_for(c,p,r.workspace,tmp_path)
    assert 'Premade::Original' in rows[0]['question']
    assert '#AnkiPlus::Cells' not in rows[0]['question']


def native_io(workflow,size=(40,40)):
    c,s,e,r,d=workflow
    b=io.BytesIO();Image.new('RGB',size,'white').save(b,format='PNG');data=b.getvalue()
    e.media['label.png']=data
    fields={'Image':'<img src="label.png">','Occlusion':'{{c1::image-occlusion:rect:left=.1:top=.1:width=.2:height=.2:oi=1}}','Header':'','Back Extra':'','Comments':''}
    e.model={'name':'Image Occlusion','type':1,'flds':[{'name':n} for n in fields],
        'tmpls':[{'qfmt':'{{cloze:Occlusion}}{{Image}}','afmt':'{{cloze:Occlusion}}{{Image}}'}],'css':'.card{}'}
    original=e.call_tool
    async def transport(name,args):
        if name=='read_media_file':
            import hashlib
            return SimpleNamespace(isError=False,structuredContent={'filename':args['filename'],'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'data':base64.b64encode(data).decode()})
        return await original(name,args)
    e.call_tool=transport
    return fields


def test_existing_native_io_quality_masks_front(workflow,tmp_path):
    c,s,e,r,d=workflow;existing(workflow);e.notes[101]['fields']=native_io(workflow)
    covered(workflow);p=run(c.stage(r.id));rows=rows_for(c,p,r.workspace,tmp_path)
    assert p.review_cards[0]['kind']=='io'
    assert 'image-occlusion:rect:' not in rows[0]['question']
    encoded=re.search(r'data:image/png;base64,([^"\s]+)',rows[0]['question'])[1]
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as front:
        assert front.getpixel((8,8))[:3]==(255,220,110)
    assert 'data-ordinal="1"' in rows[0]['question']


def test_native_io_review_fits_phone_without_resizing_source(workflow):
    c,s,e,r,d=workflow;existing(workflow);e.notes[101]['fields']=native_io(workflow,(600,360))
    original=e.media['label.png'];covered(workflow);p=run(c.stage(r.id))
    ticket=QualityGate(c).prepare(r.id,p.content_digest,'student')
    assert ticket['tile_ids']==['fibroblast_c1']
    assert e.media['label.png']==original


def test_native_mask_expansion_is_bounded_before_rasterization(workflow,monkeypatch):
    c,s,e,r,d=workflow;existing(workflow);fields=native_io(workflow,(600,360))
    fields['Occlusion']=' '.join('{{c%d::image-occlusion:rect:left=.1:top=.1:width=.2:height=.2:oi=1}}'%n for n in range(1,121))
    e.notes[101]['fields']=fields;covered(workflow);p=run(c.stage(r.id));gate=QualityGate(c)
    monkeypatch.setattr(gate,'_render',lambda *a:(_ for _ in ()).throw(AssertionError('expensive raster entered')))
    with pytest.raises(DomainError,match='LIMIT'):gate.prepare(r.id,p.content_digest,'student')


def test_native_io_create_allowed_with_normal_saved_profile(workflow):
    c,s,e,r,d=workflow;fields=native_io(workflow)
    asset=s.store.path(r.workspace,'label.png');asset.write_bytes(e.media['label.png'])
    s.save_cards(r.workspace,[{'id':'fibroblast','kind':'io','notetype':'Image Occlusion','fields':fields,
        'deck':'Default','tags':['#AnkiPlus::Cells'],'source_ref':[1], 'media':[{'filename':'label.png','path':'label.png'}]}],1)
    covered(workflow);p=run(c.stage(r.id))
    assert p.operations[-1]['arguments']['model_name']=='Image Occlusion'
    assert not [f for f in p.findings if f['severity']=='blocker']


def test_css_dependencies_refused_before_quality_browser(workflow,tmp_path):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id))
    p.review_cards[0]['model']['css']='.diagram{background-image:url("diagram.png")}'
    with patch('cards.render.render_rows',side_effect=AssertionError('expensive render entered')):
        with pytest.raises(DomainError,match='UNSUPPORTED'):
            QualityGate(c)._render(p,tmp_path/'render',r.workspace)


def test_embedded_css_dependencies_refused_before_quality_browser(workflow,tmp_path):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id))
    p.review_cards[0]['fields']['Front']='<div style="background:url(diagram.png)">Question</div>'
    with patch('cards.render.render_rows',side_effect=AssertionError('expensive render entered')):
        with pytest.raises(DomainError,match='UNSUPPORTED'):QualityGate(c)._render(p,tmp_path/'render',r.workspace)


def test_unimplemented_template_metadata_refuses_instead_of_empty_review(workflow,tmp_path):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id))
    p.review_cards[0]['model']['tmpls'][0]['qfmt']='{{Deck}} {{Front}}'
    with patch('cards.render.render_rows',side_effect=AssertionError('incomplete render entered')):
        with pytest.raises(DomainError,match='UNSUPPORTED'):QualityGate(c)._render(p,tmp_path/'render',r.workspace)


def test_expansion_bound_refuses_before_render_or_packet_allocation(workflow,monkeypatch):
    c,s,e,r,d=workflow
    cfg=c.config.read();c.config.confirm(c.config.propose({'note_type':'Cloze'},cfg.config_version).id)
    e.model.update(name='Cloze',type=1,tmpls=[{'qfmt':'{{cloze:Back}}','afmt':'{{cloze:Back}}'}])
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'kind':'cloze','notetype':'Cloze',
        'fields':{'Back':' '.join('{{c%d::answer}}'%n for n in range(1,1002))}}}],1)
    covered(workflow);p=run(c.stage(r.id));gate=QualityGate(c)
    monkeypatch.setattr(gate,'_render',lambda *a:(_ for _ in ()).throw(AssertionError('expensive render entered')))
    with pytest.raises(DomainError,match='LIMIT'):gate.prepare(r.id,p.content_digest,'student')
    assert not list((c.runs._path(r.id)/'quality').glob('*'))


@pytest.mark.parametrize('mixed',[False,True])
def test_already_active_at_stage_is_unchanged_without_send(workflow,mixed):
    from test_workflow_quality import quality_ready
    from test_verified_onboarding import setup_ready
    c,s,e,r,d=workflow;existing(workflow);e.cards[201]['queue']=0
    if mixed:
        e.cards[202]={**e.cards[201],'id':202,'ord':1,'queue':-1}
        e.cards[201]['queue']=-1;d['card_ids']=[201,202];covered(workflow)
        e.cards[201]['queue']=0
    p=quality_ready(workflow);c.authorize(r.id,p.digest);setup_ready(workflow)
    result=run(c.apply(r.id,p.digest))
    assert result['counts']['cards_unsuspended']==int(mixed)
    assert any(v['status']=='unchanged' and v['card_ids']==[201] for v in result['results'])
    assert e.sent==([('card_unsuspend',{'card_ids':[202]})] if mixed else [])


def test_layout_bounds_refuse_before_screenshot_allocation(tmp_path,monkeypatch):
    from cards.render import render_rows
    from cards.common.errors import CardsError
    from ankiplusmcp.doctor import require_browser
    from playwright.sync_api import Page
    calls=[]
    monkeypatch.setattr(Page,'screenshot',lambda *a,**kw:calls.append(kw) or (_ for _ in ()).throw(AssertionError('screenshot allocation entered')))
    with pytest.raises(CardsError,match='dimensions'):
        render_rows([{'id':'huge','question':'<div style="height:1000000px">Question</div>','answer':'Answer'}],
            tmp_path/'renders',css='',browser=require_browser('auto'),limits={'width':390,'height':12000,'pixels':24_000_000})
    assert not calls


def test_embedded_image_dimensions_checked_before_mask_or_browser(workflow,monkeypatch):
    import struct,zlib
    c,s,e,r,d=workflow
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',5000,5000,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'))+chunk(b'IEND',b'')
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'<img src="data:image/png;base64,'+base64.b64encode(png).decode()+'">'}}}],1)
    covered(workflow);p=run(c.stage(r.id));gate=QualityGate(c)
    monkeypatch.setattr(gate,'_render',lambda *a:(_ for _ in ()).throw(AssertionError('expensive render entered')))
    with pytest.raises(DomainError,match='LIMIT'):gate.prepare(r.id,p.content_digest,'student')


@pytest.mark.parametrize('location',['field','template','other_field_open_tag'])
def test_embedded_image_whitespace_and_template_headers_are_bounded(workflow,monkeypatch,location):
    import struct,zlib
    c,s,e,r,d=workflow
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',5000,5000,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'))+chunk(b'IEND',b'')
    markup='<img src="data:image/png;base64, \n'+base64.b64encode(png).decode()+'">'
    if location!='template':s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':({'Back':'<script>inert','Front':markup} if location=='other_field_open_tag' else {'Back':markup})}}],1)
    else:e.model['tmpls'][0]['qfmt']=markup+'{{Front}}'
    covered(workflow);p=run(c.stage(r.id));gate=QualityGate(c)
    monkeypatch.setattr(gate,'_render',lambda *a:(_ for _ in ()).throw(AssertionError('expensive render entered')))
    with pytest.raises(DomainError,match='LIMIT'):gate.prepare(r.id,p.content_digest,'student')
