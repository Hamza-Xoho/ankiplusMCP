"""Pending source contradictions survive searches and runs until explicit resolution.

Resolution names exact observed finding tokens; wall-clock ordering never erases
an independently recorded finding. This is historical evidence, not preference learning.
"""
import hashlib
from uuid import uuid4
from .runs import _encoded
from .store import DomainError


def source_key(decision,workspace=None):
    if hasattr(decision,'model_dump'):decision=decision.model_dump()
    refs=[]
    for r in decision['source_refs']:
        refs.append({'source_hash':r['source_hash'],'page':r['page'],'quote':' '.join((r.get('quote') or '').split())})
    hashes=sorted({hashlib.sha256(_encoded(r)).hexdigest() for r in refs})
    return hashlib.sha256(_encoded({'concept_id':decision['concept_id'],'references':hashes,**({'workspace':workspace} if not refs else {})})).hexdigest()


class SourceConflicts:
    def pending_conflicts(self,decisions,*,workspace=None):
        pending={};resolved=set();catalog=self.runs.catalog()
        if catalog.errors:raise DomainError('RUN_CORRUPT','Unreadable source-decision history must be recovered before new proposals.')
        for projection in catalog.changed:
            for event in projection.snapshot.events:
                if event.kind=='source_contradiction':
                    p=event.payload;pending[p['token']]=p['source_key']
                elif event.kind=='source_contradiction_resolved':resolved.update(event.payload['tokens'])
        return {d['concept_id'] if isinstance(d,dict) else d.concept_id:
                sorted(token for token,key in pending.items() if key==source_key(d,workspace) and token not in resolved)
                for d in decisions}

    def record_contradictions(self,run_id,requested,batch_id):
        for d in requested:
            if d['source_disagreement']:
                self.event(run_id,'source_contradiction',{'token':uuid4().hex,'source_key':source_key(d,self.runs.read(run_id).workspace),
                    'concept_id':d['concept_id'],'batch_id':batch_id,'source_refs':d['source_refs']})
