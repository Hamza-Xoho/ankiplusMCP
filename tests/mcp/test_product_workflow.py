"""Actual facade orchestration with synthetic external transport only."""
import base64
import hashlib
from copy import deepcopy
import pytest
from PIL import Image
from ankiplusmcp.store import DomainError
from test_coordinator import workflow, covered, run
from test_reconciliation import approved
from test_workflow_quality import receipt, attest
from test_sources import wait


def test_complete_facade_path_uses_bound_quality_and_real_run_state(workflow):
    from ankiplusmcp.server import API
    c,s,e,r,d=workflow;api=API(s)
    run(api.record_run_coverage(r.id,'collagen',[d]))
    wait(s,r.workspace,s.render_cards(r.workspace));p=run(api.stage_run(r.id))
    for role in ('maintainer','student'):
        ticket=api.prepare_run_quality(r.id,p['content_digest'],role)
        value=receipt(ticket,role)
        if role=='student':api.release_review_backs(r.id,p['content_digest'],ticket['ticket_id'],value['attempts'])
        api.submit_run_quality(r.id,p['content_digest'],attest(c,r.id,p['content_digest'],value))
    p=run(api.stage_run(r.id));api.authorize_run(r.id,p['digest'],'user')
    result=run(api.apply_run(r.id,p['digest']))
    assert result['counts']['notes_created']==1
    assert run(api.reconcile_run(r.id))['counts']==result['counts']


def install_media_transport(e):
    original_state=e.state;original_call=e.call_tool
    def state(op,args):
        if op!='store_media_file':return original_state(op,args)
        data=e.media.get(args['filename'])
        target=None if data is None else {'filename':args['filename'],'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        return dict(version=1,operation=op,arguments=deepcopy(args),binding=deepcopy(e.binding),target=target)
    async def call(name,args):
        from types import SimpleNamespace
        if name=='conditional_student_operation' and args['operation']=='store_media_file':
            a=args['arguments'];assert args['expected_state']==state('store_media_file',a)
            e.sent.append(('store_media_file',deepcopy(a)));e.media[a['filename']]=base64.b64decode(a['data'])
            value={'version':1,'binding':e.binding,'result':{'filename':a['filename'],'size':len(e.media[a['filename']])}}
        elif name=='read_media_file':
            data=e.media[args['filename']]
            value={'filename':args['filename'],'data':base64.b64encode(data).decode(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        else:return await original_call(name,args)
        return SimpleNamespace(isError=False,structuredContent=value)
    e.state=state;e.call_tool=call


def with_media(workflow):
    c,s,e,r,d=workflow;install_media_transport(e)
    image=s.store.root.parent/'synthetic.png';Image.new('RGB',(24,24),'white').save(image)
    artifact=s.import_image(r.workspace,str(image))['artifact']
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'media':[{'path':artifact,'filename':'review.png'}],
        'fields':{'Back':'Fibroblasts <img src="review.png">'}}}],1)
    return artifact


def test_media_is_journaled_and_verified_before_referencing_note(workflow):
    c,s,e,r,d=workflow;artifact=with_media(workflow);p=approved(workflow)
    assert [op['operation'] for op in p.operations]==['store_media_file','add_note']
    result=run(c.apply(r.id,p.digest))
    assert [op for op,a in e.sent]==['store_media_file','add_note']
    assert e.media['review.png']==s.store.path(r.workspace,artifact).read_bytes()
    assert all(x['status']=='confirmed' for x in result['results'])


def test_changed_media_invalidates_exact_authorization(workflow):
    c,s,e,r,d=workflow;artifact=with_media(workflow);p=approved(workflow)
    Image.new('RGB',(24,24),'black').save(s.store.path(r.workspace,artifact))
    with pytest.raises(DomainError,match='STALE'):run(c.apply(r.id,p.digest))
    assert not e.sent
