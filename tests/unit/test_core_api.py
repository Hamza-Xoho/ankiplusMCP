def test_public_names_are_the_private_ones():
    from cards.common import files
    from cards import figures
    assert files._write is files.atomic_write
    assert figures._regions is figures.parse_regions
    assert figures._occlusion is figures.occlusion_markup
    assert figures._images is figures.write_images


def test_lint_tag_root():
    from cards.check.lint import lint
    note = {'id': 'n001', 'fields': {'Text': '{{c1::Sodium}} crosses', 'Extra': ''}, 'tags': ['#AnkiPlus::T']}
    codes = lambda **kw: {f['code'] for f in lint(note, **kw)}
    assert 'L10' in codes()
    assert 'L10' not in codes(tag_root='#AnkiPlus')
    assert 'L10' in {f['code'] for f in lint({**note, 'tags': ['#AnkiPlusX::T']}, tag_root='#AnkiPlus')}


def test_extract_source_needs_no_build_json(tmp_path):
    from cards.extract import extract_source
    src = tmp_path/'notes.md'; src.write_text('# Membrane\n\nSodium crosses channels.\n')
    out = tmp_path/'out'
    first = extract_source(src, out)
    assert first.slide_count >= 1 and not first.cached and first.map == out/'source/map.md'
    assert (out/'source/slides.json').is_file() and not (out/'build.json').exists()
    assert extract_source(src, out).cached


def test_extract_source_cancel_leaves_no_manifest(tmp_path):
    import pytest
    from cards.extract import extract_source, ExtractionCancelled
    src = tmp_path/'notes.md'; src.write_text('# A\n\ntext\n')
    with pytest.raises(ExtractionCancelled):
        extract_source(src, tmp_path/'out', should_cancel=lambda: True)
    assert not (tmp_path/'out/source/slides.json').exists()


def test_extract_source_reports_figure_progress(tmp_path):
    import io, pymupdf
    from PIL import Image
    from cards.extract import extract_source
    buf = io.BytesIO(); Image.new('RGB', (400, 300), 'white').save(buf, 'PNG')
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc:
        page = doc.new_page(width=960, height=540); page.insert_text((40, 40), 'Title')
        page.insert_image(pymupdf.Rect(100, 80, 860, 520), stream=buf.getvalue()); doc.save(pdf)
    seen = []
    extract_source(pdf, tmp_path/'out', on_progress=lambda *event: seen.append(event))
    assert ('figures', 1, 1) in seen and ('slides', 1, None) in seen


def test_page_image(tmp_path):
    import pymupdf
    from PIL import Image
    from cards.source import page_image
    pdf = tmp_path/'l.pdf'
    with pymupdf.open() as doc: doc.new_page(width=960, height=540); doc.save(pdf)
    out = page_image(pdf, tmp_path/'p01.png', 1)
    with Image.open(out) as im: assert max(im.size) == 1000
