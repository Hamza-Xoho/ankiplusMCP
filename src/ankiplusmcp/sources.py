"""Independent source and figure operations adapting the deterministic toolkit."""
import html
from pathlib import Path
from types import SimpleNamespace
import uuid
from cards.common.paths import Build
from cards.common.source_data import selection
from .store import DomainError, digest

class Sources:
    def engine(self, workspace):
        return self.store.get(workspace).get("source_engine", "engine")

    def extract_source(self, workspace, slides=None):
        manifest = self.store.get(workspace)
        if not manifest['source']: raise DomainError('SOURCE', 'Workspace has no source.', 'Create a lecture workspace with a source or pasted text.')
        def run(cancel):
            from cards import extract
            with self.store.edit(workspace) as state:
                if cancel(): raise DomainError('CANCELLED','Cancelled.')
                path = Path(state['source']['path'])
                if digest(path) != state['source']['sha256']: raise DomainError('SOURCE_CHANGED','Source snapshot changed.')
                previous=state.get('source_engine')
                if previous and self.store.path(workspace,previous+'/source/slides.json').is_file():
                    cached=self.store.read_json(workspace,previous+'/source/slides.json')
                    required=['map.md','objectives.json','slides_summary.json']+[f['file'] for slide in cached.get('slides',[]) for f in slide.get('figures',[])]
                    if (cached.get('source_sha256')==state['source']['sha256'] and cached.get('selection')==slides
                            and cached.get('cache_version')==extract.CACHE_VERSION
                            and all(self.store.path(workspace,previous+'/source/'+name).is_file() for name in required)):
                        return {'_committed':True,'cached':True,'slide_count':cached['slide_count'],
                                'map':previous+'/source/map.md','summary':previous+'/source/slides_summary.json'}
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
                self.store.write_json(workspace,prefix+'/build.json',{'source':{'path':str(path),'sha256':state['source']['sha256'],'kind':'pdf' if path.suffix=='.pdf' else 'text'}})
                extract.run(SimpleNamespace(build=str(self.store.path(workspace,prefix)), slides=slides))
                if cancel(): raise DomainError('CANCELLED','Cancelled after extraction; cached artifacts may remain.')
                data = self.store.read_json(workspace,prefix+'/source/slides.json')
                state['source_engine']=prefix
                return {'_committed':True,'slide_count':data['slide_count'], 'map':prefix+'/source/map.md', 'summary':prefix+'/source/slides_summary.json'}
        return self.jobs.submit(workspace,'extract_source',run)

    def read_source(self, workspace, slides=None, offset=0, limit=12000):
        from cards.source import slice_text
        data = self.store.read_json(workspace,self.engine(workspace)+'/source/slides.json')
        numbers = selection(slides,[s['n'] for s in data['slides']])
        text = slice_text(data,numbers)
        return {'text':text[offset:offset+limit], 'total_chars':len(text), 'slides':numbers,
                'next_offset':offset+limit if offset+limit<len(text) else None}

    def search_source(self, workspace, query, offset=0, limit=20):
        data = self.store.read_json(workspace,self.engine(workspace)+'/source/slides.json')
        hits = [{'slide':s['n'],'text':line} for s in data['slides'] for line in s['text'].splitlines() if query.casefold() in line.casefold()]
        return {'hits':hits[offset:offset+limit], 'total':len(hits), 'next_offset':offset+limit if offset+limit<len(hits) else None}

    def get_page_image(self, workspace, page):
        from cards import source
        with self.store.edit(workspace):
            prefix=self.engine(workspace)
            source.run(SimpleNamespace(build=str(self.store.path(workspace,prefix)),page_image=page))
        return {'artifact':f'{prefix}/source/pages/p{page:02d}.png'}

    def list_figures(self, workspace, offset=0, limit=20):
        prefix=self.engine(workspace)
        data = self.store.read_json(workspace,prefix+'/source/slides.json')
        figures = [dict(f,slide=s['n'],artifact=prefix+'/source/'+f['file']) for s in data['slides'] for f in s['figures']]
        return {'figures':figures[offset:offset+limit], 'total':len(figures), 'next_offset':offset+limit if offset+limit<len(figures) else None}

    def get_figure(self, workspace, figure_id):
        prefix=self.engine(workspace)
        data = self.store.read_json(workspace,prefix+'/source/slides.json')
        for slide in data['slides']:
            for figure in slide['figures']:
                if figure['fig_id'] == figure_id: return dict(figure,slide=slide['n'],artifact=prefix+'/source/'+figure['file'])
        raise DomainError('FIGURE','Unknown figure ID.','Use list_figures.')

    def import_image(self, workspace, path):
        with self.store.edit(workspace): artifact = self.store.import_file(workspace,path)
        return {'artifact':artifact}

    def ocr_image(self, workspace, artifact, min_conf=20, min_len=2, group=True, pad=.004):
        self.image_bytes(workspace,artifact)  # verify image and size before OCR
        def run(cancel):
            from cards.extract.ocr import extract
            with self.store.edit(workspace):
                if cancel(): raise DomainError('CANCELLED','Cancelled.')
                result = extract(self.store.path(workspace,artifact),min_conf=min_conf,min_len=min_len,group=group,pad=pad)
                name = f'ocr/{uuid.uuid4().hex}.json'; self.store.write_json(workspace,name,result)
                return {'artifact':name, 'region_count':len(result['regions'])}
        return self.jobs.submit(workspace,'ocr_image',run)

    def build_occlusion(self, workspace, artifact, regions, mode='one', keep=None):
        from PIL import Image
        from cards.figures import _regions, _occlusion, _images
        if mode not in ('one','all'): raise DomainError('MODE','Use one or all.')
        self.image_bytes(workspace,artifact)
        parsed = _regions(regions,','.join(map(str,keep)) if keep is not None else None)
        if not parsed: raise DomainError('REGIONS','Supply at least one region.')
        with self.store.edit(workspace):
            ident = uuid.uuid4().hex
            media, preview = f'media/{ident}.png',f'media/{ident}_preview.png'
            self.store.path(workspace,media).parent.mkdir(exist_ok=True)
            with Image.open(self.store.path(workspace,artifact)) as im:
                _images(im.convert('RGB'),parsed,self.store.path(workspace,media),self.store.path(workspace,preview))
            result = {'fields':{'Image':f'<img src="{ident}.png">','Occlusion':_occlusion(parsed,mode)},
                      'media':[{'path':media,'filename':ident+'.png'}], 'preview':preview, 'regions':parsed}
            self.store.write_json(workspace,f'occlusions/{ident}.json',result)
        return result

    def resolve_target(self, filename='', course=None, number=None, title=None, subject=None, system=None, existing_decks=None, legacy=False):
        from cards import target
        if course is not None and number is not None and title:
            result = dict(target.build(course,number,title,subject,system),confident=True)
        else: result = target.parse(filename,subject,system)
        if result.get('confident'):
            if legacy: result['deck']=f'{result["course"]}::{result["number"]}. {result["topic"]}'
            result['create_deck'] = result['deck'] not in (existing_decks or [])
        return result

    def export_figures(self, workspace, pages=None, zoom=4, min_frac=.05, whole_page=False):
        source=self.store.get(workspace)['source']
        if not source or Path(source['path']).suffix!='.pdf': raise DomainError('SOURCE','Figure export requires a PDF.')
        def run(cancel):
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
