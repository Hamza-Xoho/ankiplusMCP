"""Durable student workflow. Networking is confined to the narrow companion adapter.

Snapshots and journals are evidence, never distributed transactions. Unknown writes
remain unknown until sufficient readback exists; creates are never blindly resent.
"""
import base64
from contextlib import contextmanager
import hashlib
import json
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import Field

from .configuration import ConfigStore
from .coverage import CoverageStore, CoverageDecision, CollectionSnapshot
from .evidence import EvidenceResolver
from .models import Model
from .run_models import RunEvent, SourceSelection
from .runs import RunStore, _encoded, _identifier
from .store import DomainError, digest


def sha(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


class Proposal(Model):
    run_id: str
    digest: str
    content_digest: str
    inputs_digest: str
    source: dict
    config: dict
    saved_config: dict = Field(default_factory=dict)
    cards: list[dict]
    media: dict = Field(default_factory=dict)
    review_selection: dict = Field(default_factory=dict)
    review_cards: list[dict] = Field(default_factory=list)
    decisions: list[dict]
    operations: list[dict]
    quality: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    binding: dict


class Authorization(Model):
    id: str
    run_id: str
    proposal_digest: str
    mode: str


CONFIG_DEPENDENCIES = ('selected_decks','profile','note_type','tag_root','review_mode','uncertain_match')


def scoped_query(query, config):
    if not isinstance(query,str) or not 1 <= len(query) <= 1500:
        raise DomainError('SCOPE','Provide a bounded search within your approved decks.')
    if '\\' in query:raise DomainError('SCOPE','Escaped search syntax is unsupported; use balanced plain terms within the approved scope.')
    quoted=False; escaped=False; depth=0
    for char in query:
        if escaped: escaped=False; continue
        if char=='\\': escaped=True; continue
        if char=='"': quoted=not quoted
        elif not quoted and char in '()':
            depth += 1 if char=='(' else -1
            if depth<0: raise DomainError('SCOPE','Search parentheses are unbalanced.')
    if depth or quoted or escaped:
        raise DomainError('SCOPE','Search quotes or parentheses are unbalanced.')
    def quote(value):
        if not isinstance(value,str) or not value or any(c in value for c in ('"','\\','\n','\r')):
            raise DomainError('CONFIG','Use an unambiguous deck name/ID and tag namespace for coverage.')
        return '"'+value+'"'
    decks=[('did:'+d if d.isdecimal() else 'deck:'+quote(d)) for d in config.selected_decks]
    own='tag:'+quote(config.tag_root+'::*')
    result='('+' or '.join([*decks,own])+') ('+query+')'
    if len(result)>2000: raise DomainError('LIMIT','Narrow the configured coverage scope.')
    return result


from .application import Application
from .run_preferences import RunPreferences
from .source_conflicts import SourceConflicts


class Coordinator(Application,RunPreferences,SourceConflicts):
    def __init__(self, service):
        self.s=service
        root=service.store.root/'.student-workflows'
        launch=service._launch_profile
        initial={'note_type':launch.note_type,'tag_root':launch.tag_root,
                 'source_roots':[str(p) for p in (service.store.source_roots or ())],
                 'profile':getattr(service.companion_connection,'profile','default')}
        self.config=ConfigStore(root,initial=initial)
        self.runs=RunStore(root)
        self.evidence=EvidenceResolver(service.source_catalog)
        self.coverage_store=CoverageStore(self.runs,self.config,self.evidence)

    @contextmanager
    def lock(self, run_id):
        path=self.runs._path(run_id)
        try:
            with FileLock(path/'.workflow.lock',timeout=0): yield
        except Timeout:
            raise DomainError('BUSY','This run is being changed; reopen it after the current action.') from None

    def event(self, run_id, kind, payload):
        self.runs.append(run_id,RunEvent(kind=kind,payload=payload))

    def start(self, workspace, pages=None):
        snap=self.s.source_catalog.snapshot(workspace)
        selection=SourceSelection(source_hash=snap.source_hash,pages=pages or [],label=snap.source_name or workspace)
        if selection.pages and not set(selection.pages) <= (snap.available_pages() or set()):
            raise DomainError('SOURCE_REF','Extract the selected pages before starting this run.')
        return self.runs.start(workspace,selection,self.config.read().config_version)

    def _connection(self):
        if self.s.companion_connection is None:
            raise DomainError('UNSUPPORTED','Configure the intended companion profile and collection first.')
        return self.s.companion_connection()

    def unresolved(self, binding=None):
        pending=[]
        catalog=self.runs.catalog()
        if catalog.errors: raise DomainError('RUN_CORRUPT','Reconcile unreadable run history before new writes.')
        for projection in catalog.changed:
            intents={}; results={}
            for e in projection.snapshot.events:
                if e.kind=='operation_intent': intents[e.payload['operation_id']]=e.payload
                if e.kind=='operation_result': results[e.payload['operation_id']]=e.payload
            for ident,intent in intents.items():
                if results.get(ident,{}).get('status') in ('confirmed','unchanged','failed','conflict'): continue
                if binding is None or intent['binding']['identity_sha256']==binding['identity_sha256']:
                    pending.append((projection.snapshot.id,intent))
        return pending

    def _prior_mappings(self, decisions, binding, cards):
        matching={}
        catalog=self.runs.catalog()
        if catalog.errors:raise DomainError('RUN_CORRUPT','Unreadable history prevents safe mapping reuse.')
        for projection in catalog.changed:
            for event in projection.snapshot.events:
                if event.kind!='verified_mapping':continue
                m=event.payload
                if any(m['binding'][k]!=v for k,v in binding.items() if k!='collection_session'):continue
                for d in decisions:
                    card=cards.get(d.draft_id)
                    if card and m['concept_id']==d.concept_id and m['source_refs']==[r.model_dump() for r in d.source_refs] and m['fields']==card['fields']:
                        matching.setdefault(d.concept_id,[]).append(m)
        return matching

    async def coverage(self, run_id, query, decisions):
        with self.lock(run_id):
            run=self.runs.read(run_id); config=self.effective_config(run_id)
            decisions=[CoverageDecision.model_validate(d).model_copy(deep=True) for d in decisions]
            requested=[d.model_dump() for d in decisions]
            pending=self.pending_conflicts(decisions,workspace=run.workspace)
            for d in decisions:
                if pending[d.concept_id]:d.source_disagreement=True
            query=scoped_query(query,config)
            async with self._connection() as adapter:
                binding=await adapter.collection_identity()
                if binding['profile_name']!=config.profile: raise DomainError('CONFIG','Saved profile differs from the selected companion.')
                with self.collection_lock(binding):
                    if self.unresolved(binding): raise DomainError('UNCERTAIN','Reconcile earlier writes before collecting new coverage.')
                    prior=self._prior_mappings(decisions,binding,{c['id']:c for c in self.s._cards(run.workspace)})
                    known=sorted({nid for values in prior.values() for m in values for nid in m['note_ids']})
                    if known:
                        # Rewrap the complete expression, keeping previous identities inside approved scope.
                        query='('+query+') or ('+' or '.join('nid:'+str(n) for n in known)+')'
                        if len(query)>2000:raise DomainError('LIMIT','Narrow this mapping batch to fit a bounded coverage search.')
                    ids=await adapter.search_notes(query)
                    notes=await adapter.read_notes(ids)
                    card_ids=[c for n in notes for c in n.card_ids]
                    cards=[]
                    for offset in range(0,len(card_ids),100): cards.extend(await adapter.read_cards(card_ids[offset:offset+100]))
                    by_id={c['id']:c for c in cards}
                    for note in notes:
                        if any(by_id[c]['nid']!=note.note_id or by_id[c]['note_fields']!=note.fields or by_id[c]['sibling_card_ids']!=sorted(note.card_ids) for c in note.card_ids):
                            raise DomainError('CONFLICT','Coverage changed between complete note/card reads.')
                        note.suspended_card_ids=[c for c in note.card_ids if by_id[c]['queue']==-1]
                    if await adapter.collection_identity()!=binding: raise DomainError('CONFLICT','Collection session changed during coverage.')
                    by_note={n.note_id:n for n in notes}
                    for d in decisions:
                        mappings=prior.get(d.concept_id,[])
                        if not mappings or d.disposition!='propose_create' or d.source_disagreement or d.uncertain:continue
                        candidates={n for m in mappings for n in m['note_ids']}
                        if len(candidates)!=1 or not candidates <= set(by_note):
                            d.disposition='pending';d.uncertain=True;d.pending_reason='prior_mapping_changed';continue
                        nid=next(iter(candidates));note=by_note[nid]
                        if note.fields!=mappings[-1]['fields']:
                            d.disposition='pending';d.uncertain=True;d.pending_reason='prior_mapping_changed';continue
                        d.candidate_note_ids=d.chosen_note_ids=[nid];d.card_ids=note.card_ids[:]
                        if mappings[-1].get('tier')==3:d.disposition='pending'
                        elif note.suspended_card_ids:d.disposition='propose_unsuspend';d.card_ids=note.suspended_card_ids[:]
                        else:d.disposition='already_covered'
                    batch=uuid4().hex
                    snapshot=CollectionSnapshot(collection_id=binding['identity_sha256'],query=query,notes=notes)
                    saved=self.coverage_store.record(run_id,snapshot,decisions,batch_id=batch,preferences=config)
                    self.record_contradictions(run_id,requested,batch)
                    self.event(run_id,'collection_coverage',{'batch_id':batch,'binding':binding,'query':query,
                        'scope':{k:getattr(config,k) for k in ('profile','selected_decks','tag_root')},
                        'notes':[n.model_dump() for n in notes],'decisions':[d.model_dump() for d in saved],
                        'evidence_origin':'companion_readback','semantic_completeness_verified':False,'requested_decisions':requested})
                    return {'batch_id':batch,'decisions':[d.model_dump() for d in saved],'query':query}

    def _inputs(self, run_id):
        run=self.runs.read(run_id);saved_config=self.config.read()
        config=self.effective_config(run_id,config=saved_config,run=run)
        events=[e for e in run.events if e.kind=='collection_coverage']
        if not events: raise DomainError('COVERAGE','Collect approved-scope coverage before staging.')
        latest={}
        selected={}
        scope={k:getattr(config,k) for k in ('profile','selected_decks','tag_root')}
        for event in run.events:
            if event.kind=='collection_coverage':
                if event.payload.get('scope')!=scope:
                    # Old coverage remains evidence, but cannot authorize new scope.
                    continue
                for decision in event.payload['decisions']:latest[decision['concept_id']]=dict(decision)
            elif event.kind=='review_decision':
                for decision in event.payload['decisions']:
                    if decision['concept_id'] in latest:latest[decision['concept_id']]=dict(decision)
                selected.update(event.payload['selected'])
        if events[-1].payload.get('scope')!=scope:
            raise DomainError('SCOPE','Approved search scope changed; refresh collection coverage before staging.')
        events=[e for e in events if e.payload.get('scope')==scope]
        decisions=list(latest.values())
        selected={d['concept_id']:selected.get(d['concept_id'],True) for d in decisions}
        pending=self.pending_conflicts(decisions,workspace=run.workspace)
        for d in decisions:
            if pending[d['concept_id']]:d['source_disagreement']=True;d['disposition']='pending'
        active_ids={d.get('draft_id') for d in decisions if selected.get(d['concept_id'],True) and d['disposition'] in ('propose_create','explicit_update')}
        with self.s.store.lock(run.workspace):
            source=self.s.source_catalog.snapshot_locked(run.workspace)
            if source.source_hash!=run.selection.source_hash: raise DomainError('SOURCE_CHANGED','Run source no longer matches its immutable selection.')
            cards=self.s._cards(run.workspace)
            media={m['filename']:{'path':m['path'],'sha256':digest(self.s.store.path(run.workspace,m['path']))} for c in cards if c['id'] in active_ids for m in c['media']}
            if sum(len(c['media']) for c in cards if c['id'] in active_ids)>len(media):
                all_media=[m for c in cards if c['id'] in active_ids for m in c['media']]
                if any(digest(self.s.store.path(run.workspace,m['path']))!=media[m['filename']]['sha256'] for m in all_media):
                    raise DomainError('MEDIA','Media names collide with different bytes.')
        selected_refs=[ref for d in decisions for ref in d['source_refs']]
        evidence=[]
        for start in range(0,len(selected_refs),20):evidence.extend(e.model_dump() for e in self.evidence.resolve(run.workspace,selected_refs[start:start+20]))
        from cards.review.packets import TEMPLATES
        policy={str(path.relative_to(TEMPLATES)):digest(path) for role in ('maintainer','student') for path in (TEMPLATES/role).glob('*.md')}
        policy['house-style.md']=digest(TEMPLATES/'house-style.md')
        from .review_app import html
        return {'review_resource_sha256':hashlib.sha256(html().encode()).hexdigest(),'quality_policy':policy,'source':run.selection.model_dump(),'config':{k:getattr(config,k) for k in CONFIG_DEPENDENCIES},'saved_config':{k:getattr(saved_config,k) for k in CONFIG_DEPENDENCIES},
                'cards':cards,'media':media,'decisions':decisions,'review_selection':selected,'pending_conflicts':pending,'evidence':evidence,
                'coverage':[{k:e.payload[k] for k in ('batch_id','binding','query','notes')} for e in events]}

    def _latest(self,run_id):
        events=[e for e in self.runs.read(run_id).events if e.kind=='proposal_staged']
        if not events: raise DomainError('PROPOSAL','Stage this run first.')
        value=events[-1].payload['proposal']
        if sha({k:v for k,v in value.items() if k!='digest'})!=value.get('digest'):
            raise DomainError('RUN_CORRUPT','Stored proposal digest does not match its immutable contents.')
        return Proposal.model_validate(value)

    def _quality(self,run_id,content_digest):
        reports={};accepted={}
        for e in self.runs.read(run_id).events:
            q=e.payload
            if q.get('content_digest')!=content_digest:continue
            if e.kind=='quality_report':reports[q['role']]=q['ticket_id'];accepted.pop(q['role'],None)
            elif e.kind=='quality_accepted' and reports.get(q['role'])==q['ticket_id']:accepted[q['role']]=q
        return [accepted[role] for role in sorted(accepted)]

    def _current(self,run_id,proposal_digest,*,quality=False):
        p=self._latest(run_id)
        if p.digest!=proposal_digest or sha(self._inputs(run_id))!=p.inputs_digest:
            raise DomainError('STALE','Proposal inputs changed; review and validate a new proposal.')
        workspace=self.runs.read(run_id).workspace
        for media in p.media.values():
            if digest(self.s.store.path(workspace,media['path']))!=media['sha256']:
                raise DomainError('STALE','Retained media changed since proposal review.')
        if quality and self._quality(run_id,p.content_digest)!=p.quality:
            raise DomainError('STALE','Quality evidence changed; stage and review the current proposal.')
        return p

    async def stage(self, run_id):
        with self.lock(run_id):
            inputs=self._inputs(run_id);run=self.runs.read(run_id)
            binding=inputs['coverage'][-1]['binding']
            observed={n['note_id']:n for b in inputs['coverage'] for n in b['notes']}
            review_cards=[]
            retained_media=dict(inputs['media'])
            planned_media={}
            if self.unresolved(binding): raise DomainError('UNCERTAIN','Reconcile earlier writes before staging.')
            cards={c['id']:c for c in inputs['cards']};operations=[];findings=[]
            active_ids=[d['draft_id'] for d in inputs['decisions'] if d.get('draft_id') and inputs['review_selection'].get(d['concept_id'],True) and d['disposition'] in ('propose_create','explicit_update')]
            checked=self.s.check_cards(run.workspace,ids=active_ids)
            findings.extend(checked['findings'])
            from cards.check.lint import lint
            for ident in active_ids:
                card=cards[ident]
                findings.extend({**finding,'card_id':ident} for finding in lint({**card,'tags':card['tags'] if card['action']=='create' else []},tag_root=inputs['config']['tag_root']))
            async with self._connection() as adapter:
                if await adapter.collection_identity()!=binding: raise DomainError('CONFLICT','Coverage belongs to another collection session; refresh it.')
                used={m['filename']:m for d in inputs['decisions'] if d['disposition'] in ('propose_create','explicit_update') and inputs['review_selection'].get(d['concept_id'],True)
                      for m in (cards.get(d.get('draft_id')) or {}).get('media',[])}
                total=0
                for filename,m in sorted(used.items()):
                    data=self.s.store.path(run.workspace,m['path']).read_bytes();total+=len(data)
                    if not data or len(data)>8*1024*1024 or total>24*1024*1024:
                        raise DomainError('LIMIT','Stage at most 24 MiB of media, with 1 byte–8 MiB per file.')
                    planned_media[filename]={'path':m['path'],'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
                    args={'filename':filename,'data':base64.b64encode(data).decode()}
                    state=await adapter.operation_state('store_media_file',args)
                    if state['target'] is not None and state['target']['sha256']!=hashlib.sha256(data).hexdigest():
                        raise DomainError('MEDIA','Existing media has different bytes; choose a new filename and re-review.')
                    operations.append({'id':sha({'operation':'store_media_file','arguments':args,'state':state})[:32],
                        'operation':'store_media_file','arguments':args,'expected_state':state,'source_refs':[],
                        'concept_id':None,'draft_id':None,'tier':None})
                for d in inputs['decisions']:
                    if not inputs['review_selection'].get(d['concept_id'],True):continue
                    action=d['disposition'];card=cards.get(d.get('draft_id'))
                    if action in ('pending','already_covered'):continue
                    if action in ('propose_create','explicit_update') and card is None:
                        raise DomainError('CARD','The coverage decision needs an existing local draft.')
                    if action=='propose_create':
                        if card['action']!='create' or card['note_id'] is not None: raise DomainError('UPDATE','Existing notes are protected; explicitly choose an update.')
                        if card['notetype']!=inputs['config']['note_type']:raise DomainError('CONFIG','Draft note type differs from the saved card profile.')
                        op='add_note';args={'deck_name':card['deck'],'model_name':card['notetype'],'fields':card['fields'],'tags':card['tags']}
                    elif action=='explicit_update':
                        if card['action']!='update' or d['chosen_note_ids']!=[card['note_id']]: raise DomainError('UPDATE','Explicit update must name exactly its selected note.')
                        op='update_note_fields';args={'id':card['note_id'],'fields':card['fields']}
                    elif action=='propose_unsuspend':op='card_unsuspend';args={'card_ids':d['card_ids']}
                    else:raise DomainError('COVERAGE','Unsupported coverage decision.')
                    state=await adapter.operation_state(op,args)
                    from .media_binding import bind_media
                    await bind_media(self,adapter,run.workspace,state,planned_media,retained_media,findings,d.get('draft_id'))
                    if op in ('update_note_fields','card_unsuspend'):
                        targets=[state['target']] if op=='update_note_fields' else state['target']
                        for target in targets:
                            prior=observed.get(target['id'])
                            if not prior or target['fields']!=prior['fields'] or sorted(c['id'] for c in target['cards'])!=sorted(prior['card_ids']):
                                raise DomainError('CONFLICT','Existing note content or card ownership changed since coverage; refresh the match.')
                    if op in ('add_note','update_note_fields'):
                        adapter.validate_note_type(state['target']['model'],args['fields'])
                        review_cards.append({**card,'model':state['target']['model']})
                    else:
                        for target in state['target']:
                            fields=target['fields']
                            ident=(d.get('draft_id') or d['concept_id']) if len(state['target'])==1 else 'existing-'+sha({'concept':d['concept_id'],'nid':target['id']})[:24]
                            review_cards.append({'id':ident,'fields':fields,'model':target['model'],'tags':target['tags'],
                                'kind':'cloze' if any('{{c' in v for v in fields.values()) else 'basic','notetype':target['model']['name'],
                                'note_id':target['id'],'action':'reuse','media':[]})
                    item={'id':sha({'concept':d['concept_id'],'operation':op,'arguments':args,'state':state})[:32],
                          'concept_id':d['concept_id'],'draft_id':d.get('draft_id'),'operation':op,'arguments':args,
                          'expected_state':state,'tier':card['tier'] if card else None,'source_refs':d['source_refs']}
                    operations.append(item)
            if len({c['id'] for c in review_cards})!=len(review_cards):raise DomainError('COVERAGE','A draft cannot have multiple competing write decisions.')
            content={'inputs':inputs,'operations':operations,'findings':findings}
            content_digest=sha(content)
            quality=self._quality(run_id,content_digest)
            value=dict(run_id=run_id,content_digest=content_digest,inputs_digest=sha(inputs),source=inputs['source'],
                config=inputs['config'],saved_config=inputs['saved_config'],cards=inputs['cards'],media=retained_media,review_selection=inputs['review_selection'],review_cards=review_cards,decisions=inputs['decisions'],operations=operations,
                quality=quality,findings=findings,binding=binding)
            proposal=Proposal(**value,digest=sha(value))
            self.runs.save_snapshot(run_id,'proposal-'+proposal.digest,proposal.model_dump())
            self.event(run_id,'proposal_staged',{'proposal':proposal.model_dump()})
            return proposal

    def authorize(self, run_id, proposal_digest, mode='user'):
        with self.lock(run_id):
            proposal=self._current(run_id,proposal_digest,quality=True)
            if any(f.get('severity')=='blocker' for f in proposal.findings):raise DomainError('QUALITY','Technical/house-style blockers must be resolved.')
            from .quality import validate_quality
            validate_quality(proposal)
            from .quality import QualityGate
            QualityGate(self).validate_proposal(proposal)
            if mode not in ('user','config'):raise DomainError('AUTHORIZATION','Choose explicit user or configuration authorization.')
            if mode=='config' and (proposal.config['review_mode']!='automatic' or proposal.config!=proposal.saved_config):raise DomainError('AUTHORIZATION','Automatic authorization requires an explicitly saved automatic preference.')
            auth=Authorization(id=uuid4().hex,run_id=run_id,proposal_digest=proposal_digest,mode=mode)
            self.event(run_id,'authorization',auth.model_dump())
            return auth
