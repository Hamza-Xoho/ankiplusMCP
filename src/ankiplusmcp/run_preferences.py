"""Explicit preference diffs scoped to one run, independent of future defaults."""
from uuid import uuid4
from .configuration import UserConfig
from .runs import _encoded,_identifier
from .store import DomainError
import hashlib

KEYS=('selected_decks','note_type','tag_root','review_mode','uncertain_match')
LABELS={'selected_decks':'Coverage decks','note_type':'New-card note type','tag_root':'New-card tag namespace','review_mode':'Draft review','uncertain_match':'Uncertain matches','source_roots':'Source folders','source_materials':'Study materials','profile':'Anki profile'}


def preference_diff(before,after,keys):
    def show(value):
        if isinstance(value,list):return ', '.join(value) if value else 'none'
        return {'manual':'review drafts with me','automatic':'process after required quality checks',
                'pending':'leave uncertain matches pending','reuse':'reuse a selected uncertain match','create':'propose a new card for uncertain matches'}.get(str(value),str(value))
    return [f'{LABELS.get(k,k)}: {show(before[k])} → {show(after[k])}' for k in keys]


class RunPreferences:
    def _overrides(self,run):
        value={}
        for event in run.events:
            if event.kind=='run_preferences':value=event.payload['overrides']
        return value

    def effective_config(self,run_id,*,config=None,run=None):
        config=config or self.config.read();run=run or self.runs.read(run_id)
        return UserConfig.model_validate({**config.model_dump(),**self._overrides(run)})

    def _scope_token(self,run,config):
        return hashlib.sha256(_encoded({'saved':{k:getattr(config,k) for k in KEYS},'overrides':self._overrides(run)})).hexdigest()

    def propose_run_preferences(self,run_id,changes):
        with self.lock(run_id):
            if not isinstance(changes,dict) or not changes or set(changes)-set(KEYS):raise DomainError('CONFIG','Only run-specific review, matching, deck and card defaults can change here.')
            run=self.runs.read(run_id);config=self.config.read()
            before=self.effective_config(run_id,config=config,run=run)
            after=UserConfig.model_validate({**before.model_dump(),**changes})
            keys=[k for k in changes if getattr(before,k)!=getattr(after,k)]
            if not keys:raise DomainError('CONFIG','No preferences changed.')
            change={'id':uuid4().hex,'run_id':run_id,'scope':'this_run','before':{k:getattr(before,k) for k in keys},
                    'after':{k:getattr(after,k) for k in keys},'expected_scope':self._scope_token(run,config),
                    'diff':preference_diff(before.model_dump(),after.model_dump(),keys)}
            self.runs.save_snapshot(run_id,'run-config-'+change['id'],change)
            self.event(run_id,'run_preferences_proposed',change)
            return change

    def confirm_run_preferences(self,run_id,change_id):
        _identifier(change_id)
        with self.lock(run_id):
            run=self.runs.read(run_id);config=self.config.read()
            changes=[e.payload for e in run.events if e.kind=='run_preferences_proposed' and e.payload['id']==change_id]
            if not changes:raise DomainError('CONFIG','Unknown run preference proposal.')
            current=self._overrides(run)
            prior=[e.payload for e in run.events if e.kind=='run_preferences' and e.payload['change_id']==change_id]
            if prior and prior[-1]['overrides']==current:return self.effective_config(run_id,config=config,run=run).model_dump()
            change=changes[-1]
            if self._scope_token(run,config)!=change['expected_scope']:raise DomainError('STALE','Preferences changed; inspect a fresh run-only diff before confirming.')
            overrides={**current,**change['after']}
            UserConfig.model_validate({**config.model_dump(),**overrides})
            self.event(run_id,'run_preferences',{'change_id':change_id,'overrides':overrides,'scope':'this_run'})
            return self.effective_config(run_id).model_dump()
