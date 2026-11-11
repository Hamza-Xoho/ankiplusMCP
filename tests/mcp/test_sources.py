import json
import threading
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
    def no_reextract(*args,**kwargs): raise AssertionError('Completed source should be cached')
    monkeypatch.setattr(cards.extract,'extract_source',no_reextract)
    result=wait(s,w,s.extract_source(w))
    assert result['cached'] is True
    s.close()


def test_workspace_has_no_fake_build_json(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])
    w = s.store.create('lecture', text='# A\n\nSodium crosses channels.\n')['id']
    wait(s, w, s.extract_source(w))
    assert not list((tmp_path/'work').rglob('build.json'))
    s.close()


def gated(monkeypatch):
    from cards import extract
    real, started, release = extract.extract_source, threading.Event(), threading.Event()
    def slow(*args, **kwargs):
        if kwargs.get('on_progress'): kwargs['on_progress']('figures', 3, 10)
        started.set(); release.wait(10)
        if kwargs.get('should_cancel') and kwargs['should_cancel'](): raise extract.ExtractionCancelled()
        return real(*args, **kwargs)
    monkeypatch.setattr(extract, 'extract_source', slow)
    return started, release


def gated_text_ready(monkeypatch):
    from cards import extract
    real, started, release = extract.extract_source, threading.Event(), threading.Event()
    early = {'slide_count': 1, 'slides': [{'n': 1, 'title': 'A', 'text': 'Sodium crosses channels.', 'figures': [], 'flags': []}]}
    def slow(*args, **kwargs):
        kwargs['on_text_ready'](early)
        started.set(); release.wait(10)
        if kwargs.get('should_cancel') and kwargs['should_cancel'](): raise extract.ExtractionCancelled()
        return real(*args, **kwargs)
    monkeypatch.setattr(extract, 'extract_source', slow)
    return started, release


def lecture(tmp_path):
    s = Service(tmp_path/'work', [tmp_path])
    return s, s.store.create('lecture', text='# A\n\nSodium crosses channels.\n')['id']


