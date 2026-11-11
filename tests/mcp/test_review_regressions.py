import threading
from pathlib import Path
import pytest
from PIL import Image
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def test_field_rewrite_invalidates_supplied_rendered_html(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[{'id':'a','kind':'basic','fields':{'Front':'Old','Back':'Answer'},'question':'Old','answer':'Answer'}],0)
    review=s.submit_review(w,'reviewer',[{'card_id':'a','verdict':'fix','rewrite':{'Front':'New'}}],1)
    s.apply_changes(w,review['review_id'],2,apply=True)
    preview=wait(s,w,s.render_cards(w))
    rendered=s.store.read_json(w,preview['prefix']+'/input.json')
    assert 'New' in rendered[0]['question'] and 'Old' not in rendered[0]['question']
    s.close()


def test_cancelled_extraction_preserves_current_source_and_revision(tmp_path,monkeypatch):
    import cards.extract
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('lecture',text='# One\nFirst fact\n\f\n# Two\nSecond fact')['id']
    wait(s,w,s.extract_source(w,'1'))
    before=s.read_source(w); revision=s.store.get(w)['revision']
    entered=threading.Event(); release=threading.Event(); native=cards.extract.extract_source
    def paused(*args,**kwargs):
        result=native(*args,**kwargs); entered.set(); release.wait(3); return result
    monkeypatch.setattr(cards.extract,'extract_source',paused)
    job=s.extract_source(w,'2'); assert entered.wait(2)
    s.jobs.cancel(w,job['id']); release.set(); s.jobs.close()
    assert s.jobs.get(w,job['id'])['status']=='cancelled'
    assert s.store.get(w)['revision']==revision
    assert s.read_source(w)==before


def test_pdf_raster_limit_checked_before_allocation(tmp_path,monkeypatch):
    import pymupdf
    pdf=tmp_path/'big.pdf'
    with pymupdf.open() as doc:
        p=doc.new_page(width=4000,height=4000)
        p.insert_text((10,20),'text')
        import io
        raw=io.BytesIO(); Image.new('RGB',(1,1),'red').save(raw,'PNG')
        p.insert_image(p.rect,stream=raw.getvalue()); doc.save(pdf)
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('lecture',source_path=str(pdf))['id']
    requests=[]; native=pymupdf.Page.get_pixmap
    def bounded(self,**kwargs):
        matrix=kwargs.get('matrix',pymupdf.Matrix(1,1)); clip=kwargs.get('clip',self.rect)
        pixels=clip.width*clip.height*matrix.a*matrix.d
        requests.append(pixels)
        if pixels>20_000_000: raise RuntimeError('unsafe raster request')
        return native(self,**kwargs)
    monkeypatch.setattr(pymupdf.Page,'get_pixmap',bounded)
    job=s.extract_source(w); s.jobs.close()
    result=s.jobs.get(w,job['id'])
    assert result['status']=='failed' and result['error']['code']=='LIMIT'
    assert not any(p>20_000_000 for p in requests)


def test_conflicting_media_and_updates_are_refused(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    media=[]
    for color in ('red','blue'):
        path=tmp_path/(color+'.png'); Image.new('RGB',(10,10),color).save(path)
        media.append(s.import_image(w,str(path))['artifact'])
    cards=[{'id':str(i),'kind':'basic','fields':{'Front':'<img src="same.png">','Back':str(i)},'media':[{'path':m,'filename':'same.png'}]} for i,m in enumerate(media)]
    s.save_cards(w,cards,2)
    with pytest.raises(DomainError,match='media'): s.prepare_write(w,3)
    cards=[{'id':str(i),'kind':'basic','action':'update','note_id':123,'fields':{'Front':str(i)}} for i in range(2)]
    s.save_cards(w,cards,3)
    with pytest.raises(DomainError,match='update'): s.prepare_write(w,4)
    s.close()


@pytest.mark.parametrize('kind,fields',[
    ('cloze',{'Text':'{{c1::ok}} {{c0::invalid}} {{c2::}}'}),
    ('io',{'Image':'not an image','Occlusion':'not native markup'}),
    ('io',{'Image':'<img src="ok.png">','Occlusion':'{{c1::image-occlusion:rect:left=.9:top=.1:width=.5:height=.1:oi=1}}'}),
])
def test_every_cloze_and_io_geometry_is_validated(tmp_path,kind,fields):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    s.save_cards(w,[{'id':'a','kind':kind,'fields':fields}],0)
    assert s.check_cards(w)['blockers']>0
    with pytest.raises(DomainError): s.prepare_write(w,1)
    s.close()


def test_conflicting_updates_same_note_are_refused(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    cards=[{'id':str(i),'kind':'basic','action':'update','note_id':123,'fields':{'Front':str(i)}} for i in range(2)]
    s.save_cards(w,cards,0)
    with pytest.raises(DomainError,match='update'): s.prepare_write(w,1)
    s.close()


def test_identical_media_dedup_and_compatible_note_updates(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('cards')['id']
    image=tmp_path/'same.png'; Image.new('RGB',(10,10),'red').save(image)
    one=s.import_image(w,str(image))['artifact']; two=s.import_image(w,str(image))['artifact']
    cards=[{'id':'a','kind':'basic','action':'update','note_id':123,'fields':{'Front':'one'},'media':[{'path':one,'filename':'same.png'}]},
           {'id':'b','kind':'basic','action':'update','note_id':123,'fields':{'Back':'two'},'media':[{'path':two,'filename':'same.png'}]}]
    s.save_cards(w,cards,2)
    plan=s.prepare_write(w,3); data=s.store.read_json(w,plan['artifact'])
    assert data['updates']==[{'note_id':123,'fields':{'Front':'one','Back':'two'}}]
    assert len(data['media'])==1
    occlusion=s.build_occlusion(w,one,[{'left':.1,'top':.1,'width':.2,'height':.2,'text':'name'}])
    s.save_cards(w,[{'id':'io','kind':'io','fields':occlusion['fields'],'media':occlusion['media']}],4)
    assert not s.check_cards(w)['blockers']
    assert s.prepare_write(w,5)['created']==1
    s.close()
