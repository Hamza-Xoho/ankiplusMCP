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
