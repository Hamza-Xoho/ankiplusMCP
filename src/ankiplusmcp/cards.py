"""Standalone card persistence, checks and previews; no mandatory lecture state."""
from pathlib import Path
from types import SimpleNamespace
import uuid
from .models import Card
from .store import DomainError, digest

class Cards:
    def _cards(self, workspace):
        path = self.store.path(workspace,'cards.json')
        return self.store.read_json(workspace,'cards.json') if path.exists() else []

    def _select(self, workspace, ids=None):
        cards = self._cards(workspace)
        if ids is not None:
            if not set(ids) <= {c['id'] for c in cards}: raise DomainError('CARD','Unknown card ID.','Use get_cards.')
            cards = [c for c in cards if c['id'] in ids]
        return cards

    def save_cards(self, workspace, cards, expected_revision):
        if not 1 <= len(cards) <= 500: raise DomainError('LIMIT','Save between 1 and 500 cards.')
        parsed = [Card.model_validate(c).model_dump() for c in cards]
        if len({c['id'] for c in parsed}) != len(parsed): raise DomainError('CARD','Duplicate card IDs.')
        with self.store.edit(workspace,expected_revision) as state:
            for card in parsed:
                for media in card['media']:
                    self.image_bytes(workspace,media['path'])
            self.store.write_json(workspace,'cards.json',parsed)
        return {'revision':state['revision'], 'saved':len(parsed)}

    def get_cards(self, workspace, ids=None, offset=0, limit=20):
        with self.store.lock(workspace):
            cards = self._select(workspace,ids)
            return {'cards':cards[offset:offset+limit], 'total':len(cards), 'revision':self.store.get(workspace)['revision'],
                    'next_offset':offset+limit if offset+limit<len(cards) else None}

    def save_omissions(self, workspace, omissions, expected_revision):
        if len(omissions)>500: raise DomainError('LIMIT','At most 500 omissions per workspace.')
        if any(not isinstance(o,dict) or type(o.get('slide')) is not int or o['slide']<1 or not isinstance(o.get('reason'),str) or not o['reason'] for o in omissions):
            raise DomainError('OMISSION','Each omission needs a positive slide number and a reason.')
        with self.store.edit(workspace,expected_revision) as state:
            self.store.write_json(workspace,'omissions.json',omissions)
        return {'revision':state['revision'],'saved':len(omissions)}

    def check_cards(self, workspace, ids=None, house_style=False, coverage=False):
        from cards.check.lint import lint, CLOZE
        cards = self._select(workspace,ids)
        findings=[]
        for card in cards:
            Card.model_validate(card)
            def finding(code,message,severity='blocker'):
                findings.append({'code':code,'card_id':card['id'],'message':message,'severity':severity})
            from .validation import cloze_errors, io_errors
            if card['kind']=='cloze':
                for message in cloze_errors(' '.join(card['fields'].values())):
                    finding('CLOZE',message)
            if card['kind']=='io':
                for message in io_errors(card['fields']):
                    finding('IO',message)
            if house_style:
                findings.extend(dict(f,card_id=card['id']) for f in lint(card))
        coverage_result=None
        if coverage:
            from cards.check.coverage import summarize
            data=self.store.read_json(workspace,self.engine(workspace)+'/source/slides.json')
            objectives=self.store.read_json(workspace,self.engine(workspace)+'/source/objectives.json')['objectives']
            skips=self.store.read_json(workspace,'omissions.json') if self.store.path(workspace,'omissions.json').exists() else []
            coverage_result,_=summarize(cards,skips,[s['n'] for s in data['slides']],objectives)
            for objective in coverage_result['objectives_without_t1']:
                findings.append({'code':'COVERAGE','severity':'warn','message':f'Objective {objective} has no tier-1 card.'})
        return {'findings':findings,'blockers':sum(f['severity']=='blocker' for f in findings),
                'coverage':coverage_result,'checked':len(cards),'house_style':house_style,
                'source_accuracy_verified':False}

    def render_cards(self, workspace, ids=None, front=None, back=None, css=None, per_sheet=8, desktop_sample=0, light=False):
        with self.store.lock(workspace):
            selected=self._select(workspace,ids)
            if not selected: raise DomainError('CARD','No cards to render.','Save cards first.')
            revision=self.store.get(workspace)['revision']
        def run(cancel):
            from cards import render
            from cards.render.templates import CLOZE, fill, page
            from cards.render.occlusion import bodies
            from cards.common.paths import Build
            with self.store.edit(workspace,revision) as state:
                if cancel(): raise DomainError('CANCELLED','Cancelled.')
                rows=[]
                for card in selected:
                    media={m['filename']:str(self.store.path(workspace,m['path'])) for m in card['media']}
                    b=Build(self.store.directory(workspace))
                    if card['question'] is not None:
                        pairs=[(card['id'],card['question'],card['answer'])]
                    elif card['kind']=='io':
                        fronts,answer=bodies(b,card['fields'],media)
                        pairs=[(f'{card["id"]}_c{n}',q,answer) for n,q in fronts]
                    else:
                        fields=card['fields']; names=list(fields)
                        primary=names[0]
                        if card['kind']=='cloze':
                            numbers=sorted({int(m[1]) for value in fields.values() for m in CLOZE.finditer(value)})
                            if not numbers: raise DomainError('CLOZE','No valid cloze to render.')
                            ft=front or '{{cloze:'+primary+'}}'
                            bt=back or ft+'<hr>'+('{{'+names[1]+'}}' if len(names)>1 else '')
                        else:
                            numbers=[1]; ft=front or '{{'+primary+'}}'; bt=back or '{{FrontSide}}<hr>'+('{{'+names[1]+'}}' if len(names)>1 else '')
                        pairs=[]
                        for n in numbers:
                            question=fill(ft,fields,card['tags'],n,'front')
                            answer=fill(bt,fields,card['tags'],n,'back',question)
                            pairs.append((f'{card["id"]}_c{n}',question,answer))
                    for ident,question,answer in pairs:
                        # Inline only validated workspace media before handing inert HTML to renderer.
                        cleaner=lambda content: page('',content,b,media).split("<div id='qa'>",1)[1].rsplit('</div></body>',1)[0]
                        rows.append({'id':ident,'question':cleaner(question),'answer':cleaner(answer)})
                prefix=f'previews/{uuid.uuid4().hex}'
                build=self.store.path(workspace,prefix); build.mkdir(parents=True)
                self.store.write_json(workspace,prefix+'/input.json',rows)
                from cards.common.files import _write
                _write(build/'input.jsonl',''.join(__import__('json').dumps(row)+'\n' for row in rows))
                if css is not None:
                    (build/'model').mkdir()
                    for name,body in [('front.html',''),('back.html',''),('style.css',css)]: _write(build/'model'/name,body)
                render.run(SimpleNamespace(build=str(build),anki_html='input.jsonl',only=None,per_sheet=per_sheet))
                if cancel(): raise DomainError('CANCELLED','Cancelled; previews not marked current.')
                manifest=self.store.read_json(workspace,prefix+'/renders/sheets.json')
                sheets=[dict(sheet,**{side:str(Path(sheet[side]).relative_to(self.store.directory(workspace))) for side in ('fronts','backs')}) for sheet in manifest['sheets']]
                from .variants import samples
                variants=samples(self.store,workspace,prefix,rows,css,desktop_sample,light,cancel)
                if cancel(): raise DomainError('CANCELLED','Cancelled; previews not marked current.')
                result={'_committed':True,'samples':variants,'sheets':sheets,'cards_sha256':digest(self.store.path(workspace,'cards.json')),'selected_ids':[c['id'] for c in selected],'card_revision':revision,'prefix':prefix,'approximation': 'Local inert template rendering; custom Anki filters/add-on JavaScript are not executed.'}
                self.store.write_json(workspace,'latest-preview.json',result)
                return result
        return self.jobs.submit(workspace,'render_cards',run)