def test_reads_do_not_wait_for_extraction(tmp_path, monkeypatch):
    started, release = gated(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    t = time.monotonic(); s.get_cards(w); assert time.monotonic() - t < 1
    assert s.jobs.get(w, job['id'])['progress'] == 'figures 3/10'
    release.set(); wait(s, w, job); s.close()


def test_cancel_mid_extraction_then_retry(tmp_path, monkeypatch):
    started, release = gated(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    s.jobs.cancel(w, job['id']); release.set()
    for _ in range(300):
        if s.jobs.get(w, job['id'])['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert s.jobs.get(w, job['id'])['status'] == 'cancelled'
    assert 'source_engine' not in s.store.get(w)
    release.set(); wait(s, w, s.extract_source(w)); assert 'Sodium' in s.read_source(w)['text']; s.close()


def test_source_changed_during_extraction_publishes_nothing(tmp_path, monkeypatch):
    from ankiplusmcp import sources
    s, w = lecture(tmp_path); real = sources.digest; calls = []
    def digest(path):          # the first check sees the real hash, the check at publish time does not
        calls.append(path)
        return real(path) if len(calls) == 1 else 'changed'
    monkeypatch.setattr(sources, 'digest', digest)
    job = s.extract_source(w)
    for _ in range(300):
        record = s.jobs.get(w, job['id'])
        if record['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert record['status'] == 'failed' and record['error']['code'] == 'SOURCE_CHANGED'
    assert 'source_engine' not in s.store.get(w); s.close()


def test_two_extractions_at_once_leave_one_complete_result(tmp_path):
    s, w = lecture(tmp_path)
    a, b = s.extract_source(w, slides='1'), s.extract_source(w)
    wait(s, w, a); wait(s, w, b)
    engine = s.store.get(w)['source_engine']
    assert s.store.read_json(w, engine + '/source/slides.json')['slide_count'] >= 1; s.close()


def test_second_workspace_reuses_ocr_results(tmp_path, monkeypatch):
    import io, pymupdf
    from cards.extract import ocr
    calls = []
    monkeypatch.setattr(ocr, 'extract', lambda path, **kw: calls.append(1) or {'regions': [], 'repeated': {}})
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 5.5.4')
    buf = io.BytesIO(); Image.new('RGB', (400, 300), 'white').save(buf, 'PNG')
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=960, height=540); page.insert_text((40, 40), 'Title')
        page.insert_image(pymupdf.Rect(100, 80, 860, 520), stream=buf.getvalue()); doc.save(pdf)
    s = Service(tmp_path/'work', [tmp_path])
    for _ in range(2):
        w = s.store.create('lecture', source_path=str(pdf))['id']
        wait(s, w, s.extract_source(w))
    assert len(calls) == 1
    assert s.store.list()['total'] == 2      # the cache folder is not a workspace
    s.close()


def test_source_is_readable_before_labels_finish(tmp_path, monkeypatch):
    started, release = gated_text_ready(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    early = s.read_source(w)
    assert 'Sodium' in early['text'] and early['labels_pending'] is True
    assert s.search_source(w, 'sodium')['labels_pending'] is True
    assert s.jobs.get(w, job['id'])['progress'].startswith('text ready')
    release.set(); wait(s, w, job)
    assert 'labels_pending' not in s.read_source(w)
    assert not s.store.path(w, 'source-partial.json').exists(); s.close()


def test_cancel_removes_the_partial_marker(tmp_path, monkeypatch):
    started, release = gated_text_ready(monkeypatch); s, w = lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    s.jobs.cancel(w, job['id']); release.set()
    for _ in range(300):
        if s.jobs.get(w, job['id'])['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert not s.store.path(w, 'source-partial.json').exists()
    with pytest.raises(DomainError): s.read_source(w)
    s.close()


def _dead_marker(s, w, job_id, record):
    s.store.write_json(w, 'early/source/slides.partial.json', {'slide_count': 1, 'slides': [
        {'n': 1, 'title': 'A', 'text': 'Sodium crosses channels.', 'figures': [], 'flags': []}]})
    s.store.write_json(w, 'source-partial.json', {'prefix': 'early', 'job': job_id})
    if record: s.store.write_json(w, f'jobs/{job_id}.json', record)


def test_marker_of_a_dead_job_is_ignored(tmp_path):
    s, w = lecture(tmp_path)
    _dead_marker(s, w, 'deadjob', {'id': 'deadjob', 'owner': 'nolease', 'operation': 'extract_source',
                                   'status': 'running', 'progress': 'text ready', 'cancel_requested': False})
    with pytest.raises(DomainError): s.read_source(w)
    assert not s.store.path(w, 'source-partial.json').exists()
    s.close()


def test_marker_of_an_unknown_job_is_ignored(tmp_path):
    s, w = lecture(tmp_path)
    _dead_marker(s, w, 'nosuchjob', None)
    with pytest.raises(DomainError): s.search_source(w, 'sodium')
    assert not s.store.path(w, 'source-partial.json').exists()
    s.close()


REGION = {'text': 'Sodium', 'conf': 90, 'left': .1, 'top': .1, 'width': .2, 'height': .1}


def figure_lecture(tmp_path):
    import io, pymupdf
    buf = io.BytesIO(); Image.new('RGB', (400, 300), 'white').save(buf, 'PNG')
    pdf = tmp_path/'lecture.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=960, height=540); page.insert_text((40, 40), 'Membrane transport')
        page.insert_image(pymupdf.Rect(100, 80, 860, 520), stream=buf.getvalue()); doc.save(pdf)
    s = Service(tmp_path/'work', [tmp_path])
    return s, s.store.create('lecture', source_path=str(pdf))['id']


def gated_ocr(monkeypatch, fail=False):
    """The real extractor, with OCR held until released (and optionally failing)."""
    from cards import extract
    started, release = threading.Event(), threading.Event()
    def slow(paths, **kwargs):
        started.set(); release.wait(10)
        if fail: raise RuntimeError('ocr broke')
        return {p: {'regions': [REGION], 'repeated': {}} for p in paths}
    monkeypatch.setattr(extract, 'ocr_figures', slow)
    return started, release


def test_map_and_figures_while_labels_pending(tmp_path, monkeypatch):
    started, release = gated_ocr(monkeypatch); s, w = figure_lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    marker = s.store.read_json(w, 'source-partial.json')
    map_path = marker['prefix'] + '/source/map.md'
    assert map_path in s.jobs.get(w, job['id'])['progress']
    early = s.read_artifact(w, map_path)
    assert early['labels_pending'] is True and 'labels pending' in early['text']
    listed = s.list_figures(w)
    assert listed['labels_pending'] is True and listed['figures'][0]['ocr_labels'] is None
    figure = s.get_figure(w, listed['figures'][0]['fig_id'])
    assert figure['labels_pending'] is True and figure['ocr_labels'] is None
    assert s.image_bytes(w, figure['artifact']).startswith(b'\x89PNG')
    assert s.image_bytes(w, s.get_page_image(w, 1)['artifact']).startswith(b'\x89PNG')
    s.save_cards(w, [{'id': 'a', 'fields': {'Text': '{{c1::Sodium}} crosses'}, 'source_ref': [1]}], s.store.get(w)['revision'])
    with pytest.raises(DomainError) as caught: s.check_cards(w, coverage=True)
    assert caught.value.code == 'LABELS_PENDING' and job['id'] in caught.value.message
    assert s.check_cards(w)['checked'] == 1          # checks that need no extraction still run
    release.set(); result = wait(s, w, job)
    assert result['map'] == map_path
    after = s.read_artifact(w, map_path)
    assert 'labels_pending' not in after and 'labels pending' not in after['text']
    listed = s.list_figures(w)
    assert 'labels_pending' not in listed and listed['figures'][0]['ocr_labels'] == [REGION]
    assert s.get_figure(w, listed['figures'][0]['fig_id'])['ocr_labels'] == [REGION]
    assert s.check_cards(w, coverage=True)['coverage'] is not None
    s.close()


def test_published_data_beats_the_marker(tmp_path, monkeypatch):
    started, release = gated_ocr(monkeypatch); release.set(); s, w = figure_lecture(tmp_path)
    wait(s, w, s.extract_source(w))
    published = s.store.get(w)['source_engine'] + '/source/map.md'
    _dead_marker(s, w, 'livejob', {'id': 'livejob', 'owner': s.jobs.owner, 'operation': 'extract_source',
                                   'status': 'running', 'progress': 'text ready', 'cancel_requested': False})
    listed = s.list_figures(w)
    assert 'labels_pending' not in listed and listed['figures'][0]['ocr_labels'] == [REGION]
    assert 'labels_pending' not in s.read_artifact(w, published)
    assert s.check_cards(w, coverage=True)['coverage'] is not None
    s.close()


def test_publish_compares_with_the_hash_that_was_read(tmp_path, monkeypatch):
    from pathlib import Path
    from ankiplusmcp.store import digest
    started, release = gated_ocr(monkeypatch); s, w = figure_lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    with s.store.edit(w) as state:        # the source and its recorded hash both move on mid-extraction
        path = Path(state['source']['path']); path.chmod(0o644); path.write_bytes(path.read_bytes() + b'\n%changed')
        state['source']['sha256'] = digest(path)
    release.set()
    for _ in range(300):
        record = s.jobs.get(w, job['id'])
        if record['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert record['status'] == 'failed' and record['error']['code'] == 'SOURCE_CHANGED'
    assert 'source_engine' not in s.store.get(w); s.close()


def test_failed_extraction_clears_the_marker(tmp_path, monkeypatch):
    started, release = gated_ocr(monkeypatch, fail=True); s, w = figure_lecture(tmp_path)
    job = s.extract_source(w); assert started.wait(5)
    assert s.store.path(w, 'source-partial.json').exists()
    release.set()
    for _ in range(300):
        record = s.jobs.get(w, job['id'])
        if record['status'] not in ('queued', 'running'): break
        time.sleep(.02)
    assert record['status'] == 'failed'
    assert not s.store.path(w, 'source-partial.json').exists()
    with pytest.raises(DomainError): s.list_figures(w)
    s.close()
