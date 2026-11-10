"""Prepare Anki arguments and record caller evidence; never contact Anki."""
from collections import defaultdict
import uuid
from .models import ExternalResult
from .store import DomainError, digest

class Payloads:
    def prepare_write(self, workspace, expected_revision, ids=None):
        with self.store.lock(workspace):
            state=self.store.get(workspace)
            if state['revision']!=expected_revision: raise DomainError('STALE','Workspace revision changed.')
            cards=self._select(workspace,ids)
            if not cards: raise DomainError('CARD','No cards selected.')
            checks=self.check_cards(workspace,ids)
            if checks['blockers']: raise DomainError('VALIDATION','Cards contain technical blockers.','Use check_cards and correct the affected fields.')
            ident=uuid.uuid4().hex; base=f'write/{ident}'
            groups=defaultdict(list); updates=[]; media=[]; suspension=[]
            for card in cards:
                if card['action']=='update': updates.append({'note_id':card['note_id'],'fields':card['fields']})
                else: groups[(card['deck'],card['notetype'],tuple(card['fields']))].append(card)
                media.extend(card['media'])
                if card['tier']==3:
                    suspension.append({'draft_id':card['id'],'note_id':card['note_id'],'card_ids':card['card_ids'],'requires_card_id_resolution':not bool(card['card_ids'])})
            unique_media={}
            for item in media:
                filename=item['filename']
                content=digest(self.store.path(workspace,item['path']))
                if filename in unique_media and unique_media[filename][0]!=content:
                    raise DomainError('MEDIA','Conflicting media content uses one Anki filename.','Use distinct filenames and update the card image references.')
                unique_media[filename]=(content,item)
            media=[entry[1] for entry in unique_media.values()]
            merged={}
            for update in updates:
                fields=merged.setdefault(update['note_id'],{})
                for name,value in update['fields'].items():
                    if name in fields and fields[name]!=value:
                        raise DomainError('UPDATE','Conflicting update values for the same note field.','Resolve the conflicting local cards before preparing payloads.')
                    fields[name]=value
            updates=[{'note_id':nid,'fields':fields} for nid,fields in merged.items()]
            batches=[]; imports=[]
            from cards.write.importfile import emit
            for (deck,model,_),notes in groups.items():
                for start in range(0,len(notes),100):
                    relative=f'{base}/batches/{len(batches)+1:03d}.json'
                    self.store.write_json(workspace,relative,{'deck_name':deck,'model_name':model,'notes':[{'fields':n['fields'],'tags':n['tags']} for n in notes[start:start+100]]})
                    batches.append({'artifact':relative,'sha256':digest(self.store.path(workspace,relative)), 'draft_ids':[n['id'] for n in notes[start:start+100]]})
                relative=f'{base}/import-{len(imports)+1:03d}.txt'
                emit(self.store.path(workspace,relative),notes,deck,model); imports.append(relative)
            plan={'plan_id':ident,'revision':expected_revision,'cards_sha256':digest(self.store.path(workspace,'cards.json')),
                  'created':sum(len(v) for v in groups.values()),'updated':len(updates),'batches':batches,'updates':updates,
                  'media':media,'suspension_intentions':suspension,'import_files':imports,
                  'performed_anki_operations':0,'review_required':False,'findings':checks['findings'],
                  'verification_expectations':{'created_draft_ids':[c['id'] for c in cards if c['action']=='create'],
                    'update_note_ids':[c['note_id'] for c in cards if c['action']=='update'],
                    'instructions':'Use official Anki MCP to read back actual note fields and resolve card IDs before suspension.'}}
            artifact=f'{base}/plan.json'; self.store.write_json(workspace,artifact,plan)
            self.store.write_json(workspace,'latest-plan.json',{'artifact':artifact})
            return {'plan_id':ident,'artifact':artifact,'created':plan['created'],'updated':plan['updated'],'batches':batches,'performed_anki_operations':0}

    def record_external_results(self, workspace, plan_id, results, expected_revision):
        parsed=[ExternalResult.model_validate(r).model_dump() for r in results]
        with self.store.edit(workspace,expected_revision) as state:
            plan=self.store.read_json(workspace,f'write/{plan_id}/plan.json')
            if plan['cards_sha256']!=digest(self.store.path(workspace,'cards.json')): raise DomainError('STALE','Write plan is stale.','Reconcile actual Anki results before preparing another plan.')
            self.store.write_json(workspace,f'write/{plan_id}/external-results.json',{'results':parsed,'evidence_origin':'caller_supplied','independently_verified':False})
        return {'revision':state['revision'],'recorded':len(parsed),'evidence_origin':'caller_supplied','independently_verified':False}

    def get_report(self, workspace):
        path=self.store.path(workspace,'latest-plan.json')
        report={'workspace':workspace,'revision':self.store.get(workspace)['revision'],'cards':len(self._cards(workspace)),
                'reported_successes':0,'reported_failures':0,'ambiguous':0,'evidence_origin':'caller_supplied','independently_verified':False,'performed_anki_operations':0}
        if path.exists():
            plan=self.store.read_json(workspace,self.store.read_json(workspace,'latest-plan.json')['artifact'])
            report['planned']={'created':plan['created'],'updated':plan['updated']}
            report['plan_stale']=plan['cards_sha256']!=digest(self.store.path(workspace,'cards.json'))
            receipts=self.store.path(workspace,f'write/{plan["plan_id"]}/external-results.json')
            if receipts.exists():
                results=self.store.read_json(workspace,str(receipts.relative_to(self.store.directory(workspace))))['results']
                report.update(reported_successes=sum(r['status']=='success' for r in results),reported_failures=sum(r['status']=='failed' for r in results),ambiguous=sum(r['status']=='ambiguous' for r in results))
        return report
