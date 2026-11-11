import json
from pathlib import Path
import pytest
from cards import extract as ex
from cards.extract import ocr

@pytest.fixture
def counted(monkeypatch):
    calls = []
    monkeypatch.setattr(ocr, 'extract', lambda path, **kw: calls.append(Path(path).name) or {'regions': [{'text': Path(path).read_text()}], 'repeated': {}})
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 5.5.4')
    return calls

def files(tmp_path, *contents):
    out = []
    for i, text in enumerate(contents):
        p = tmp_path/f'f{i}.png'; p.write_text(text); out.append(p)
    return out

def test_identical_figures_are_read_once(tmp_path, counted):
    a, b, c = files(tmp_path, 'same', 'same', 'other')
    result = ex.ocr_figures([a, b, c], workers=2)
    assert len(counted) == 2 and result[a] == result[b] and result[a] is not result[b] and result[c] != result[a]

def test_cache_hit_skips_ocr(tmp_path, counted):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    first = ocr.cached_extract(a, cache); second = ocr.cached_extract(a, cache)
    assert len(counted) == 1 and first == second

def test_corrupt_cache_entry_is_a_miss(tmp_path, counted):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache)
    entry = next(cache.iterdir()); entry.write_text('{"regions": [')
    assert ocr.cached_extract(a, cache)['regions'] and len(counted) == 2
    json.loads(entry.read_text())

def test_cache_key_follows_the_tesseract_version(tmp_path, counted, monkeypatch):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache)
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'tesseract 6.0.0')
    ocr.cached_extract(a, cache); assert len(counted) == 2

def test_cache_is_bounded(tmp_path, counted, monkeypatch):
    import os
    monkeypatch.setattr(ocr, 'CACHE_LIMIT', 3); cache = tmp_path/'cache'
    for p in files(tmp_path, *'abcde'):
        ocr.cached_extract(p, cache)
        for e in cache.iterdir(): os.utime(e, (1000, 1000))   # every entry has the same mtime
    assert len(list(cache.iterdir())) == 3

def test_cache_key_follows_the_ocr_code(tmp_path, counted, monkeypatch):
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache)
    monkeypatch.setattr(ocr, 'code_digest', lambda: 'different')
    ocr.cached_extract(a, cache); assert len(counted) == 2

def test_no_caching_when_tesseract_version_is_unknown(tmp_path, counted, monkeypatch):
    monkeypatch.setattr(ocr, 'tesseract_version', lambda: 'unknown')
    (a,) = files(tmp_path, 'x'); cache = tmp_path/'cache'
    ocr.cached_extract(a, cache); ocr.cached_extract(a, cache)
    assert len(counted) == 2 and (not cache.exists() or not list(cache.iterdir()))

def test_default_workers(monkeypatch):
    import os
    monkeypatch.setattr(os, 'cpu_count', lambda: 6); assert ex.default_workers() == 6
    monkeypatch.setattr(os, 'cpu_count', lambda: None); assert ex.default_workers() == 4
