from pathlib import Path
from threading import Event
import pytest
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_evidence import setup_source
from test_sources import wait


def test_retained_chapter_catalog(tmp_path):
    s, w, _ = setup_source(tmp_path)
    try:
        wait(s,w,s.extract_source(w,'1'))
        first=s.source_catalog.snapshot(w).current()
        wait(s,w,s.extract_source(w,'2'))
        snapshot=s.source_catalog.snapshot(w)
        assert snapshot.current().prefix != first.prefix
        assert snapshot.candidates(1,first.prefix)[0][0] == first.prefix
        assert snapshot.available_pages() == {1,2}
    finally: s.close()


def test_catalog_excludes_foreign_or_escaping_extractions(tmp_path):
    s,w,_=setup_source(tmp_path)
    try:
        prefix='extractions/'+'f'*32+'/engine'
        s.store.write_json(w,prefix+'/source/slides.json',{'source_sha256':'0'*64,'slides':[]})
        outside=tmp_path/'outside'; outside.mkdir()
        (s.store.directory(w)/'extractions'/('a'*32)).symlink_to(outside,target_is_directory=True)
        snapshot=s.source_catalog.snapshot(w)
        assert [d.prefix for d in snapshot.datasets] == [snapshot.active_prefix]
    finally: s.close()


def test_cards_only_catalog(tmp_path):
    s=Service(tmp_path/'data',[tmp_path])
    try:
        w=s.store.create('cards')['id']
        assert s.source_catalog.snapshot(w).available_pages() is None
    finally: s.close()


def partial(s,w,job):
    prefix='extractions/'+'b'*32+'/engine'
    s.store.write_json(w,prefix+'/source/slides.partial.json',{'slides':[{'n':1,'text':'early','figures':[{'ocr_labels':[],'repeated_labels':[]}]}]})
    s.store.write_json(w,'source-partial.json',{'prefix':prefix,'job':job})


def test_live_partial_labels(tmp_path):
    s=Service(tmp_path/'data',[tmp_path]); gate=Event()
    try:
        w=s.store.create('lecture',text='# First\nText')['id']
        job=s.jobs.submit(w,'test',lambda cancel,report: (gate.wait(5) or {}))
        partial(s,w,job['id'])
        snapshot=s.source_catalog.snapshot(w)
        assert snapshot.current().labels_pending
        figure=snapshot.current().data['slides'][0]['figures'][0]
        assert figure['ocr_labels'] is None and figure['repeated_labels'] is None
        with pytest.raises(DomainError,match='LABELS_PENDING'): snapshot.current(require_complete=True)
    finally: gate.set(); s.close()


def test_interrupted_partial_is_not_current(tmp_path):
    s=Service(tmp_path/'data',[tmp_path])
    try:
        w=s.store.create('lecture',text='# First\nText')['id']; partial(s,w,'missing')
        with pytest.raises(DomainError): s.source_catalog.snapshot(w).current()
    finally: s.close()


def test_physical_and_printed_page_labels(tmp_path):
    import pymupdf
    p=tmp_path/'book.pdf'
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50,50),'Fibroblast has basophilic cytoplasm and oval nucleus.')
        doc.set_page_labels([{'startpage':0,'prefix':'','style':'r','firstpagenum':7}]); doc.save(p)
    s=Service(tmp_path/'data',[tmp_path])
    try:
        w=s.store.create('lecture',source_path=str(p))['id']; wait(s,w,s.extract_source(w))
        assert s.source_catalog.snapshot(w).page_label(1)=='vii'
    finally: s.close()


def test_changed_source_refuses_catalog(tmp_path):
    s,w,_=setup_source(tmp_path)
    try:
        path=Path(s.store.get(w)['source']['path']); path.chmod(0o600); path.write_text('changed')
        with pytest.raises(DomainError,match='SOURCE_CHANGED'): s.source_catalog.snapshot(w)
    finally: s.close()


def test_overlapping_extractions_keep_other_partial_marker(tmp_path,monkeypatch):
    from cards import extract
    from threading import Event
    s=Service(tmp_path/'data',[tmp_path]); first=Event();second=Event();release1=Event();release2=Event()
    original=extract.extract_source
    def paused(*a,**kw):
        ready=kw['on_text_ready']; number=a[2]
        def callback(data):
            ready(data); (first if number=='1' else second).set()
            assert (release1 if number=='1' else release2).wait(4)
        kw['on_text_ready']=callback
        return original(*a,**kw)
    monkeypatch.setattr(extract,'extract_source',paused)
    try:
        w=s.store.create('lecture',text='# First\nOne\n\n# Second\nTwo')['id']
        a=s.extract_source(w,'1'); assert first.wait(2)
        b=s.extract_source(w,'2'); assert second.wait(2)
        marker=s.store.read_json(w,'source-partial.json'); assert marker['job']==b['id']
        release1.set(); wait(s,w,a)
        assert s.store.read_json(w,'source-partial.json')==marker
        release2.set(); wait(s,w,b)
    finally: release1.set(); release2.set(); s.close()
