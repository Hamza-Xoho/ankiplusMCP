"""Installed product and real disposable Anki collection over MCP memory streams.

All quality/host receipts in this LOCAL TEST are signed synthetic fixtures. They
exercise enforcement, never establish actual reviewer quality or Mac acceptance.
No sockets, real profiles, credentials, host mounts, sync or rollback.
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
import importlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
from ankiplusmcp.anki_adapter import AnkiAdapter
from ankiplusmcp.service import Service
from ankiplusmcp.server import create_server
from ankiplusmcp.coordinator import Coordinator
from ankiplusmcp.quality import QualityGate
from ankiplusmcp.runs import _encoded


def synthetic_receipt(ticket,role):
    agent='LOCAL-SYNTHETIC-'+role
    reads=[{'artifact':name,'sha256':value,'order':i+1,'turn':1,'agent_id':agent,'tool':'Read'} for i,(name,value) in enumerate(ticket['files'].items())]
    if role=='student':
        fronts=[r for r in reads if r['artifact'].startswith('fronts')];backs=[r for r in reads if r['artifact'].startswith('backs')]
        reads=[r for r in reads if r not in fronts+backs]+fronts+backs
        for i,r in enumerate(reads):r['order']=i+1
        committed=max(r['order'] for r in fronts)+1
        for r in backs:r['order']+=2
    else:committed=None
    report=f'# Review Report — anki-{role}\n'
    for draft_id in ticket['draft_ids']:
        report+=f'\n## Note {draft_id} — PASS\n'
        if role=='student':report+='**Attempt:** synthetic answer → right\n'
    report+=f'\n## Summary\n**Verdict:** PASS\n**Stats:** notes={len(ticket["draft_ids"])}, pass={len(ticket["draft_ids"])}\n'
    return dict(ticket_id=ticket['ticket_id'],role=role,agent_id=agent,author_agent_id='LOCAL-SYNTHETIC-author',
        model='claude-sonnet-5-5',effort='high' if role=='maintainer' else 'medium',
        launch={'max_turns':14 if role=='maintainer' else 6,'tools':ticket['tools'],'omit_author_context':True},
        reads=reads,attempts_committed_at=committed,attempts={i:'synthetic answer' for i in ticket['tile_ids']} if role=='student' else {},report=report)


async def main(package_name):
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.shared.memory import create_connected_server_and_client_session
    with tempfile.TemporaryDirectory(prefix='student-product-') as temporary:
        root=Path(temporary)
        service=Service(root/'workspaces',[root],browser='chromium')
        try:
            import os
            parameters=StdioServerParameters(command=sys.executable,args=['/artifact/companion_stdio.py',str(root),package_name],env={**os.environ,'PYTHONPATH':'/artifact/companion-runtime'})
            async with stdio_client(parameters) as (read,write),ClientSession(read,write) as companion_client:
                await companion_client.initialize()
                dispatch_run=None;dispatch_digest=None;dispatches=[]
                class ObservedClient:
                    async def list_tools(self):return await companion_client.list_tools()
                    async def call_tool(self,name,args):
                        if name=='conditional_student_operation':
                            assert dispatch_run and dispatch_digest
                            assert any(event.kind=='operation_intent' and event.payload['proposal_digest']==dispatch_digest
                                and event.payload['operation']==args['operation'] and event.payload['arguments']==args['arguments']
                                and event.payload['expected_state']==args['expected_state'] for event in c.runs.read(dispatch_run).events)
                            dispatches.append({'run_id':dispatch_run,'operation':args['operation']})
                        return await companion_client.call_tool(name,args)
                observed=ObservedClient()
                @asynccontextmanager
                async def connection():yield AnkiAdapter(observed,profile='Synthetic',collection_path=str(root/'collection.anki2'))
                service.companion_connection=connection
                async with create_connected_server_and_client_session(create_server(service)) as client:
                    calls=[]
                    async def call(name,arguments=None,error=None):
                        started=time.monotonic();response=await client.call_tool(name,arguments or {});value=response.structuredContent
                        calls.append({'tool':name,'error':bool(response.isError),'duration_ms':round((time.monotonic()-started)*1000,1)})
                        if error:
                            assert response.isError and value['error']['code']==error,(name,value)
                        else:assert not response.isError,(name,value)
                        return value
                    choices=await call('get_collection_choices');assert any(d['name']=='Default' for d in choices['decks'])
                    prefs=await call('propose_student_setup',{'choices':{'profile':'Synthetic','note_type':'Basic','selected_decks':[],'source_materials':['custom lecture notes']}})
                    await call('confirm_preferences',{'change_id':prefs['id']})
                    setup=await call('advance_student_setup',{'step':'storage','evidence':{}});assert not setup['ready_to_apply']
                    await call('advance_student_setup',{'step':'connection','evidence':{}})
                    w=await call('create_workspace',{'mode':'lecture','text':'# Cells\nFibroblasts make collagen.'});workspace=w['id']
                    job=await call('extract_source',{'workspace':workspace})
                    for _ in range(300):
                        state=await call('get_job',{'workspace':workspace,'job_id':job['id']})
                        if state['status'] not in ('queued','running'):break
                        await asyncio.sleep(.02)
                    assert state['status']=='completed',state
                    card={'id':'fibroblast','kind':'basic','fields':{'Front':'What makes collagen?','Back':'Fibroblasts'},'notetype':'Basic','deck':'Default','tags':['#AnkiPlus::Cells'],'tier':3,'source_ref':[1]}
                    await call('save_cards',{'workspace':workspace,'cards':[card],'expected_revision':0})
                    current=await call('start_student_run',{'workspace':workspace,'pages':[1]});run_id=current['id']
                    c=Coordinator(service);source=service.store.get(workspace)['source']['sha256']
                    decision={'concept_id':'fibroblast','draft_id':'fibroblast','disposition':'propose_create','source_refs':[{'source_hash':source,'page':1,'quote':'Fibroblasts make collagen.'}]}
                    await call('record_run_coverage',{'run_id':run_id,'query':'collagen','decisions':[decision]})
                    p=await call('stage_run',{'run_id':run_id})
                    await call('authorize_run',{'run_id':run_id,'proposal_digest':p['digest']},error='QUALITY')
                    opened=await call('open_run_review',{'run_id':run_id})
                    resource=await client.read_resource('ui://ankiplus/review.html');html=resource.contents[0].text
                    assert 'AnkiPlus' in html and 'callServerTool' in html
                    changed=await call('save_run_review',{'run_id':run_id,'session_token':opened['session_token'],'expected_proposal_digest':opened['digest'],'decisions':[{'concept_id':'fibroblast','action':'edit-new','fields':{'Back':'Fibroblasts'}}]})
                    resumed=await call('open_run_review',{'run_id':run_id});assert resumed['items'][0]['fields']['Back']=='Fibroblasts'
                    await call('save_run_review',{'run_id':run_id,'session_token':'forged','expected_proposal_digest':changed['digest'],'decisions':[{'concept_id':'fibroblast','action':'exclude'}]},error='SESSION')
                    p=await call('stage_run',{'run_id':run_id})
                    key=QualityGate(c).key_path.read_bytes()
                    for role in ('maintainer','student'):
                        ticket=await call('prepare_run_quality',{'run_id':run_id,'content_digest':p['content_digest'],'role':role})
                        receipt=synthetic_receipt(ticket,role)
                        if role=='student':await call('release_review_backs',{'run_id':run_id,'content_digest':p['content_digest'],'ticket_id':ticket['ticket_id'],'attempts':receipt['attempts']})
                        receipt['attestation']=hmac.new(key,_encoded({'run_id':run_id,'content_digest':p['content_digest'],'receipt':receipt}),hashlib.sha256).hexdigest()
                        await call('submit_run_quality',{'run_id':run_id,'content_digest':p['content_digest'],'receipt':receipt})
                    p=await call('stage_run',{'run_id':run_id})
                    await call('advance_student_setup',{'step':'quality_runtime','evidence':{'run_id':run_id}})
                    evidence={'run_id':run_id,'session_token_sha256':hashlib.sha256(resumed['session_token'].encode()).hexdigest(),
                        'resource_sha256':hashlib.sha256(html.encode()).hexdigest(),'bridge_version':'2.0.4','runtime':'LOCAL SYNTHETIC MCP ACCEPTANCE',
                        'observations':{'initialize':True,'tool_call':True,'readback':True,'reconnect':True}}
                    evidence['attestation']=hmac.new(key,_encoded({'purpose':'interactive-review','receipt':evidence}),hashlib.sha256).hexdigest()
                    await call('advance_student_setup',{'step':'interactive_review','evidence':evidence})
                    setup=await call('advance_student_setup',{'step':'guide','evidence':{}});assert setup['ready_to_apply'],setup
                    await call('authorize_run',{'run_id':run_id,'proposal_digest':p['digest'],'mode':'user'})
                    dispatch_run=run_id;dispatch_digest=p['digest']
                    result=await call('apply_run',{'run_id':run_id,'proposal_digest':p['digest']});assert result['counts']['notes_created']==1 and result['counts']['cards_suspended']==1,result
                    nid=result['results'][0]['note_ids'][0];cid=result['results'][0]['card_ids'][0]
                    async with connection() as adapter:
                        assert (await adapter.read_notes([nid]))[0].fields['Back']=='Fibroblasts'
                        assert (await adapter.read_cards([cid]))[0]['queue']==-1
                    replay=await call('apply_run',{'run_id':run_id,'proposal_digest':p['digest']});assert replay['counts']==result['counts']
                    async with connection() as adapter:assert len(await adapter.search_notes('tag:#AnkiPlus::*'))==1
                    recovered=await call('reconcile_run',{'run_id':run_id});assert recovered['counts']==result['counts']
                    second=await call('start_student_run',{'workspace':workspace,'pages':[1]})
                    await call('record_run_coverage',{'run_id':second['id'],'query':'collagen','decisions':[decision]})
                    next_p=await call('stage_run',{'run_id':second['id']});assert next_p['operations']==0 and next_p['pending']==1
                    history=await call('get_run_history',{'run_id':run_id});assert any(e['kind']=='operation_intent' for e in history['events'])
                    async def passing_quality(target,staged):
                        for role in ('maintainer','student'):
                            ticket=await call('prepare_run_quality',{'run_id':target,'content_digest':staged['content_digest'],'role':role})
                            receipt=synthetic_receipt(ticket,role)
                            if role=='student':await call('release_review_backs',{'run_id':target,'content_digest':staged['content_digest'],'ticket_id':ticket['ticket_id'],'attempts':receipt['attempts']})
                            receipt['attestation']=hmac.new(key,_encoded({'run_id':target,'content_digest':staged['content_digest'],'receipt':receipt}),hashlib.sha256).hexdigest()
                            await call('submit_run_quality',{'run_id':target,'content_digest':staged['content_digest'],'receipt':receipt})
                        return await call('stage_run',{'run_id':target})
                    # Explicit reuse of the known suspended card verifies real
                    # card IDs; editing its note retains existing tags/scheduling.
                    reuse=await call('start_student_run',{'workspace':workspace,'pages':[1]})
                    reuse_decision={**decision,'disposition':'propose_unsuspend','candidate_note_ids':[nid],'chosen_note_ids':[nid],'card_ids':[cid]}
                    await call('record_run_coverage',{'run_id':reuse['id'],'query':'collagen','decisions':[reuse_decision]})
                    reuse_p=await passing_quality(reuse['id'],await call('stage_run',{'run_id':reuse['id']}))
                    await call('authorize_run',{'run_id':reuse['id'],'proposal_digest':reuse_p['digest']})
                    dispatch_run=reuse['id'];dispatch_digest=reuse_p['digest']
                    reuse_result=await call('apply_run',{'run_id':reuse['id'],'proposal_digest':reuse_p['digest']})
                    assert reuse_result['counts']['cards_unsuspended']==1,reuse_result
                    from PIL import Image
                    Image.new('RGB',(24,24),'white').save(root/'update.png')
                    asset=await call('import_image',{'workspace':workspace,'path':str(root/'update.png')})
                    manifest=await call('get_workspace',{'workspace':workspace})
                    await call('patch_cards',{'workspace':workspace,'expected_revision':manifest['revision'],'patches':[{'id':'fibroblast','changes':{
                        'action':'update','note_id':nid,'card_ids':[cid],'tier':1,
                        'fields':{'Back':'Fibroblasts <img src="synthetic-product.png">'},
                        'media':[{'path':asset['artifact'],'filename':'synthetic-product.png'}]}}]})
                    updating=await call('start_student_run',{'workspace':workspace,'pages':[1]})
                    update_decision={**reuse_decision,'disposition':'explicit_update'}
                    await call('record_run_coverage',{'run_id':updating['id'],'query':'collagen','decisions':[update_decision]})
                    update_p=await passing_quality(updating['id'],await call('stage_run',{'run_id':updating['id']}))
                    await call('authorize_run',{'run_id':updating['id'],'proposal_digest':update_p['digest']})
                    dispatch_run=updating['id'];dispatch_digest=update_p['digest']
                    update_result=await call('apply_run',{'run_id':updating['id'],'proposal_digest':update_p['digest']})
                    assert update_result['counts']['notes_updated']==1 and all(row['status']=='confirmed' for row in update_result['results']),update_result
                    async with connection() as adapter:
                        assert (await adapter.read_notes([nid]))[0].fields['Back']=='Fibroblasts <img src="synthetic-product.png">'
                        media=await adapter.read_media('synthetic-product.png')
                        assert media['sha256']==hashlib.sha256((root/'update.png').read_bytes()).hexdigest()
                    # The normal saved Basic profile also supports a mixed run
                    # containing canonical native IO. Both use their actual
                    # captured models and real generated card identities.
                    mixed_w=await call('create_workspace',{'mode':'lecture','text':'# Histology\nA synthetic diagram identifies the nucleus.'})
                    mixed_workspace=mixed_w['id'];mixed_job=await call('extract_source',{'workspace':mixed_workspace})
                    for _ in range(300):
                        mixed_state=await call('get_job',{'workspace':mixed_workspace,'job_id':mixed_job['id']})
                        if mixed_state['status'] not in ('queued','running'):break
                        await asyncio.sleep(.02)
                    assert mixed_state['status']=='completed'
                    Image.new('RGB',(600,360),'white').save(root/'mixed.png')
                    mixed_asset=await call('import_image',{'workspace':mixed_workspace,'path':str(root/'mixed.png')})
                    mixed_cards=[{'id':'mixedbasic','kind':'basic','notetype':'Basic','fields':{'Front':'What does this synthetic diagram identify?','Back':'Nucleus'},'deck':'Default','tags':['#AnkiPlus::Mixed'],'source_ref':[1]},
                        {'id':'diagram','kind':'io','notetype':'Image Occlusion','fields':{'Occlusion':'{{c1::image-occlusion:rect:left=.1:top=.1:width=.2:height=.2:oi=1}}','Image':'<img src="mixed-native.png">','Header':'Synthetic nucleus','Back Extra':'','Comments':''},'deck':'Default','tags':['#AnkiPlus::Mixed'],'source_ref':[1],'media':[{'path':mixed_asset['artifact'],'filename':'mixed-native.png'}]}]
                    await call('save_cards',{'workspace':mixed_workspace,'cards':mixed_cards,'expected_revision':0})
                    mixed_run=await call('start_student_run',{'workspace':mixed_workspace,'pages':[1]})
                    mixed_hash=service.store.get(mixed_workspace)['source']['sha256']
                    await call('record_run_coverage',{'run_id':mixed_run['id'],'query':'nucleus','decisions':[
                        {'concept_id':row['id'],'draft_id':row['id'],'disposition':'propose_create','source_refs':[{'source_hash':mixed_hash,'page':1,'quote':'A synthetic diagram identifies the nucleus.'}]} for row in mixed_cards]})
                    mixed_p=await passing_quality(mixed_run['id'],await call('stage_run',{'run_id':mixed_run['id']}))
                    await call('authorize_run',{'run_id':mixed_run['id'],'proposal_digest':mixed_p['digest']})
                    dispatch_run=mixed_run['id'];dispatch_digest=mixed_p['digest']
                    mixed_result=await call('apply_run',{'run_id':mixed_run['id'],'proposal_digest':mixed_p['digest']})
                    assert mixed_result['counts']['notes_created']==2 and mixed_result['counts']['cards_generated']==2,mixed_result
                    # Fault injection loses a real accepted acknowledgement, then
                    # restarts the primary stores. The child still owns real Anki.
                    manifest=await call('get_workspace',{'workspace':workspace})
                    await call('patch_cards',{'workspace':workspace,'patches':[{'id':'fibroblast','changes':{'action':'create','note_id':None,'card_ids':[],'media':[],'fields':{'Front':'Where is collagen made?','Back':'Fibroblasts'},'tier':1}}],'expected_revision':manifest['revision']})
                    third=await call('start_student_run',{'workspace':workspace,'pages':[1]});third_id=third['id']
                    another={**decision,'concept_id':'second-synthetic-concept'}
                    await call('record_run_coverage',{'run_id':third_id,'query':'collagen','decisions':[another]})
                    third_p=await call('stage_run',{'run_id':third_id})
                    for role in ('maintainer','student'):
                        ticket=await call('prepare_run_quality',{'run_id':third_id,'content_digest':third_p['content_digest'],'role':role})
                        receipt=synthetic_receipt(ticket,role)
                        if role=='student':await call('release_review_backs',{'run_id':third_id,'content_digest':third_p['content_digest'],'ticket_id':ticket['ticket_id'],'attempts':receipt['attempts']})
                        receipt['attestation']=hmac.new(key,_encoded({'run_id':third_id,'content_digest':third_p['content_digest'],'receipt':receipt}),hashlib.sha256).hexdigest()
                        await call('submit_run_quality',{'run_id':third_id,'content_digest':third_p['content_digest'],'receipt':receipt})
                    third_p=await call('stage_run',{'run_id':third_id})
                    await call('authorize_run',{'run_id':third_id,'proposal_digest':third_p['digest'],'mode':'user'})
                    class LostAcknowledgement:
                        async def list_tools(self):return await observed.list_tools()
                        async def call_tool(self,name,args):
                            response=await observed.call_tool(name,args)
                            if name=='conditional_student_operation' and not response.isError:raise TimeoutError('LOCAL FAULT: lost real acknowledgement')
                            return response
                    @asynccontextmanager
                    async def lossy():yield AnkiAdapter(LostAcknowledgement(),profile='Synthetic',collection_path=str(root/'collection.anki2'))
                    service.companion_connection=lossy
                    dispatch_run=third_id;dispatch_digest=third_p['digest']
                    uncertain=await call('apply_run',{'run_id':third_id,'proposal_digest':third_p['digest']})
                    assert uncertain['counts']['uncertain_operations']==1,uncertain
                    sent_before_restart=len(dispatches)
                    fresh=Service(root/'workspaces',[root],browser='chromium');fresh.companion_connection=connection
                    try:
                        recovered=await Coordinator(fresh).reconcile(third_id)
                        assert recovered['counts']['uncertain_operations']==1
                        replayed=await Coordinator(fresh).apply(third_id,third_p['digest'])
                        assert replayed['counts']['uncertain_operations']==1
                        assert len(dispatches)==sent_before_restart
                        async with connection() as adapter:assert len(await adapter.search_notes('tag:#AnkiPlus::*'))==4
                    finally:fresh.close()
                    # Actual OCR and local inert Chromium helpers in the same
                    # installed package, still with no runtime network or mounts.
                    from PIL import Image,ImageDraw,ImageFont
                    picture=Image.new('RGB',(800,200),'white')
                    ImageDraw.Draw(picture).text((60,60),'Nucleus',fill='black',font=ImageFont.load_default(size=60))
                    picture.save(root/'label.png')
                    image_workspace=await call('create_workspace',{'mode':'cards'})
                    imported=await call('import_image',{'workspace':image_workspace['id'],'path':str(root/'label.png')})
                    ocr_job=await call('ocr_image',{'workspace':image_workspace['id'],'artifact':imported['artifact']})
                    for _ in range(300):
                        ocr=await call('get_job',{'workspace':image_workspace['id'],'job_id':ocr_job['id']})
                        if ocr['status'] not in ('queued','running'):break
                        await asyncio.sleep(.02)
                    assert ocr['status']=='completed' and ocr['result']['region_count']>0,ocr
                    print(json.dumps({'status':'passed','synthetic_only':True,'quality_execution':'SIGNED SYNTHETIC FIXTURE, NOT REVIEWER ACCEPTANCE',
                        'primary':importlib.metadata.version('ankiplusmcp'),'companion_archive_sha256':hashlib.sha256(Path('/artifact/companion.ankiaddon').read_bytes()).hexdigest(),'anki':importlib.metadata.version('anki'),
                        'package':package_name,'verified_note_id':nid,'verified_card_id':cid,'intent_before_every_send':True,'conditional_dispatches':dispatches,'counts':result['counts'],'mixed_basic_native_io_notes':mixed_result['counts']['notes_created'],'restart_uncertain':True,'notes_updated':update_result['counts']['notes_updated'],'cards_unsuspended':reuse_result['counts']['cards_unsuspended'],'media_verified':True,'ocr_regions':ocr['result']['region_count'],'calls':calls},indent=2))
        finally:
            service.close()


if __name__=='__main__':asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else 'addon'))
