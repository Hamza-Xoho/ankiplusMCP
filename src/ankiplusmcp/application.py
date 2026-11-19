"""Per-operation durable application and read-only reconciliation."""
import base64
from contextlib import contextmanager
import hashlib
from filelock import FileLock, Timeout
from .runs import _encoded
from .store import DomainError, digest


class Application:
    @contextmanager
    def collection_lock(self,binding):
        try:
            with FileLock(self.config.directory/('collection-'+binding['identity_sha256']+'.lock'),timeout=0):yield
        except Timeout:raise DomainError('BUSY','Another run is applying to this collection.') from None

    def _journal(self,run_id):
        intents={};acks={};results={}
        for e in self.runs.read(run_id).events:
            p=e.payload
            if e.kind=='operation_intent':intents[p['operation_id']]=p
            elif e.kind=='operation_ack':acks[p['operation_id']]=p
            elif e.kind=='operation_result':results[p['operation_id']]=p
        return intents,acks,results

    def _outcome(self,run_id,item,status,*,note_ids=None,card_ids=None,code=None):
        value={'operation_id':item.get('operation_id',item.get('id')),'operation':item['operation'],
               'status':status,'note_ids':note_ids or [],'card_ids':card_ids or [],
               'evidence_origin':'companion_readback' if status in ('confirmed','unchanged') else 'coordinator',
               'code':code}
        self.event(run_id,'operation_result',value)
        return value

    def _guard_locked(self,run_id,p):
        """Called while holding workspace + configuration locks through dispatch."""
        run=self.runs.read(run_id)
        if self.s._cards(run.workspace)!=p.cards:
            raise DomainError('STALE','Drafts changed since authorization.')
        config=self.config._current()[0]
        if any(getattr(config,k)!=v for k,v in p.config.items()):raise DomainError('STALE','Relevant saved preferences changed since authorization.')
        snap=self.s.source_catalog.snapshot_locked(run.workspace)
        if snap.source_hash!=p.source['source_hash']:raise DomainError('SOURCE_CHANGED','Source changed since authorization.')
        for m in p.media.values():
            if digest(self.s.store.path(run.workspace,m['path']))!=m['sha256']:raise DomainError('STALE','Media changed since authorization.')

    async def _verify(self,adapter,intent,ack):
        binding=await adapter.collection_identity()
        if any(binding[k]!=v for k,v in intent['binding'].items() if k!='collection_session'):
            raise DomainError('CONFLICT','Readback belongs to another collection/profile.')
        op=intent['operation'];args=intent['arguments'];nid=None
        if op=='add_note':
            nid=ack.get('result',{}).get('note_id') if ack else None
            if type(nid) is not int or nid<=0:return None
        elif op=='update_note_fields':nid=args['id']
        if nid is not None:
            notes=await adapter.read_notes([nid])
            if len(notes)!=1 or notes[0].fields!=args['fields'] or not notes[0].card_ids:return None
            cards=await adapter.read_cards(notes[0].card_ids)
            if any(c['nid']!=nid or c['note_fields']!=args['fields'] or c['sibling_card_ids']!=sorted(notes[0].card_ids) for c in cards):return None
            return {'note_ids':[nid],'card_ids':notes[0].card_ids}
        if op in ('card_suspend','card_unsuspend'):
            cards=await adapter.read_cards(args['card_ids'])
            wanted=op=='card_suspend'
            # Bind complete note fields/ownership from the reviewed state even
            # when reconciliation occurs in a new observed runtime session.
            targets=intent['expected_state']['target']
            expected={n['id']:n for n in targets}
            for card in cards:
                note=expected.get(card['nid'])
                if not note or card['note_fields']!=note['fields'] or card['sibling_card_ids']!=sorted(c['id'] for c in note['cards']):return None
                if (card['queue']==-1)!=wanted:return None
            return {'note_ids':sorted({c['nid'] for c in cards}),'card_ids':args['card_ids']}
        if op=='store_media_file':
            media=await adapter.read_media(args['filename'])
            wanted=base64.b64decode(args['data'],validate=True)
            if media['sha256']!=hashlib.sha256(wanted).hexdigest() or base64.b64decode(media['data'],validate=True)!=wanted:return None
            return {'note_ids':[],'card_ids':[]}
        raise DomainError('UNSUPPORTED','Unsupported verification operation.')

    async def _send(self,run_id,p,adapter,item):
        run=self.runs.read(run_id)
        # No await can intervene between the final local check and durable intent.
        # These locks remain held while the adapter performs guarded dispatch.
        with self.s.store.lock(run.workspace), self.config._lock():
            self._guard_locked(run_id,p)
            if await adapter.collection_identity()!=p.binding:
                return self._outcome(run_id,item,'conflict',code='COLLECTION_CHANGED')
            current=await adapter.operation_state(item['operation'],item['arguments'])
            if current!=item['expected_state']:
                if item['operation'] in ('card_suspend','card_unsuspend'):
                    verified=await self._verify(adapter,{**item,'binding':p.binding},None)
                    if verified is not None:return self._outcome(run_id,item,'unchanged',**verified)
                return self._outcome(run_id,item,'conflict',code='TARGET_CHANGED')
            intent={**item,'operation_id':item['id'],'binding':p.binding,'proposal_digest':p.digest,'content_digest':p.content_digest}
            self.event(run_id,'operation_intent',intent)
            try:
                ack=await adapter.dispatch(item['operation'],item['arguments'],item['expected_state'])
            except DomainError as exc:
                return self._outcome(run_id,item,'conflict' if exc.code=='CONFLICT' else 'uncertain',code=exc.code)
            # An acknowledgement is durable even if malformed or the process dies
            # before the next instruction. It is never itself confirmed success.
            self.event(run_id,'operation_ack',{'operation_id':item['id'],'acknowledgement':ack})
        try:verified=await self._verify(adapter,intent,ack)
        except DomainError as exc:return self._outcome(run_id,item,'uncertain',code=exc.code)
        if verified is None:return self._outcome(run_id,item,'uncertain',code='READBACK_INCOMPLETE')
        outcome=self._outcome(run_id,item,'confirmed',**verified)
        if item['operation'] in ('add_note','update_note_fields'):
            self.event(run_id,'verified_mapping',{'source_refs':item['source_refs'],'concept_id':item['concept_id'],
                'fields':item['arguments']['fields'],'note_ids':verified['note_ids'],'card_ids':verified['card_ids'],
                'binding':p.binding,'operation_id':item['id'],'tier':item.get('tier')})
        return outcome

    async def _tier(self,run_id,p,adapter,item,result):
        if item.get('tier')!=3 or item['operation'] not in ('add_note','update_note_fields') or result['status']!='confirmed':return
        opid=item['id']+'-tier'
        intents,acks,results=self._journal(run_id)
        if opid in intents or opid in results:return
        args={'card_ids':result['card_ids']}
        state=await adapter.operation_state('card_suspend',args)
        fields=item['arguments']['fields']
        if any(n['id'] not in result['note_ids'] or n['fields']!=fields for n in state['target']):
            self._outcome(run_id,dict(id=opid,operation='card_suspend'),'conflict',code='GENERATED_CARDS_CHANGED');return
        child={**item,'id':opid,'operation':'card_suspend','arguments':args,'expected_state':state,'tier':None}
        await self._send(run_id,p,adapter,child)

    def _summary(self,run_id,proposal=None):
        intents,acks,results=self._journal(run_id)
        rows=list(results.values())
        confirmed=[r for r in rows if r['status']=='confirmed']
        counts={
            'notes_created':sum(len(r['note_ids']) for r in confirmed if r['operation']=='add_note'),
            'notes_updated':sum(len(r['note_ids']) for r in confirmed if r['operation']=='update_note_fields'),
            'cards_generated':sum(len(r['card_ids']) for r in confirmed if r['operation']=='add_note'),
            'cards_suspended':sum(len(r['card_ids']) for r in confirmed if r['operation']=='card_suspend'),
            'cards_unsuspended':sum(len(r['card_ids']) for r in confirmed if r['operation']=='card_unsuspend'),
            'uncertain_operations':sum(r['status']=='uncertain' for r in rows)}
        pending=[o['id'] for o in proposal.operations if o['id'] not in results] if proposal else []
        return {'run_id':run_id,'results':rows,'counts':counts,'pending_operation_ids':pending}

    async def apply(self,run_id,proposal_digest):
        with self.lock(run_id):
            p=self._current(run_id,proposal_digest,quality=True)
            # Always repeat local quality enforcement; a human click never bypasses it.
            from .quality import validate_quality
            validate_quality(p)
            from .quality import QualityGate
            QualityGate(self).validate_proposal(p)
            if any(f.get('severity')=='blocker' for f in p.findings):raise DomainError('QUALITY','Technical blockers remain.')
            auth=[e for e in self.runs.read(run_id).events if e.kind=='authorization' and e.payload['proposal_digest']==proposal_digest]
            if not auth:raise DomainError('AUTHORIZATION','Authorize this exact proposal before application.')
            with self.collection_lock(p.binding):
                # Earlier uncertain operations in other runs block new writes.
                if any(r!=run_id for r,intent in self.unresolved(p.binding)):
                    raise DomainError('UNCERTAIN','Reconcile earlier uncertain collection writes first.')
                async with self._connection() as adapter:
                    intents,acks,results=self._journal(run_id)
                    for item in p.operations:
                        ident=item['id']
                        if ident in intents and ident not in results:
                            self._outcome(run_id,item,'uncertain',code='RECONCILE_REQUIRED');break
                        if ident in results:
                            if results[ident]['status']=='uncertain':break
                            await self._tier(run_id,p,adapter,item,results[ident]);continue
                        # Local edits during a prior readback invalidate all remaining sends.
                        self._current(run_id,proposal_digest,quality=True)
                        result=await self._send(run_id,p,adapter,item)
                        if result['status']=='uncertain':break
                        await self._tier(run_id,p,adapter,item,result)
                    return self._summary(run_id,p)

    async def reconcile(self,run_id):
        with self.lock(run_id):
            intents,acks,results=self._journal(run_id)
            p=self._latest(run_id)
            with self.collection_lock(p.binding):
                async with self._connection() as adapter:
                    for ident,intent in intents.items():
                        if results.get(ident,{}).get('status') in ('confirmed','unchanged','failed','conflict'):continue
                        ack=acks.get(ident,{}).get('acknowledgement')
                        try:verified=await self._verify(adapter,intent,ack)
                        except DomainError as exc:
                            self._outcome(run_id,intent,'uncertain',code=exc.code);continue
                        if verified is None:self._outcome(run_id,intent,'uncertain',code='INSUFFICIENT_COLLECTION_EVIDENCE')
                        else:self._outcome(run_id,intent,'confirmed',**verified)
            return self._summary(run_id,p)
