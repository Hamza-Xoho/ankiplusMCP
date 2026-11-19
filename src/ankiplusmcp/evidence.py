"""Resolve citations from retained source text; never ask a model to invent quotes."""
import re
from typing import Literal

from pydantic import Field

from .models import Model, Positive
from .store import DomainError
from .source_catalog import EXTRACTION



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
    extraction_status: str = 'recognized'
    labels_pending: bool = False
    source_accuracy_verified: Literal[False] = False


class EvidenceResolver:
    def __init__(self, catalog):
        self.catalog = catalog

    def resolve(self, workspace: str, refs: list[EvidenceRef]) -> list[SourceEvidence]:
        parsed = [EvidenceRef.model_validate(ref) for ref in refs]
        if len(parsed) > 20 or sum(len(ref.quote or '') for ref in parsed) > 24000:
            raise DomainError('LIMIT', 'Resolve at most 20 passages and 24,000 quotation characters at a time.')
        snapshot = self.catalog.snapshot(workspace)
        if not snapshot.source:
            raise DomainError('SOURCE', 'This workspace has no source; no citation was invented.')
        result = []
        for ref in parsed:
            if ref.source_hash != snapshot.source_hash:
                raise DomainError('SOURCE_CHANGED', 'Citation refers to a different source version.')
            candidates = snapshot.candidates(ref.page, ref.extraction)
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
            result.append(SourceEvidence(
                source_hash=snapshot.source_hash, source_name=snapshot.source_name, page=ref.page,
                page_label=snapshot.page_label(ref.page), location_kind=snapshot.location_kind, extraction=prefix,
                extraction_status=page.get('extraction_status','recognized'), title=page.get('title', '')[:500], quote=quote, start=start, end=end,
                extraction_origin='ocr' if 'scan' in page.get('flags', []) else 'text', labels_pending=pending))
        return result
