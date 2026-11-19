"""Resumable setup milestones. Public inputs cannot assert a verified check."""
import hashlib
import hmac
import json
from pathlib import Path
from uuid import uuid4
from pydantic import Field
from .configuration import UserConfig
from .coordinator import Coordinator,sha
from .guide import Guide,VerifiedCapabilities
from .models import Model
from .quality import QualityGate
from .runs import _encoded,_publish
from .store import DomainError,digest

REQUIRED=('storage','connection','interactive_review','quality_runtime','guide')


class SetupStatus(Model):
    configuration: UserConfig
    onboarding_complete: bool
    remaining_checks: list[str]
    checks: dict = Field(default_factory=dict)
    guide_path: str | None = None


class Onboarding:
    def __init__(self,service):
        self.s=service;self.c=Coordinator(service)
        self.directory=self.c.config.directory/'onboarding'
        if self.directory.is_symlink():raise DomainError('CONFIG','Onboarding evidence cannot be a symbolic link.')
        self.directory.mkdir(exist_ok=True)

    def _checks(self):
        checks={}
        for file in sorted(self.directory.glob('*.json')):
            if file.is_symlink():raise DomainError('CONFIG','Onboarding record cannot be a symbolic link.')
            record=json.loads(file.read_bytes())
            checks[record['step']]=record['result']
        config=self.c.config.read()
        # Historical completion does not establish a newly selected profile/type.
        connection=checks.get('connection',{})
        if connection.get('status')=='passed' and connection.get('preferences')!={'profile':config.profile,'note_type':config.note_type}:
            checks['connection']={'status':'required','code':'PREFERENCES_CHANGED'}
        return checks

    def status(self):
        config=self.c.config.read();checks=self._checks()
        remaining=[key for key in REQUIRED if checks.get(key,{}).get('status')!='passed']
        guide=checks.get('guide',{}).get('path')
        if guide:
            path=Path(guide)
            if not path.is_file() or path.is_symlink():
                checks['guide']={'status':'required','code':'GUIDE_MISSING'}
                if 'guide' not in remaining:remaining.append('guide')
        complete=not remaining and config.onboarding_complete and config.onboarding_version==1
        return SetupStatus(configuration=config,onboarding_complete=complete,remaining_checks=remaining,checks=checks,guide_path=guide)

    def _capabilities(self,checks):
        passed=lambda key:checks.get(key,{}).get('status')=='passed'
        return VerifiedCapabilities(anki_connection=passed('connection'),interactive_review=passed('interactive_review'),
            independent_quality_review=passed('quality_runtime'),source_evidence=passed('storage'),history=passed('storage'))

    def refresh_guide(self):
        return Guide.write(self.c.config.read(),self._capabilities(self._checks()))

    async def advance(self,step,evidence):
        if step not in REQUIRED:raise DomainError('SETUP','Choose a supported setup milestone.')
        if not isinstance(evidence,dict):raise DomainError('SETUP','Setup evidence must be a structured record.')
        config=self.c.config.read()
        try:
            if step=='storage':
                if evidence:raise DomainError('SETUP','Storage is checked directly, not from caller assertions.')
                path=self.c.config.directory/('.storage-probe-'+uuid4().hex+'.json')
                value={'probe':uuid4().hex}
                try:
                    _publish(path,value)
                    if json.loads(path.read_bytes())!=value:raise DomainError('STORAGE','Storage readback did not match.')
                finally:path.unlink(missing_ok=True)
                result={'status':'passed','evidence_sha256':sha({'root':str(self.s.store.root)})}
            elif step=='connection':
                if evidence:raise DomainError('SETUP','Connection is checked directly, not from caller assertions.')
                async with self.c._connection() as adapter:
                    capabilities=await adapter.capabilities()
                    required={'collection_identity','find_notes','notes_info','student_operation_state','conditional_student_operation','read_media_file','model_field_names','model_templates','model_styling'}
                    if not required<=capabilities:raise DomainError('UNSUPPORTED','The installed companion lacks required student workflow capabilities.')
                    binding=await adapter.collection_identity()
                    if binding['profile_name']!=config.profile:raise DomainError('CONFLICT','Saved profile differs from the intended companion profile.')
                    model=await adapter.read_note_type(config.note_type)
                    if await adapter.collection_identity()!=binding:raise DomainError('CONFLICT','Profile changed during setup verification.')
                result={'status':'passed','evidence_sha256':sha({'binding':binding,'model':model}),
                        'preferences':{'profile':config.profile,'note_type':config.note_type}}
            elif step=='quality_runtime':
                if set(evidence)!={'run_id'}:raise DomainError('QUALITY','Observed independent quality execution evidence is required; a caller pass flag is insufficient.')
                p=self.c._latest(evidence['run_id']);self.c._current(evidence['run_id'],p.digest,quality=True)
                QualityGate(self.c).validate_proposal(p)
                result={'status':'passed','evidence_sha256':sha(p.quality),'run_id':p.run_id,'provenance':'trusted_verifier_imported_host_execution'}
            elif step=='interactive_review':
                required={'run_id','session_token_sha256','resource_sha256','bridge_version','runtime','observations','attestation'}
                if set(evidence)!=required:raise DomainError('SETUP','A trusted observed production App handshake/readback/reconnect receipt is required.')
                gate=QualityGate(self.c);body={k:v for k,v in evidence.items() if k!='attestation'}
                expected=hmac.new(gate.key_path.read_bytes(),_encoded({'purpose':'interactive-review','receipt':body}),hashlib.sha256).hexdigest()
                if not isinstance(evidence['attestation'],str) or not hmac.compare_digest(expected,evidence['attestation']):raise DomainError('SETUP','Production App verification requires trusted host attestation.')
                from .review_app import html
                if evidence['resource_sha256']!=hashlib.sha256(html().encode()).hexdigest() or evidence['bridge_version']!='2.0.4' or not isinstance(evidence['runtime'],str) or not evidence['runtime'].strip():
                    raise DomainError('SETUP','App resource, bridge or observed runtime differs from this installation.')
                if evidence['observations']!={'initialize':True,'tool_call':True,'readback':True,'reconnect':True}:raise DomainError('SETUP','Production App interaction and reconnect have not all been observed.')
                sessions=[e for e in self.c.runs.read(evidence['run_id']).events if e.kind=='review_session' and e.payload['token_sha256']==evidence['session_token_sha256']]
                if not sessions:raise DomainError('SETUP','The observed App session does not belong to this run.')
                result={'status':'passed','evidence_sha256':sha(evidence),'runtime':evidence['runtime']}
            else:
                if evidence:raise DomainError('SETUP','The tailored guide is written and checked directly.')
                guide=self.refresh_guide()
                result={'status':'passed','path':str(guide),'evidence_sha256':digest(guide)}
        except (DomainError,OSError,ValueError) as exc:
            result={'status':'failed','code':getattr(exc,'code','STORAGE'),'remedy':getattr(exc,'remedy','Check the chosen data folder or supply actual host evidence.')}
        # Unique monotonic sequence under the same configuration lock used for preferences.
        with self.c.config._lock():
            number=max((int(p.stem) for p in self.directory.glob('[0-9]'*20+'.json')),default=0)+1
            _publish(self.directory/f'{number:020d}.json',{'step':step,'result':result})
        checks=self._checks()
        if checks.get('guide',{}).get('status')=='passed' and step!='guide':
            guide=self.refresh_guide()
            with self.c.config._lock():
                number=max((int(p.stem) for p in self.directory.glob('[0-9]'*20+'.json')),default=0)+1
                _publish(self.directory/f'{number:020d}.json',{'step':'guide','result':{'status':'passed','path':str(guide),'evidence_sha256':digest(guide)}})
            checks=self._checks()
        self.c.config._record_setup({k:(('pass:'+v['evidence_sha256']) if v.get('status')=='passed' else 'failed:'+v.get('code','REQUIRED')) for k,v in checks.items()},not any(checks.get(k,{}).get('status')!='passed' for k in REQUIRED))
        return self.status()
