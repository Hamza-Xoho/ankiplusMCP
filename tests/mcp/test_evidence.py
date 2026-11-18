import pytest

from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def setup_source(tmp_path):
    s = Service(tmp_path / 'work', [tmp_path])
    w = s.store.create('lecture', text='# Fibroblast\nFlat branched cell, with basophilic cytoplasm.\nOval nucleus prominent nucleolus.\n\n# Function\nFormation of fibres.')['id']
    wait(s, w, s.extract_source(w))
    return s, w, s.store.get(w)['source']['sha256']


def test_evidence_returns_actual_quote_with_source_identity_and_section(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        evidence = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1, quote='Flat branched cell, with basophilic cytoplasm.')])[0]
        assert evidence.quote == 'Flat branched cell, with basophilic cytoplasm.'
        assert evidence.page == 1
        assert evidence.source_hash == sha
        assert evidence.location_kind == 'text_section'
        assert evidence.extraction_origin == 'text'
        assert evidence.source_accuracy_verified is False
    finally:
        s.close()


def test_unsupported_quote_wrong_page_and_changed_source_are_refused(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        resolver = EvidenceResolver(s.source_catalog)
        for reference in [EvidenceRef(source_hash=sha, page=1, quote='Invented scientific fact'),
                          EvidenceRef(source_hash=sha, page=99, quote='Fibroblast'),
                          EvidenceRef(source_hash='f' * 64, page=1, quote='Fibroblast')]:
            with pytest.raises(DomainError):
                resolver.resolve(w, [reference])
    finally:
        s.close()


def test_whitespace_tolerant_quote_is_returned_from_original_text(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        quote = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1, quote='basophilic   cytoplasm.\nOval nucleus')])[0].quote
        assert quote == 'basophilic cytoplasm.\nOval nucleus'
    finally:
        s.close()


def test_multiple_passages_remain_separate_and_ocr_is_labelled(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        prefix, data, _ = s.source_data(w)
        data['slides'][0]['flags'] = ['scan', 'image_only']
        s.store.write_json(w, prefix + '/source/slides.json', data)
        result = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1, quote='basophilic cytoplasm'),
                                                 EvidenceRef(source_hash=sha, page=2, quote='Formation of fibres.')])
        assert len(result) == 2
        assert result[0].extraction_origin == 'ocr'
        assert result[1].page == 2
    finally:
        s.close()


def test_figure_only_reference_does_not_invent_a_quote(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        result = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1)])[0]
        assert result.quote is None
        assert result.title == 'Fibroblast'
    finally:
        s.close()


def test_pdf_page_and_printed_label_are_distinct(tmp_path):
    import pymupdf
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    source = tmp_path / 'book.pdf'
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 50), 'Fibroblast has basophilic cytoplasm and an oval nucleus.')
    document.set_page_labels([{'startpage': 0, 'prefix': '', 'style': 'r', 'firstpagenum': 7}])
    document.save(source)
    document.close()
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        workspace = s.store.create('lecture', source_path=str(source))['id']
        wait(s, workspace, s.extract_source(workspace))
        sha = s.store.get(workspace)['source']['sha256']
        evidence = EvidenceResolver(s.source_catalog).resolve(workspace, [EvidenceRef(source_hash=sha, page=1, quote='basophilic cytoplasm')])[0]
        assert evidence.page == 1
        assert evidence.page_label == 'vii'
        assert evidence.location_kind == 'pdf_page'
    finally:
        s.close()


def test_invalid_draft_source_reference_is_flagged_when_extraction_exists(tmp_path):
    s, w, sha = setup_source(tmp_path)
    try:
        s.save_cards(w, [{'id': 'n1', 'fields': {'Text': '{{c1::Fibroblast}}'}, 'source_ref': [99]}], 0)
        findings = s.check_cards(w)['findings']
        assert any(f['code'] == 'SOURCE_REF' and f['severity'] == 'blocker' for f in findings)
    finally:
        s.close()


def test_reviewer_rejection_is_not_reported_as_covered_material(tmp_path):
    s, w, sha = setup_source(tmp_path)
    try:
        s.save_cards(w, [{'id': 'n1', 'fields': {'Text': '{{c1::Fibroblast}}'}, 'source_ref': [1]}], 0)
        s.save_omissions(w, [{'slide': 2, 'reason': 'rejected_in_review', 'note_id': 'rejected'}], 1)
        result = s.check_cards(w, coverage=True)
        assert result['coverage']['slides_uncovered'] == [2]
        assert result['coverage']['review_rejected_omissions'][0]['slide'] == 2
        assert result['blockers'] == 0, 'coverage reporting must not silently change warning/blocker policy'
    finally:
        s.close()


def test_earlier_chapter_evidence_and_card_refs_survive_later_extraction(tmp_path):
    from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
    s, w, sha = setup_source(tmp_path)
    try:
        wait(s, w, s.extract_source(w, '1'))
        original = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1, quote='basophilic cytoplasm')])[0]
        s.save_cards(w, [{'id': 'n1', 'fields': {'Text': '{{c1::Fibroblast}}'}, 'source_ref': [1]}], 0)
        wait(s, w, s.extract_source(w, '2'))
        revisited = EvidenceResolver(s.source_catalog).resolve(w, [EvidenceRef(source_hash=sha, page=1, quote='basophilic cytoplasm')])[0]
        assert revisited.quote == original.quote
        assert revisited.extraction == original.extraction
        assert not any(f['code'] == 'SOURCE_REF' for f in s.check_cards(w)['findings'])
    finally:
        s.close()


def test_original_pdf_page_can_be_viewed_after_switching_chapters(tmp_path):
    import pymupdf
    document = pymupdf.open()
    for text in ['Chapter one fibroblast basophilic cytoplasm oval nucleus.', 'Chapter two collagen fibres and connective tissue.']:
        page = document.new_page()
        page.insert_text((50, 50), text)
    path = tmp_path / 'chapters.pdf'
    document.save(path)
    document.close()
    s = Service(tmp_path / 'work', [tmp_path])
    try:
        w = s.store.create('lecture', source_path=str(path))['id']
        wait(s, w, s.extract_source(w, '1'))
        first = s.get_page_image(w, 1)['artifact']
        original = s.image_bytes(w, first)
        wait(s, w, s.extract_source(w, '2'))
        revisited = s.get_page_image(w, 1)['artifact']
        assert s.image_bytes(w, revisited) == original
    finally:
        s.close()
