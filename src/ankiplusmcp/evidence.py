"""Resolve citations from retained source text; never ask a model to invent quotes."""
import re
from pathlib import Path
from typing import Literal

from pydantic import Field

from .models import Model, Positive
from .store import DomainError, digest

EXTRACTION = r'^(?:engine|extractions/[a-f0-9]{32}/engine)$'


class EvidenceRef(Model):
    source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    page: Positive
    quote: str | None = Field(default=None, min_length=1, max_length=6000)
    extraction: str | None = Field(default=None, pattern=EXTRACTION)


class SourceEvidence(Model):
    source_hash: str
    source_name: str
    page: Positive
    page_label: str | None = None
    location_kind: Literal['pdf_page', 'text_section']
    extraction: str
    title: str
    quote: str | None = None
    start: int | None = None
    end: int | None = None
    extraction_origin: Literal['text', 'ocr']
    labels_pending: bool = False
    source_accuracy_verified: Literal[False] = False


class EvidenceResolver:
    def __init__(self, service):
        self.service = service

    def datasets(self, workspace, source):
        """Immutable matching extractions, current first. Caller owns snapshot locking."""
        result = []
        try:
            prefix, data, pending = self.service.source_data(workspace)
            if data.get('source_sha256', source['sha256']) == source['sha256']:
                result.append((prefix, data, pending))
        except DomainError:
            pass
        root = self.service.store.directory(workspace)
        paths = [root / 'engine/source/slides.json', *sorted((root / 'extractions').glob('*/engine/source/slides.json'))]
        seen = {item[0] for item in result}
        for path in paths:
            prefix = path.parent.parent.relative_to(root).as_posix()
            if prefix in seen or not path.exists():
                continue
            if not re.fullmatch(EXTRACTION, prefix):
                continue
            # Resolve through Store so retained references cannot follow a
            # symlink outside this workspace.
            try:
                data = self.service.store.read_json(workspace, path.relative_to(root).as_posix())
            except DomainError:
                continue
            if data.get('source_sha256') == source['sha256']:
                result.append((prefix, data, False))
        return result

    def page_candidates(self, workspace, source, page, extraction=None):
        return [(prefix, slide, pending) for prefix, data, pending in self.datasets(workspace, source)
                if extraction is None or prefix == extraction
                for slide in data['slides'] if slide['n'] == page]

    def available_pages(self, workspace):
        source = self.service.store.get(workspace).get('source')
        if not source:
            return None
        datasets = self.datasets(workspace, source)
        return {page['n'] for _, data, _ in datasets for page in data['slides']} if datasets else None

    def resolve(self, workspace: str, refs: list[EvidenceRef]) -> list[SourceEvidence]:
        parsed = [EvidenceRef.model_validate(ref) for ref in refs]
        if len(parsed) > 20 or sum(len(ref.quote or '') for ref in parsed) > 24000:
            raise DomainError('LIMIT', 'Resolve at most 20 passages and 24,000 quotation characters at a time.')
        with self.service.store.lock(workspace):
            source = self.service.store.get(workspace).get('source')
            if not source:
                raise DomainError('SOURCE', 'This workspace has no source; no citation was invented.')
            if digest(Path(source['path'])) != source['sha256']:
                raise DomainError('SOURCE_CHANGED', 'Stored source snapshot changed.')
            datasets = self.datasets(workspace, source)
            is_pdf = Path(source['path']).suffix.lower() == '.pdf'
            result = []
            for ref in parsed:
                if ref.source_hash != source['sha256']:
                    raise DomainError('SOURCE_CHANGED', 'Citation refers to a different source version.')
                candidates = [(prefix, page, pending) for prefix, data, pending in datasets
                              if ref.extraction is None or prefix == ref.extraction
                              for page in data['slides'] if page['n'] == ref.page]
                found = None
                for prefix, page, pending in candidates:
                    quote, start, end = None, None, None
                    if ref.quote is not None:
                        words = ref.quote.split()
                        if not words:
                            raise DomainError('SOURCE_REF', 'A quote cannot contain only whitespace.')
                        match = re.search(r'\s+'.join(re.escape(word) for word in words), page['text'])
                        if match is None:
                            continue
                        start, end = match.span()
                        quote = page['text'][start:end]
                    found = (prefix, page, pending, quote, start, end)
                    break
                if found is None:
                    raise DomainError('SOURCE_REF', 'Citation page or quotation is absent from the retained matching extractions.')
                prefix, page, pending, quote, start, end = found
                label = None
                if is_pdf:
                    import pymupdf
                    with pymupdf.open(source['path']) as document:
                        label = document[ref.page - 1].get_label() or None
                result.append(SourceEvidence(
                    source_hash=source['sha256'], source_name=source['name'], page=ref.page,
                    page_label=label, location_kind='pdf_page' if is_pdf else 'text_section', extraction=prefix,
                    title=page.get('title', '')[:500], quote=quote, start=start, end=end,
                    extraction_origin='ocr' if 'scan' in page.get('flags', []) else 'text', labels_pending=pending))
            return result
