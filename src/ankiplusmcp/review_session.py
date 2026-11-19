"""Run/workspace/session-bound review. Decisions change local proposals, never Anki."""
import hashlib
import secrets
import time
from uuid import uuid4
from .coordinator import sha
from .coverage import CoverageDecision
from .models import Card
from .store import DomainError


class ReviewSession:
    def __init__(self,coordinator):self.c=coordinator

    def _validate_session(self,run_id,token):
        if not isinstance(token,str) or len(token)!=64:raise DomainError('SESSION','Reopen this run to establish a review session.')
        hashed=hashlib.sha256(token.encode()).hexdigest()
        run=self.c.runs.read(run_id)
        sessions=[e.payload for e in run.events if e.kind=='review_session' and secrets.compare_digest(e.payload['token_sha256'],hashed)]
        if not sessions or sessions[-1]['workspace']!=run.workspace or sessions[-1]['expires_at']<time.time():
            raise DomainError('SESSION','Review session expired or belongs to another run.')
        return run

    def _view(self,run_id):
        p=self.c._latest(run_id);inputs=self.c._inputs(run_id)
        current=sha(inputs)==p.inputs_digest
        return p,inputs,p.digest if current else 'unstaged-'+sha(inputs),current

    async def open(self,run_id):
        try:self.c._latest(run_id)
        except DomainError:await self.c.stage(run_id)
        with self.c.lock(run_id):
            token=secrets.token_hex(32);run=self.c.runs.read(run_id)
            self.c.event(run_id,'review_session',{'token_sha256':hashlib.sha256(token.encode()).hexdigest(),
                'workspace':run.workspace,'expires_at':time.time()+3600})
            return self.read(run_id,token)

    @staticmethod
    def _fields(fields,budget=8000):
        size=max(40,budget//max(1,len(fields)))
        return {k:v[:size] for k,v in fields.items()},[k for k,v in fields.items() if len(v)>size]

    def read(self,run_id,session_token,offset=0):
        run=self._validate_session(run_id,session_token)
        if type(offset) is not int or offset<0:raise DomainError('LIMIT','Invalid review page.')
        p,inputs,version,current=self._view(run_id)
        cards={c['id']:c for c in inputs['cards']};notes={n['note_id']:n for b in inputs['coverage'] for n in b['notes']}
        items=[]
        for d in inputs['decisions'][offset:offset+1]:
            card=cards.get(d.get('draft_id'));fields=card['fields'] if card else {}
            if d['disposition'] in ('already_covered','propose_unsuspend') and len(d['chosen_note_ids'])==1:
                fields=notes[d['chosen_note_ids'][0]]['fields']
            display,truncated=self._fields(fields)
            evidence=self.c.evidence.resolve(run.workspace,d['source_refs']) if d['source_refs'] else []
            refs=[]
            for number,e in enumerate(evidence):
                value=e.model_dump();value['quote_truncated']=len(value.get('quote') or '')>300
                value['quote']=(value.get('quote') or '')[:300];value['reference_index']=number;refs.append(value)
            existing=[]
            candidate_order=list(dict.fromkeys(d['chosen_note_ids']+d['candidate_note_ids']))
            for nid in candidate_order[:3]:
                note=notes[nid];values,short=self._fields(note['fields'],budget=3000)
                existing.append({**note,'fields':values,'truncated_fields':short})
            rows=[]
            reports={}
            for event in run.events:
                if event.kind=='quality_report' and event.payload['content_digest']==p.content_digest:
                    reports[event.payload['role']]=event.payload['rows']
            for report in reports.values():
                for row in report:
                    if row.get('note_id')==d.get('draft_id') or (row['type']=='set' and d.get('draft_id') in row.get('notes',[])):
                        rows.append({k:(str(v)[:800] if not isinstance(v,(bool,int)) else v) for k,v in row.items() if k not in ('rewrite',)})
            findings=[f for f in p.findings if f.get('card_id') in (None,d.get('draft_id'))]+rows
            from .run_responses import page
            shown,_=page(findings,0,10,budget=6000)
            items.append({**{k:v for k,v in d.items() if k!='source_refs'},'fields':display,'truncated_fields':truncated,
                'selected':inputs['review_selection'].get(d['concept_id'],True),'source_evidence':refs,
                'existing_notes':existing,'more_existing_candidates':len(d['candidate_note_ids'])>3,
                'findings':shown,'findings_total':len(findings),'more_findings':len(shown)<len(findings)})
        ready=False
        if current:
            try:
                from .quality import QualityGate,validate_quality
                self.c._current(run_id,p.digest,quality=True)
                validate_quality(p);QualityGate(self.c).validate_proposal(p)
                ready=True
            except DomainError:pass
        return {'run_id':run_id,'workspace':run.workspace,'session_token':session_token,'digest':version,
            'proposal_digest':p.digest,'content_digest':p.content_digest,'items':items,'offset':offset,'total':len(inputs['decisions']),
            'next_offset':offset+1 if offset+1<len(inputs['decisions']) else None,'needs_revalidation':not current,
            'quality_status':'ready' if ready else 'required','source':p.source,
            'can_authorize':ready and not any(f.get('severity')=='blocker' for f in p.findings)}

    def field(self,run_id,token,concept_id,name,note_id=None,offset=0,limit=4000):
        self._validate_session(run_id,token)
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=4000:raise DomainError('LIMIT','Invalid field slice.')
        p,inputs,version,current=self._view(run_id)
        d=next((d for d in inputs['decisions'] if d['concept_id']==concept_id),None)
        if d is None:raise DomainError('REVIEW','Unknown review item.')
        if note_id is None and d['disposition'] in ('already_covered','propose_unsuspend') and len(d['chosen_note_ids'])==1:
            note_id=d['chosen_note_ids'][0]
        if note_id is not None:
            if note_id not in d['candidate_note_ids']:raise DomainError('REVIEW','Existing note is outside this review item.')
            fields=next(n['fields'] for b in reversed(inputs['coverage']) for n in b['notes'] if n['note_id']==note_id)
        else:fields=next(c['fields'] for c in inputs['cards'] if c['id']==d.get('draft_id'))
        if name not in fields:raise DomainError('REVIEW','Unknown field.')
        value=fields[name]
        return {'text':value[offset:offset+limit],'next_offset':offset+limit if offset+limit<len(value) else None,'digest':version}

    def source_image(self,run_id,token,expected_review_digest,concept_id,reference_index):
        run=self._validate_session(run_id,token)
        _,inputs,version,_=self._view(run_id)
        if version!=expected_review_digest:raise DomainError('STALE','This source view changed; reload the saved review.')
        decision=next((d for d in inputs['decisions'] if d['concept_id']==concept_id),None)
        if decision is None:raise DomainError('REVIEW','Unknown review item.')
        refs=decision['source_refs']
        if type(reference_index) is not int or not 0<=reference_index<len(refs):raise DomainError('SOURCE_REF','Unknown source reference.')
        evidence=self.c.evidence.resolve(run.workspace,[refs[reference_index]])[0]
        if evidence.location_kind!='pdf_page':raise DomainError('SOURCE_REF','This reference is a text section, not a PDF page.')
        asset=self.c.s.get_page_image(run.workspace,evidence.page)
        data=self.c.s.image_bytes(run.workspace,asset['artifact'])
        if self._view(run_id)[2]!=version:raise DomainError('STALE','The review changed while loading its source page; reload it.')
        return data

    async def decide(self,run_id,session_token,expected_proposal_digest,decisions):
        with self.c.lock(run_id),self.c.collection_lock(self.c._latest(run_id).binding):
            run=self._validate_session(run_id,session_token)
            p,inputs,version,current=self._view(run_id)
            if expected_proposal_digest!=version:raise DomainError('STALE','This tab shows an older proposal. Reload the saved review before changing it.')
            if not isinstance(decisions,list) or not 1<=len(decisions)<=100:raise DomainError('LIMIT','Save between 1 and 100 decisions.')
            if any(not isinstance(v,dict) or ('fields' in v and not isinstance(v['fields'],dict)) for v in decisions):
                raise DomainError('REVIEW','Each decision and its fields must be structured mappings.')
            if len({v.get('concept_id') for v in decisions})!=len(decisions):raise DomainError('REVIEW','Do not repeat a review item in one save.')
            by_id={d['concept_id']:d for d in inputs['decisions']};cards={c['id']:c for c in inputs['cards']}
            selected=dict(inputs['review_selection']);changed=[];card_changed=False;resolved=[]
            notes={n['note_id']:n for b in inputs['coverage'] for n in b['notes']}
            revision=self.c.s.store.get(run.workspace)['revision']
            for value in decisions:
                if not isinstance(value,dict) or set(value)-{'concept_id','action','fields','note_id','card_ids','resolve_contradiction'}:
                    raise DomainError('REVIEW','Unsupported review decision fields.')
                ident=value.get('concept_id');action=value.get('action')
                if ident not in by_id or action not in ('keep','exclude','edit-new','choose-existing','defer','explicit-update'):
                    raise DomainError('REVIEW','Choose a supported action on a displayed item.')
                d=dict(by_id[ident]);card=cards.get(d.get('draft_id'));nid=value.get('note_id')
                if nid is not None and (type(nid) is not int or nid not in d['candidate_note_ids']):raise DomainError('REVIEW','Select an existing candidate from this review.')
                selected[ident]=action!='exclude'
                if action=='defer':d['disposition']='pending'
                elif action in ('edit-new','explicit-update'):
                    if action=='explicit-update' and nid is None:raise DomainError('UPDATE','Explicit update requires a selected existing note.')
                    fields={**(notes[nid]['fields'] if nid else (card or {}).get('fields',{})),**value.get('fields',{})}
                    if card is None:
                        card=Card(id='draft-'+uuid4().hex,kind='cloze' if any('{{c' in v for v in fields.values()) else 'basic',
                            fields=fields,notetype=p.config['note_type'],tags=[p.config['tag_root']+'::Adapted'],source_ref=[r['page'] for r in d['source_refs']]).model_dump()
                        d['draft_id']=card['id']
                    else:card={**card,'fields':fields,'question':None,'answer':None}
                    if action=='edit-new':
                        card.update(action='create',note_id=None,card_ids=[])
                        d.update(disposition='propose_create',chosen_note_ids=[],card_ids=[])
                    else:
                        card.update(action='update',note_id=nid,card_ids=notes[nid]['card_ids'])
                        d.update(disposition='explicit_update',chosen_note_ids=[nid],card_ids=notes[nid]['card_ids'])
                    cards[card['id']]=Card.model_validate(card).model_dump();card_changed=True;d['uncertain']=False
                elif action=='choose-existing':
                    if nid is None:raise DomainError('REVIEW','Choose the existing note that covers this concept.')
                    ids=value.get('card_ids',notes[nid]['card_ids'])
                    if not isinstance(ids,list) or not ids or any(type(i) is not int for i in ids) or len(set(ids))!=len(ids) or not set(ids)<=set(notes[nid]['card_ids']):
                        raise DomainError('REVIEW','Choose actual card IDs owned by the selected note.')
                    suspended=[cid for cid in ids if cid in notes[nid]['suspended_card_ids']]
                    d.update(chosen_note_ids=[nid],card_ids=suspended or ids,disposition='propose_unsuspend' if suspended else 'already_covered',uncertain=False)
                if d['source_disagreement'] and not (value.get('resolve_contradiction') is True and action in ('choose-existing','edit-new','explicit-update')):
                    d['disposition']='pending'
                elif value.get('resolve_contradiction') is True:
                    d['source_disagreement']=False
                    resolved.extend(inputs['pending_conflicts'].get(ident,[]))
                changed.append(CoverageDecision.model_validate(d).model_dump())
            if card_changed:self.c.s.save_cards(run.workspace,list(cards.values()),revision)
            if resolved:self.c.event(run_id,'source_contradiction_resolved',{'tokens':sorted(set(resolved))})
            self.c.event(run_id,'review_decision',{'decisions':changed,'selected':selected,'previous_digest':version})
        try:await self.c.stage(run_id)
        except DomainError as exc:
            if exc.code not in ('TRANSPORT','COMPANION','UNSUPPORTED','CONFLICT','QUALITY'):raise
            self.c.event(run_id,'review_revalidation_required',{'code':exc.code})
        return self.read(run_id,session_token)

    def approve(self,run_id,session_token,expected_proposal_digest):
        self._validate_session(run_id,session_token)
        p,inputs,version,current=self._view(run_id)
        if not current or version!=expected_proposal_digest:raise DomainError('STALE','Reload and validate the current proposal before approval.')
        return self.c.authorize(run_id,p.digest,'user').model_dump()
