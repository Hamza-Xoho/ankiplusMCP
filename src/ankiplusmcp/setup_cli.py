"""Local setup and trusted host-evidence import. No reviewer launch or collection write.

The importer is an operator/supervisor trust boundary, deliberately absent from
MCP tools. Run it only on actual observed host exports, never author assertions.
It cannot add missing host controls, substitute models or relax review budgets.
"""
import argparse
import asyncio
import hashlib
import hmac
import json
from pathlib import Path
from . import settings
from .service import Service
from .store import DomainError
from .runs import _encoded,_publish


def onboard_main(argv):
    parser=argparse.ArgumentParser(prog='ankiplusmcp onboard')
    parser.add_argument('--workspace-root',default=str(settings.default_workspace_root()))
    parser.add_argument('--step',choices=('storage','connection','guide'))
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--companion-url');parser.add_argument('--anki-profile');parser.add_argument('--anki-collection-path');parser.add_argument('--companion-token-file')
    args=parser.parse_args(argv)
    s=Service(args.workspace_root,[])
    try:
        if args.companion_url:
            if not args.anki_profile or not args.anki_collection_path:raise DomainError('CONFIG','Select the intended companion profile and collection explicitly.')
            from .companion_connection import CompanionConnection
            s.companion_connection=CompanionConnection(args.companion_url,profile=args.anki_profile,collection_path=args.anki_collection_path,token_file=args.companion_token_file)
        from .onboarding import Onboarding
        onboarding=Onboarding(s)
        status=asyncio.run(onboarding.advance(args.step,{})) if args.step else onboarding.status()
        if args.json:print(status.model_dump_json())
        else:
            print('Setup verified.' if status.onboarding_complete else 'Setup still needs: '+', '.join(status.remaining_checks))
            if status.guide_path:print('Your guide: '+status.guide_path)
        return 0
    except (DomainError,OSError,ValueError) as exc:
        print(json.dumps({'status':'error','code':getattr(exc,'code','INPUT'),'message':str(exc)[:1000]}));return 2
    finally:s.close()


def evidence_main(argv):
    parser=argparse.ArgumentParser(prog='ankiplusmcp verify-host-evidence',description='Trusted local operator import of actual observed host evidence; never a reviewer launcher.')
    parser.add_argument('--workspace-root',required=True)
    parser.add_argument('--kind',choices=('quality','interactive-review'),required=True)
    parser.add_argument('--run-id',required=True);parser.add_argument('--content-digest')
    parser.add_argument('--observed-execution',required=True)
    args=parser.parse_args(argv)
    s=Service(args.workspace_root,[])
    try:
        path=Path(args.observed_execution)
        if path.is_symlink() or not path.is_file() or path.stat().st_size>512000:raise DomainError('QUALITY','Use a bounded original observed execution file, not a symbolic link.')
        body=json.loads(path.read_bytes())
        if not isinstance(body,dict) or 'attestation' in body:raise DomainError('QUALITY','Provide the original observed export, without an author-supplied attestation.')
        from .coordinator import Coordinator
        from .quality import QualityGate,LIMITS,ROLE_TOOLS
        c=Coordinator(s);gate=QualityGate(c)
        if args.kind=='quality':
            role=body.get('role')
            if role not in LIMITS or body.get('launch')!={'max_turns':LIMITS[role],'tools':ROLE_TOOLS[role],'omit_author_context':True}:
                raise DomainError('QUALITY','Actual launch-level cumulative controls and reviewer isolation are missing; no evidence can be attested.')
            if not args.content_digest:raise DomainError('QUALITY','Name the exact reviewed proposal content digest.')
            message={'run_id':args.run_id,'content_digest':args.content_digest,'receipt':body}
            signed={**body,'attestation':hmac.new(gate.key_path.read_bytes(),_encoded(message),hashlib.sha256).hexdigest()}
            result=gate.submit(args.run_id,args.content_digest,signed)
            output=gate._packet(args.run_id,body['ticket_id'])/'attested-execution.json'
        else:
            if body.get('run_id')!=args.run_id:raise DomainError('SETUP','Observed App evidence belongs to another run.')
            message={'purpose':'interactive-review','receipt':body}
            signed={**body,'attestation':hmac.new(gate.key_path.read_bytes(),_encoded(message),hashlib.sha256).hexdigest()}
            from .onboarding import Onboarding
            status=asyncio.run(Onboarding(s).advance('interactive_review',signed))
            if 'interactive_review' in status.remaining_checks:raise DomainError('SETUP','Actual production App verification evidence is incomplete or changed.')
            result={'status':'accepted','runtime':body['runtime']}
            output=c.runs._path(args.run_id)/('app-evidence-'+hashlib.sha256(_encoded(signed)).hexdigest()+'.json')
        if output.exists() and output.read_bytes()!=_encoded(signed):raise DomainError('CONFLICT','An existing attested export differs; preserve both original records.')
        _publish(output,signed)
        print(json.dumps({'result':result,'attested_execution':str(output),'evidence_origin':'imported_host_execution'}));return 0
    except (DomainError,OSError,ValueError,KeyError) as exc:
        print(json.dumps({'status':'error','code':getattr(exc,'code','INPUT'),'message':str(exc)[:1000]}));return 2
    finally:s.close()
