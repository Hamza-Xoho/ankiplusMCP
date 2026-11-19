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
    report=f'# Review Report — anki-{role}\n\n## Note fibroblast — PASS\n'
    if role=='student':report+='**Attempt:** Fibroblasts → right\n'
    report+='\n## Summary\n**Verdict:** PASS\n**Stats:** notes=1, pass=1\n'
    return dict(ticket_id=ticket['ticket_id'],role=role,agent_id=agent,author_agent_id='LOCAL-SYNTHETIC-author',
        model='claude-sonnet-5-5',effort='high' if role=='maintainer' else 'medium',
        launch={'max_turns':14 if role=='maintainer' else 6,'tools':ticket['tools'],'omit_author_context':True},
        reads=reads,attempts_committed_at=committed,attempts={i:'Fibroblasts' for i in ticket['tile_ids']} if role=='student' else {},report=report)


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
                @asynccontextmanager
                async def connection():yield AnkiAdapter(companion_client,profile='Synthetic',collection_path=str(root/'collection.anki2'))
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
                    # Fault injection loses a real accepted acknowledgement, then
                    # restarts the primary stores. The child still owns real Anki.
                    manifest=await call('get_workspace',{'workspace':workspace})
                    await call('patch_cards',{'workspace':workspace,'patches':[{'id':'fibroblast','changes':{'fields':{'Front':'Where is collagen made?'},'tier':1}}],'expected_revision':manifest['revision']})
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
                        async def list_tools(self):return await companion_client.list_tools()
                        async def call_tool(self,name,args):
                            response=await companion_client.call_tool(name,args)
                            if name=='conditional_student_operation' and not response.isError:raise TimeoutError('LOCAL FAULT: lost real acknowledgement')
                            return response
                    @asynccontextmanager
                    async def lossy():yield AnkiAdapter(LostAcknowledgement(),profile='Synthetic',collection_path=str(root/'collection.anki2'))
                    service.companion_connection=lossy
                    uncertain=await call('apply_run',{'run_id':third_id,'proposal_digest':third_p['digest']})
                    assert uncertain['counts']['uncertain_operations']==1,uncertain
                    fresh=Service(root/'workspaces',[root],browser='chromium');fresh.companion_connection=connection
                    try:
                        recovered=await Coordinator(fresh).reconcile(third_id)
                        assert recovered['counts']['uncertain_operations']==1
                        replayed=await Coordinator(fresh).apply(third_id,third_p['digest'])
                        assert replayed['counts']['uncertain_operations']==1
                        async with connection() as adapter:assert len(await adapter.search_notes('tag:#AnkiPlus::*'))==2
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
                        'package':package_name,'counts':result['counts'],'restart_uncertain':True,'ocr_regions':ocr['result']['region_count'],'calls':calls},indent=2))
        finally:
            service.close()


if __name__=='__main__':asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else 'addon'))
