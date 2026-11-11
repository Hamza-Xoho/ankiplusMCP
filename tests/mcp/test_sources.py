import json
import time
import pytest
from PIL import Image
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError


def wait(service, w, job):
    for _ in range(300):
        result = service.jobs.get(w, job['id'])
        if result['status'] not in ('queued','running'): break
        time.sleep(.02)
    assert result['status'] == 'completed', result
    return result['result']


def test_text_source_slices_and_target(tmp_path):
    service = Service(tmp_path/'work', [tmp_path])
    w = service.store.create('lecture', text='# Membrane\n\nObjectives\n1. Identify ions\n\nSodium crosses channels.\n')
    result = wait(service, w['id'], service.extract_source(w['id']))
    assert result['slide_count'] >= 1
    assert 'Sodium' in service.read_source(w['id'])['text']
    assert service.search_source(w['id'], 'sodium')['hits']
    assert service.resolve_target(filename='MED241_L006_membrane.txt')['confident']
    assert service.artifacts(w['id'])['artifacts']
    with pytest.raises(DomainError): service.read_artifact(w['id'], '../outside')
    service.close()


def test_pdf_and_occlusion(tmp_path):
    import pymupdf
    pdf = tmp_path/'lecture.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(); page.insert_text((70,70), 'Sodium crosses channels.'); doc.save(pdf)
    s = Service(tmp_path/'work', [tmp_path]); w = s.store.create('lecture', source_path=str(pdf))['id']
    wait(s,w,s.extract_source(w))
    image = s.get_page_image(w,1)['artifact']
    assert s.image_bytes(w,image).startswith(b'\x89PNG')
    im = tmp_path/'figure.png'; Image.new('RGB',(300,200),'white').save(im)
    artifact = s.import_image(w,str(im))['artifact']
    result = s.build_occlusion(w,artifact,[{'text':'Sodium','left':.1,'top':.1,'width':.2,'height':.1}])
    assert 'image-occlusion' in result['fields']['Occlusion']
    assert s.image_bytes(w,result['preview']).startswith(b'\x89PNG')
    assert pdf.read_bytes().startswith(b'%PDF')
    s.close()


def test_export_figures_ocr_and_meter(tmp_path):
    import pymupdf
    s=Service(tmp_path/'work',[tmp_path])
    pdf=tmp_path/'figure.pdf'
    with pymupdf.open() as doc:
        p=doc.new_page(width=400,height=300); p.insert_text((30,60),'Sodium',fontsize=26); doc.save(pdf)
    w=s.store.create('lecture',source_path=str(pdf))['id']
    exported=wait(s,w,s.export_figures(w,whole_page=True,zoom=2))
    artifact=exported['figures'][0]['artifact']
    result=wait(s,w,s.ocr_image(w,artifact,min_conf=0,min_len=1))
    assert 'regions' in s.store.read_json(w,result['artifact'])
    transcript=__import__('pathlib').Path(__file__).resolve().parents[1]/'fixtures/transcripts/clean.jsonl'
    copied=tmp_path/'clean.jsonl'; copied.write_bytes(transcript.read_bytes())
    assert s.measure_usage(w,str(copied))['format']=='claude_code'
    s.close()


def test_meter_cannot_follow_subagent_symlinks_outside_roots(tmp_path):
    from pathlib import Path
    safe=tmp_path/'safe'; safe.mkdir()
    outside=tmp_path/'outside'; outside.mkdir()
    fixture=Path(__file__).resolve().parents[1]/'fixtures/transcripts/clean.jsonl'
    main=safe/'clean.jsonl'; main.write_bytes(fixture.read_bytes())
    (outside/'agent-test.jsonl').write_bytes(fixture.read_bytes())
    (outside/'agent-test.meta.json').write_text('{"agentType":"review","isFork":false}')
    (safe/'clean').mkdir(); (safe/'clean/subagents').symlink_to(outside,target_is_directory=True)
    s=Service(tmp_path/'work',[safe]); w=s.store.create('cards')['id']
    with pytest.raises(DomainError): s.measure_usage(w,str(main))
    s.close()


def test_completed_source_extraction_is_reused(tmp_path,monkeypatch):
    import cards.extract
    s=Service(tmp_path/'work',[tmp_path]); w=s.store.create('lecture',text='# One\nFirst fact')['id']
    wait(s,w,s.extract_source(w))
    def no_reextract(args): raise AssertionError('Completed source should be cached')
    monkeypatch.setattr(cards.extract,'run',no_reextract)
    result=wait(s,w,s.extract_source(w))
    assert result['cached'] is True
    s.close()


def test_workspace_has_no_fake_build_json(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])
    w = s.store.create('lecture', text='# A\n\nSodium crosses channels.\n')['id']
    wait(s, w, s.extract_source(w))
    assert not list((tmp_path/'work').rglob('build.json'))
    s.close()
