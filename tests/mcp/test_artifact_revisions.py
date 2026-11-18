from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PIL import Image

from ankiplusmcp.service import Service
from test_sources import wait


def draft(text='{{c1::Nucleus}} stores DNA'):
    return {'id': 'n1', 'fields': {'Text': text}}


def test_importing_image_does_not_stale_a_card_edit(tmp_path):
    image = tmp_path / 'figure.png'
    Image.new('RGB', (20, 20), 'white').save(image)
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        s.save_cards(workspace, [draft()], 0)
        s.import_image(workspace, str(image))
        assert s.save_cards(workspace, [draft('{{c1::Membrane}} surrounds the cell')], 1)['revision'] == 2
        assert s.store.get(workspace)['artifact_revision'] == 1
    finally:
        s.close()


def test_native_render_does_not_block_reads_or_advance_card_revision(tmp_path, monkeypatch):
    from cards import render
    entered, release = Event(), Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return []
    monkeypatch.setattr(render, 'render_rows', delayed)
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        s.save_cards(workspace, [draft()], 0)
        job = s.render_cards(workspace)
        assert entered.wait(2)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(s.get_cards, workspace)
            try:
                assert future.result(timeout=.5)['revision'] == 1
            finally:
                release.set()
        wait(s, workspace, job)
        assert s.store.get(workspace)['revision'] == 1
        assert s.store.get(workspace)['artifact_revision'] == 1
    finally:
        release.set()
        s.close()


def test_changed_cards_cannot_receive_stale_render_publication(tmp_path, monkeypatch):
    from cards import render
    entered, release = Event(), Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return []
    monkeypatch.setattr(render, 'render_rows', delayed)
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        s.save_cards(workspace, [draft()], 0)
        job = s.render_cards(workspace)
        assert entered.wait(2)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(s.save_cards, workspace, [draft('{{c1::New}} content')], 1)
            try:
                assert future.result(timeout=.5)['revision'] == 2
            finally:
                release.set()
        import time
        for _ in range(100):
            status = s.jobs.get(workspace, job['id'])
            if status['status'] not in ('running', 'queued'):
                break
            time.sleep(.01)
        assert status['status'] == 'failed'
        assert not s.store.path(workspace, 'latest-preview.json').exists()
    finally:
        release.set()
        s.close()


def test_native_ocr_allows_reads_and_rejects_changed_input(tmp_path, monkeypatch):
    from cards.extract import ocr
    entered, release = Event(), Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return {'regions': []}
    monkeypatch.setattr(ocr, 'extract', delayed)
    image = tmp_path / 'figure.png'
    Image.new('RGB', (20, 20), 'white').save(image)
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        artifact = s.import_image(workspace, str(image))['artifact']
        job = s.ocr_image(workspace, artifact)
        assert entered.wait(2)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(s.get_cards, workspace)
            try:
                assert future.result(timeout=.5)['revision'] == 0
                Image.new('RGB', (20, 20), 'black').save(s.store.path(workspace, artifact))
            finally:
                release.set()
        import time
        for _ in range(100):
            status = s.jobs.get(workspace, job['id'])
            if status['status'] not in ('running', 'queued'):
                break
            time.sleep(.01)
        assert status['status'] == 'failed'
        assert s.store.get(workspace)['artifact_revision'] == 1
    finally:
        release.set()
        s.close()


def test_lock_contention_returns_retryable_busy(tmp_path):
    import pytest
    from ankiplusmcp.store import DomainError
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('cards')['id']
        with s.store.lock(workspace):
            with pytest.raises(DomainError) as error:
                with s.store.lock(workspace, timeout=.01):
                    raise AssertionError('contended lock was acquired')
        assert error.value.code == 'BUSY'
        assert 'retry' in error.value.remedy.lower()
    finally:
        s.close()


def test_rejected_page_render_does_not_overwrite_published_image(tmp_path, monkeypatch):
    import pytest
    from cards import source
    from ankiplusmcp.store import DomainError
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('lecture', text='# One\nAn original fact')['id']
        wait(s, workspace, s.extract_source(workspace))
        original = s.store.path(workspace, s.engine(workspace) + '/source/pages/p01.png')
        original.parent.mkdir(exist_ok=True)
        original.write_bytes(b'previous approved image')
        def stale_render(pdf, output, number):
            with s.store.edit(workspace) as state:
                state['source']['sha256'] = 'f' * 64
            output.write_bytes(b'stale replacement')
        monkeypatch.setattr(source, 'page_image', stale_render)
        with pytest.raises(DomainError, match='SOURCE_CHANGED'):
            s.get_page_image(workspace, 1)
        assert original.read_bytes() == b'previous approved image'
    finally:
        s.close()
