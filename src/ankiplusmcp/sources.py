"""Independent source and figure operations adapting the deterministic toolkit."""
import html
from pathlib import Path
from types import SimpleNamespace
import uuid
from cards.common.paths import Build
from cards.common.source_data import selection
from .store import DomainError, digest
from . import doctor

class Sources:
    def engine(self, workspace):
        return self.store.get(workspace).get("source_engine", "engine")

    def pending_marker(self, workspace):
        """The text-ready marker {'prefix','job'} while its job is queued or running, else None."""
        if not self.store.path(workspace,'source-partial.json').is_file(): return None
        try:
            marker=self.store.read_json(workspace,'source-partial.json')
            try: running=self.jobs.get(workspace,marker['job'])['status'] in ('queued','running')
            except DomainError: running=False
            if running and isinstance(marker['prefix'],str): return marker
            # Its job is gone (killed server, unknown id): behave as if no extraction had started.
            self.store.path(workspace,'source-partial.json').unlink(missing_ok=True)
        except (DomainError,KeyError,TypeError,OSError): pass
        return None

    def published(self, workspace):
        return self.store.path(workspace,self.engine(workspace)+'/source/slides.json').is_file()

    def source_data(self, workspace):
        """(prefix, slides data, labels_pending). A published extraction beats a text-ready marker."""
        prefix=self.engine(workspace)
        marker=None if self.published(workspace) else self.pending_marker(workspace)
        if marker:
            data=self.store.read_json(workspace,marker['prefix']+'/source/slides.partial.json')
            for slide in data['slides']:
                for figure in slide['figures']:
                    figure['ocr_labels']=figure['repeated_labels']=None   # not read yet, unlike []: read, none found
            return marker['prefix'],data,True
        return prefix,self.store.read_json(workspace,prefix+'/source/slides.json'),False

    def require_extraction(self, workspace, needs):
        """Refuse, retryably, while only the early text exists and no finished extraction is published."""
        marker=None if self.published(workspace) else self.pending_marker(workspace)
        if marker:
            raise DomainError('LABELS_PENDING',f'Figure labels are still being read by job {marker["job"]}; {needs} needs the finished extraction.',
                              'Wait until get_job reports that job completed, then retry.')

    def extract_source(self, workspace, slides=None):
        manifest = self.store.get(workspace)
        if not manifest['source']: raise DomainError('SOURCE', 'Workspace has no source.', 'Create a lecture workspace with a source or pasted text.')
        def run(cancel, report):
            from cards import extract
            # 1. Under the lock: reuse a matching earlier extraction.
            with self.store.lock(workspace):
                state = self.store.get(workspace)
                path = Path(state['source']['path']); sha = state['source']['sha256']
                if cancel(): raise DomainError('CANCELLED','Cancelled.')
                if digest(path) != sha: raise DomainError('SOURCE_CHANGED','Source snapshot changed.')
                previous=state.get('source_engine')
                if previous and self.store.path(workspace,previous+'/source/slides.json').is_file():
                    cached=self.store.read_json(workspace,previous+'/source/slides.json')
                    required=['map.md','objectives.json','slides_summary.json']+[f['file'] for slide in cached.get('slides',[]) for f in slide.get('figures',[])]
                    if (cached.get('source_sha256')==sha and cached.get('selection')==slides
                            and cached.get('cache_version')==extract.CACHE_VERSION
                            and all(self.store.path(workspace,previous+'/source/'+name).is_file() for name in required)):
                        return {'_committed':True,'cached':True,'slide_count':cached['slide_count'],
                                'map':previous+'/source/map.md','summary':previous+'/source/slides_summary.json'}
            # 2. No lock: limits, then the slow extraction into a fresh folder.
            if path.suffix=='.pdf':
                import pymupdf
                with pymupdf.open(path) as pdf:
                    if len(pdf)>500: raise DomainError('LIMIT','PDF exceeds 500 pages; split the source.')
                    for page in pdf:
                        if page.rect.width*page.rect.height*16>20_000_000 or max(page.rect.width,page.rect.height)*4>32000:
                            raise DomainError('LIMIT','PDF page exceeds safe 4x raster limits.','Resize the PDF pages before extraction.')
                        for info in page.get_image_info():
                            if info.get('width',0)*info.get('height',0)>20_000_000:
                                raise DomainError('LIMIT','Embedded PDF image exceeds 20 million pixels.')
            prefix=f'extractions/{uuid.uuid4().hex}/engine'
            ready=[]
            # The core has already written the early map (figures marked "labels pending") when text_ready runs.
            early=f'text ready; map readable now at {prefix}/source/map.md; '
            def progress(kind, done, total):
                report(f'slides {done}' if kind=='slides' else (early if ready else '')+f'figures {done}/{total}')
            def text_ready(data):
                # The marker is not a revision: it only lets reads answer from the early text.
                self.store.write_json(workspace,prefix+'/source/slides.partial.json',data)
                self.store.write_json(workspace,'source-partial.json',{'prefix':prefix,'job':getattr(report,'job',None)})
                ready.append(1)
                report(early+f'figures 0/{sum(len(slide["figures"]) for slide in data["slides"])}')
            def clear_marker():
                # Compare-then-remove is not atomic: the worst case is losing a concurrent run's early text, never serving stale data.
                try:
                    if self.store.read_json(workspace,'source-partial.json').get('prefix')==prefix:
                        self.store.path(workspace,'source-partial.json').unlink(missing_ok=True)
                except (DomainError,OSError): pass
            try:
                try: extract.extract_source(path, self.store.path(workspace,prefix), slides, on_progress=progress, should_cancel=cancel, ocr_cache=self.store.root/'.cache'/'ocr', on_text_ready=text_ready)
                except extract.ExtractionCancelled as exc: raise DomainError('CANCELLED','Cancelled.') from exc
                except Exception as exc:
                    # The extractor reports a missing OCR program as its own E24; name the fix instead.
                    if getattr(exc,'code',None)=='E24' and not doctor.have('tesseract'): doctor.require('tesseract')
                    raise
                # 3. Publish: the source must be the one we read.
                with self.store.edit(workspace) as state:
                    if cancel(): raise DomainError('CANCELLED','Cancelled after extraction; cached artifacts may remain.')
                    # Compare with the hash phase 1 checked: that is the file the extractor read.
                    if digest(Path(state['source']['path'])) != sha: raise DomainError('SOURCE_CHANGED','Source snapshot changed.')
                    data = self.store.read_json(workspace,prefix+'/source/slides.json')
                    state['source_engine']=prefix
            finally: clear_marker()
            return {'_committed':True,'slide_count':data['slide_count'], 'map':prefix+'/source/map.md', 'summary':prefix+'/source/slides_summary.json'}
        return self.jobs.submit(workspace,'extract_source',run)

    def read_source(self, workspace, slides=None, offset=0, limit=12000):
        from cards.source import slice_text
        _, data, pending = self.source_data(workspace)
        numbers = selection(slides,[s['n'] for s in data['slides']])
        text = slice_text(data,numbers)
        return {'text':text[offset:offset+limit], 'total_chars':len(text), 'slides':numbers,
                'next_offset':offset+limit if offset+limit<len(text) else None, **({'labels_pending':True} if pending else {})}

    def search_source(self, workspace, query, offset=0, limit=20):
        _, data, pending = self.source_data(workspace)
        hits = [{'slide':s['n'],'text':line} for s in data['slides'] for line in s['text'].splitlines() if query.casefold() in line.casefold()]
        return {'hits':hits[offset:offset+limit], 'total':len(hits), 'next_offset':offset+limit if offset+limit<len(hits) else None, **({'labels_pending':True} if pending else {})}

    def get_page_image(self, workspace, page):
        from cards.source import page_image
        with self.store.edit(workspace) as state:
            # Pages depend only on the PDF, so the early text's folder serves while labels are pending.
            prefix, data, _ = self.source_data(workspace)
            selection(str(page),[s['n'] for s in data['slides']])
            page_image(Path(state['source']['path']),self.store.path(workspace,f'{prefix}/source/pages/p{page:02d}.png'),page)
        return {'artifact':f'{prefix}/source/pages/p{page:02d}.png'}

    def labels_pending_for(self, workspace, artifact):
        """True when `artifact` lies in an extraction whose figure labels are still being read."""
        marker=self.pending_marker(workspace)
        return bool(marker) and self.store.path(workspace,marker['prefix']) in self.store.path(workspace,artifact).parents

    def list_figures(self, workspace, offset=0, limit=20):
        prefix, data, pending = self.source_data(workspace)
        figures = [dict(f,slide=s['n'],artifact=prefix+'/source/'+f['file']) for s in data['slides'] for f in s['figures']]
        return {'figures':figures[offset:offset+limit], 'total':len(figures), 'next_offset':offset+limit if offset+limit<len(figures) else None, **({'labels_pending':True} if pending else {})}

    def get_figure(self, workspace, figure_id):
        prefix, data, pending = self.source_data(workspace)
        for slide in data['slides']:
            for figure in slide['figures']:
                if figure['fig_id'] == figure_id: return dict(figure,slide=slide['n'],artifact=prefix+'/source/'+figure['file'],**({'labels_pending':True} if pending else {}))
        raise DomainError('FIGURE','Unknown figure ID.','Use list_figures.')

    def import_image(self, workspace, path):
        with self.store.edit(workspace): artifact = self.store.import_file(workspace,path)
        return {'artifact':artifact}

    def ocr_image(self, workspace, artifact, min_conf=20, min_len=2, group=True, pad=.004):
        doctor.require('tesseract')
        self.image_bytes(workspace,artifact)  # verify image and size before OCR
        def run(cancel, report):
            from cards.extract.ocr import extract
            with self.store.edit(workspace):
                if cancel(): raise DomainError('CANCELLED','Cancelled.')
                result = extract(self.store.path(workspace,artifact),min_conf=min_conf,min_len=min_len,group=group,pad=pad)
                name = f'ocr/{uuid.uuid4().hex}.json'; self.store.write_json(workspace,name,result)
                return {'artifact':name, 'region_count':len(result['regions'])}
        return self.jobs.submit(workspace,'ocr_image',run)

    def build_occlusion(self, workspace, artifact, regions, mode='one', keep=None):
        from PIL import Image
        from cards.figures import parse_regions, occlusion_markup, write_images
        if mode not in ('one','all'): raise DomainError('MODE','Use one or all.')
        self.image_bytes(workspace,artifact)
        parsed = parse_regions(regions,','.join(map(str,keep)) if keep is not None else None)
        if not parsed: raise DomainError('REGIONS','Supply at least one region.')
        with self.store.edit(workspace):
            ident = uuid.uuid4().hex
            media, preview = f'media/{ident}.png',f'media/{ident}_preview.png'
            self.store.path(workspace,media).parent.mkdir(exist_ok=True)
            with Image.open(self.store.path(workspace,artifact)) as im:
                write_images(im.convert('RGB'),parsed,self.store.path(workspace,media),self.store.path(workspace,preview))
            result = {'fields':{'Image':f'<img src="{ident}.png">','Occlusion':occlusion_markup(parsed,mode)},
                      'media':[{'path':media,'filename':ident+'.png'}], 'preview':preview, 'regions':parsed}
            self.store.write_json(workspace,f'occlusions/{ident}.json',result)
        return result

    def resolve_target(self, filename='', course=None, number=None, title=None, subject=None, system=None, existing_decks=None, legacy=False):
        from cards import target
        if course is not None and number is not None and title:
            result = dict(target.build(course,number,title,subject,system,self.profile.tag_root),confident=True)
        else: result = target.parse(filename,subject,system,self.profile.tag_root)
        result['note_type'] = self.profile.note_type
        if result.get('confident'):
            if legacy: result['deck']=f'{result["course"]}::{result["number"]}. {result["topic"]}'
            result['create_deck'] = result['deck'] not in (existing_decks or [])
        return result

    def export_figures(self, workspace, pages=None, zoom=4, min_frac=.05, whole_page=False):
        source=self.store.get(workspace)['source']
        if not source or Path(source['path']).suffix!='.pdf': raise DomainError('SOURCE','Figure export requires a PDF.')
        def run(cancel, report):
            import pymupdf
            with self.store.edit(workspace):
                prefix=f'exports/{uuid.uuid4().hex}'; figures=[]
                with pymupdf.open(source['path']) as doc:
                    if len(doc)>500: raise DomainError('LIMIT','PDF exceeds 500 pages.')
                    for number in selection(pages,list(range(1,len(doc)+1))):
                        if cancel(): raise DomainError('CANCELLED','Cancelled.')
                        page=doc[number-1]; area=max(1,abs(page.rect.get_area()))
                        rects=[page.rect] if whole_page else list({tuple(r):r for im in page.get_images(full=True) for r in page.get_image_rects(im[0]) if abs(r.get_area())/area>=min_frac}.values())
                        for index,rect in enumerate(sorted(rects,key=lambda r:-abs(r.get_area())),1):
                            if rect.width*rect.height*zoom**2>20_000_000: raise DomainError('LIMIT','Raster exceeds 20 million pixels.','Reduce zoom.')
                            relative=f'{prefix}/p{number:03d}_fig{index}.png'
                            path=self.store.path(workspace,relative); path.parent.mkdir(parents=True,exist_ok=True)
                            pix=page.get_pixmap(clip=rect,matrix=pymupdf.Matrix(zoom,zoom),alpha=False); pix.save(path)
                            figures.append({'artifact':relative,'slide':number,'width':pix.width,'height':pix.height})
                self.store.write_json(workspace,prefix+'/manifest.json',figures)
                return {'figures':figures,'manifest':prefix+'/manifest.json'}
        return self.jobs.submit(workspace,'export_figures',run)

    def measure_usage(self, workspace, transcript):
        # This diagnostic understands Claude Code only; never auto-search host histories.
        from cards import meter
        source=self.store.source(transcript)
        if source.suffix!='.jsonl': raise DomainError('TRANSCRIPT','Supply a Claude Code JSONL transcript.')
        for sub in source.with_suffix('').glob('subagents/agent-*.jsonl'):
            self.store.source(str(sub))
            self.store.source(str(sub.with_suffix('.meta.json')))
        with self.store.edit(workspace):
            prefix=f'usage/{uuid.uuid4().hex}'
            result=meter.run(SimpleNamespace(build=None,session=str(source),latest=None,out=str(self.store.path(workspace,prefix)),line=False))
        return {'format':'claude_code','summary':result.lines,'json':prefix+'/cost.json','markdown':prefix+'/cost.md'}
