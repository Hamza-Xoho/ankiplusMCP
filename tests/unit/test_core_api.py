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
