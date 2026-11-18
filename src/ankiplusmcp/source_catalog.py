"""Detached source discovery snapshots; workspace locking is explicit at the seam."""
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import re
from typing import Literal
from .store import DomainError, digest

EXTRACTION = r'^(?:engine|extractions/[a-f0-9]{32}/engine)$'

@dataclass(frozen=True)
class SourceDataset:
    prefix: str
    data: dict
    labels_pending: bool
    objectives: tuple = ()

@dataclass(frozen=True)
class SourceSnapshot:
    source: dict | None
    active_prefix: str
    datasets: tuple[SourceDataset, ...]
    labels: dict[int, str] = field(default_factory=dict)
    pending_prefix: str | None = None
    pending_job: str | None = None

    @property
    def source_hash(self): return self.source['sha256'] if self.source else None
    @property
    def source_name(self): return self.source['name'] if self.source else None
    @property
    def location_kind(self) -> Literal['pdf_page', 'text_section'] | None:
        return ('pdf_page' if Path(self.source['path']).suffix.lower()=='.pdf' else 'text_section') if self.source else None

    def current(self, require_complete=False):
        for item in self.datasets:
            if item.prefix == self.active_prefix:
                if require_complete and item.labels_pending:
                    raise DomainError('LABELS_PENDING',f'Figure labels are still being read by job {self.pending_job}; wait for extraction completion.')
                return item
        raise DomainError('SOURCE','No current extraction is available.')

    def candidates(self, page, extraction=None):
        return [(d.prefix,s,d.labels_pending) for d in self.datasets if extraction is None or d.prefix==extraction
                for s in d.data['slides'] if s['n']==page]

    def available_pages(self):
        return {s['n'] for d in self.datasets for s in d.data['slides']} if self.datasets else None

    def page_label(self, page): return self.labels.get(page)

    def labels_pending_for(self, artifact):
        return bool(self.pending_prefix and PurePosixPath(self.pending_prefix) in PurePosixPath(artifact).parents)

class SourceCatalog:
    def __init__(self, store, jobs): self.store,self.jobs=store,jobs

    def pending_marker(self, workspace):
        try:
            marker=self.store.read_json(workspace,'source-partial.json')
            if re.fullmatch(EXTRACTION,marker['prefix']) and self.jobs.get(workspace,marker['job'])['status'] in ('queued','running'):
                self.store.path(workspace,marker['prefix'])
                return marker
        except (DomainError,KeyError,TypeError,OSError): pass
        self.store.path(workspace,'source-partial.json').unlink(missing_ok=True)
        return None

    def snapshot(self, workspace):
        with self.store.lock(workspace): return self.snapshot_locked(workspace)

    def snapshot_locked(self, workspace):
        state=self.store.get(workspace); source=state.get('source'); active=state.get('source_engine','engine')
        if source:
            try: valid=digest(Path(source['path']))==source['sha256']
            except OSError: valid=False
            if not valid: raise DomainError('SOURCE_CHANGED','Stored source snapshot changed.')
        result=[]; marker=self.pending_marker(workspace)
        published=self.store.path(workspace,active+'/source/slides.json').is_file()
        if not published and marker:
            active=marker['prefix']
            data=self.store.read_json(workspace,active+'/source/slides.partial.json')
            for slide in data['slides']:
                for figure in slide['figures']: figure['ocr_labels']=figure['repeated_labels']=None
            result.append(SourceDataset(active,data,True))
        root=self.store.directory(workspace)
        paths=[active+'/source/slides.json','engine/source/slides.json',
               *[p.relative_to(root).as_posix() for p in sorted((root/'extractions').glob('*/engine/source/slides.json'))]]
        seen={d.prefix for d in result}
        for path in paths:
            prefix=str(PurePosixPath(path).parent.parent)
            if prefix in seen or not re.fullmatch(EXTRACTION,prefix): continue
            try:
                publication=prefix+'/.publication.json'
                if self.store.path(workspace,publication).exists() and self.store.read_json(workspace,publication).get('status')!='published': continue
                data=self.store.read_json(workspace,path)
                if not source or data.get('source_sha256',source['sha256'] if prefix==active else None)!=source['sha256']: continue
                obj=prefix+'/source/objectives.json'
                objectives=tuple(self.store.read_json(workspace,obj)['objectives']) if self.store.path(workspace,obj).is_file() else ()
            except (DomainError,OSError): continue
            result.append(SourceDataset(prefix,data,False,objectives)); seen.add(prefix)
        result.sort(key=lambda d: (d.prefix != active, len(d.data['slides']), d.prefix))
        labels={}
        if source and Path(source['path']).suffix.lower()=='.pdf':
            import pymupdf
            with pymupdf.open(source['path']) as doc:
                labels={i+1:p.get_label() for i,p in enumerate(doc) if p.get_label()}
        return SourceSnapshot(source,active,tuple(result),labels,marker['prefix'] if marker else None,marker['job'] if marker else None)
