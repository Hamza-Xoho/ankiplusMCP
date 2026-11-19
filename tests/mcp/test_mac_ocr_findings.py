import subprocess
from pathlib import Path
import pytest
from PIL import Image
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def test_empty_successful_ocr_is_honest(tmp_path,monkeypatch):
    import cards.extract.ocr as ocr
    monkeypatch.setattr(ocr,'extract',lambda *a,**kw:{'image_size':{'width':20,'height':20},'regions':[],'repeated':[]})
    s=Service(tmp_path/'data',[tmp_path]);p=tmp_path/'blank.png';Image.new('RGB',(20,20),'white').save(p)
    try:
        w=s.store.create('cards')['id'];asset=s.import_image(w,str(p))['artifact']
        result=wait(s,w,s.ocr_image(w,asset));assert result['extraction_status']=='no_text'
        assert s.image_bytes(w,asset).startswith(b'\x89PNG')
    finally:s.close()


@pytest.mark.parametrize('outcome',['no_text','unavailable','failed','timeout'])
def test_image_only_page_retains_evidence_without_quotes(tmp_path,monkeypatch,outcome):
    import pymupdf
    import cards.extract.ocr as ocr
    def process(*a,**kw):
        if '--version' in a[0]:return subprocess.CompletedProcess(a[0],0,stdout=b'tesseract test')
        if outcome=='unavailable':raise FileNotFoundError('missing')
        if outcome=='failed':raise subprocess.CalledProcessError(1,a[0])
        if outcome=='timeout':raise subprocess.TimeoutExpired(a[0],30)
        return subprocess.CompletedProcess(a[0],0,stdout=b'text\tconf\tleft\ttop\twidth\theight\tblock_num\tpar_num\tline_num\n')
    monkeypatch.setattr(subprocess,'run',process);ocr._VERSION.clear()
    p=tmp_path/'blank.pdf'
    with pymupdf.open() as doc:doc.new_page();doc.save(p)
    s=Service(tmp_path/'data',[tmp_path])
    try:
        w=s.store.create('lecture',source_path=str(p))['id'];wait(s,w,s.extract_source(w))
        _,data,_=s.source_data(w);page=data['slides'][0]
        assert page['text']=='' and page['extraction_status']==outcome
        assert s.image_bytes(w,s.get_page_image(w,1)['artifact']).startswith(b'\x89PNG')
        from ankiplusmcp.evidence import EvidenceResolver
        resolver=EvidenceResolver(s.source_catalog);sha=s.store.get(w)['source']['sha256']
        ev=resolver.resolve(w,[{'source_hash':sha,'page':1}])[0]
        assert ev.quote is None and ev.extraction_status==outcome
        with pytest.raises(DomainError):resolver.resolve(w,[{'source_hash':sha,'page':1,'quote':'Invented nucleus'}])
    finally:s.close();ocr._VERSION.clear()


def test_chrome_without_playwright_is_not_a_usable_browser(tmp_path,monkeypatch):
    from ankiplusmcp import doctor
    monkeypatch.setattr(doctor,'system_chrome',lambda:tmp_path/'chrome')
    monkeypatch.setattr(doctor,'have',lambda name:False)
    import builtins
    original=builtins.__import__
    def missing(name,*a,**kw):
        if name.startswith('playwright'):raise ImportError('no playwright')
        return original(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',missing)
    check=next(x for x in doctor.run_checks(tmp_path,'chrome') if x['name']=='chromium')
    assert check['status']=='missing'


def test_desktop_can_read_packaged_workflow_without_skill_directory(tmp_path):
    from ankiplusmcp.server import API
    s=Service(tmp_path/'data',[])
    try:
        text=API(s).get_guidance('workflow')['text']
        assert text==Path('skills/ankiplusmcp/SKILL.md').read_text().split('---',2)[2].strip()
        assert 'reconcile_run' in text
    finally:s.close()


def test_detected_browser_with_launch_failure_fails_doctor(tmp_path,monkeypatch):
    from ankiplusmcp import doctor
    monkeypatch.setattr(doctor,'describe_browser',lambda setting:('chrome','system Chrome'))
    monkeypatch.setattr(doctor,'probe_browser',lambda browser:(_ for _ in ()).throw(RuntimeError('driver failed')))
    check=next(x for x in doctor.run_checks(tmp_path) if x['name']=='chromium')
    assert check['status']=='missing' and 'launch failed' in check['detail']


def test_legacy_empty_page_still_refuses_with_honest_remedy(tmp_path,monkeypatch):
    import pymupdf
    from cards.extract import pdf,ocr
    from cards.common.paths import Build
    from cards.common.errors import CardsError
    monkeypatch.setattr(ocr,'_words',lambda *a,**kw:[])
    p=tmp_path/'blank.pdf'
    with pymupdf.open() as doc:doc.new_page();doc.save(p)
    with pytest.raises(CardsError) as error:list(pdf.read(p,Build(tmp_path/'engine')))
    assert error.value.code=='E21' and 'install' not in str(error.value).lower()
