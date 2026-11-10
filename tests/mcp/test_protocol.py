import asyncio
import json
import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_discovery_cards_errors_and_images(tmp_path):
    async def run():
        params=StdioServerParameters(command=sys.executable,args=['-m','ankiplusmcp','--workspace-root',str(tmp_path/'work'),'--source-root',str(tmp_path)],env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[2]/'src')})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                listed=await session.list_tools(); names={t.name for t in listed.tools}
                assert {'extract_source','save_cards','render_cards','prepare_write','submit_review','get_image'} <= names
                assert not {'add_notes','card_suspend','find_notes'} & names
                result=await session.call_tool('create_workspace',{'mode':'cards'})
                assert not result.isError
                w=result.structuredContent['id']
                result=await session.call_tool('save_cards',{'workspace':w,'cards':[{'id':'n1','fields':{'Text':'{{c1::Sodium}} crosses a channel'}}],'expected_revision':0})
                assert not result.isError
                bad=await session.call_tool('save_cards',{'workspace':w,'cards':[{'id':'n1','fields':{'Text':'x'}}],'expected_revision':0})
                assert bad.isError and bad.structuredContent['error']['code']=='STALE'
                bad=await session.call_tool('read_artifact',{'workspace':w,'artifact':'../secret'})
                assert bad.isError
                result=await session.call_tool('render_cards',{'workspace':w})
                job=result.structuredContent['id']
                for _ in range(200):
                    response=await session.call_tool('get_job',{'workspace':w,'job_id':job})
                    record=response.structuredContent
                    if record['status'] not in ('queued','running'): break
                    await asyncio.sleep(.05)
                assert record['status']=='completed', record
                result=await session.call_tool('get_image',{'workspace':w,'artifact':record['result']['sheets'][0]['fronts']})
                assert result.content[0].type=='image'
                assert (await session.call_tool('capabilities',{})).structuredContent['anki_connection']=='separate_host_dependency'
    asyncio.run(run())


def test_client_roots_become_source_roots(tmp_path):
    from mcp import types
    allowed=tmp_path/'allowed'; allowed.mkdir()
    inside=allowed/'a.txt'; inside.write_text('hello'); outside=tmp_path/'b.txt'; outside.write_text('x')
    async def roots(context):
        return types.ListRootsResult(roots=[types.Root(uri=allowed.as_uri(),name='allowed')])
    async def run():
        env={k:v for k,v in os.environ.items() if not k.startswith('ANKIPLUS_')}
        env['PYTHONPATH']=str(Path(__file__).resolve().parents[2]/'src')
        params=StdioServerParameters(command=sys.executable,args=['-m','ankiplusmcp','--workspace-root',str(tmp_path/'work')],cwd='/',env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write,list_roots_callback=roots) as session:
                await session.initialize()
                ok=await session.call_tool('create_workspace',{'mode':'lecture','source_path':str(inside)})
                assert not ok.isError, ok.content
                bad=await session.call_tool('create_workspace',{'mode':'lecture','source_path':str(outside)})
                assert bad.isError and bad.structuredContent['error']['code']=='SOURCE'
                caps=await session.call_tool('capabilities',{})
                assert caps.structuredContent['source_roots_origin']=='client'
    asyncio.run(run())


def test_root_cwd_without_roots_grants_nothing(tmp_path):
    f=tmp_path/'a.txt'; f.write_text('x')
    async def run():
        env={k:v for k,v in os.environ.items() if not k.startswith('ANKIPLUS_')}
        env['PYTHONPATH']=str(Path(__file__).resolve().parents[2]/'src')
        params=StdioServerParameters(command=sys.executable,args=['-m','ankiplusmcp','--workspace-root',str(tmp_path/'work')],cwd='/',env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                bad=await session.call_tool('create_workspace',{'mode':'lecture','source_path':str(f)})
                error=bad.structuredContent['error']
                assert bad.isError and error['code']=='SOURCE' and '--source-root' in error['remedy']
                caps=await session.call_tool('capabilities',{})
                assert caps.structuredContent['source_roots_origin']=='none' and caps.structuredContent['source_roots']==[]
    asyncio.run(run())
