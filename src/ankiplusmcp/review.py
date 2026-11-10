"""Optional review snapshots and explicit, revision-checked field changes."""
import uuid
from .models import Finding, Card
from .store import DomainError, digest

class Review:
    def prepare_review(self, workspace, scope='content', ids=None):
        with self.store.lock(workspace):
            return self._review_bundle(workspace,scope,ids)

    def _review_bundle(self, workspace, scope, ids):
        if scope not in ('content','visual'): raise DomainError('SCOPE','Use content or visual.')
        selected=self._select(workspace,ids)
        result={'scope':scope,'revision':self.store.get(workspace)['revision'],
                'reviewer_identity_verified':False,'card_ids':[c['id'] for c in selected]}
        if scope=='visual':
            path=self.store.path(workspace,'latest-preview.json')
            if not path.exists(): return dict(result,status='needs_previews',next_tool='render_cards')
            preview=self.store.read_json(workspace,'latest-preview.json')
            if preview.get('cards_sha256') != digest(self.store.path(workspace,'cards.json')):
                return dict(result,status='stale_previews',next_tool='render_cards')
            # Do not attach fields, sources or author reasoning to a visual bundle.
            if set(preview.get('selected_ids',[])) != {c['id'] for c in selected}:
                return dict(result,status='needs_scoped_previews',next_tool='render_cards with these ids')
            result['sheets']=preview['sheets']
        else:
            result['cards']=selected
            result['source_available']=self.store.path(workspace,self.engine(workspace)+'/source/slides.json').is_file()
            result['source_tool']='read_source for cited source_ref slide numbers'
        return result

    def submit_review(self, workspace, reviewer, findings, expected_revision):
        if not reviewer.strip() or len(reviewer)>200: raise DomainError('REVIEW','Supply a short reviewer label.')
        if len(findings)>1000: raise DomainError('LIMIT','At most 1000 findings.')
        parsed=[Finding.model_validate(f).model_dump() for f in findings]
        with self.store.edit(workspace,expected_revision) as state:
            cards={c['id']:c for c in self._cards(workspace)}
            for finding in parsed:
                if finding['card_id'] not in cards: raise DomainError('CARD','Review refers to unknown card.')
                if finding['rewrite'] and not set(finding['rewrite'])<=set(cards[finding['card_id']]['fields']):
                    raise DomainError('REVIEW','Rewrite contains unknown fields.','Use existing field names; correct and resubmit.')
            ident=uuid.uuid4().hex
            self.store.write_json(workspace,f'reviews/{ident}.json',{'reviewer':reviewer,'identity_verified':False,'findings':parsed,'cards_sha256':digest(self.store.path(workspace,'cards.json'))})
        return {'review_id':ident,'revision':state['revision'],'findings':len(parsed)}

    def apply_changes(self, workspace, review_id, expected_revision, ids=None, apply=False):
        with self.store.lock(workspace,'review'):
            review=self.store.read_json(workspace,f'reviews/{review_id}.json')
            if review['cards_sha256'] != digest(self.store.path(workspace,'cards.json')):
                raise DomainError('STALE','Review is stale.','Review the current cards.')
            cards=self._cards(workspace); byid={c['id']:c for c in cards}; changes=[]; seen={}
            for finding in review['findings']:
                if ids is not None and finding['card_id'] not in ids: continue
                for field,new in (finding['rewrite'] or {}).items():
                    key=(finding['card_id'],field)
                    if key in seen and seen[key]!=new: raise DomainError('CONFLICT','Review has conflicting rewrites for one field.','Submit a resolved review.')
                    seen[key]=new
            for (ident,field),new in seen.items():
                old=byid[ident]['fields'][field]
                if old!=new:
                    changes.append({'card_id':ident,'field':field,'before':old,'after':new})
                    byid[ident]['fields'][field]=new
                    byid[ident]['question']=None
                    byid[ident]['answer']=None
            if self.store.get(workspace)['revision'] != expected_revision: raise DomainError('STALE','Workspace revision changed.')
            if apply:
                result=self.save_cards(workspace,cards,expected_revision)
                return {'changes':changes,'applied':True,**result}
            return {'changes':changes,'applied':False,'revision':expected_revision}
