#!/usr/bin/env python3
"""Exercise discovery, source extraction, cards, previews and payloads via stdio.

Run with this environment's Python. Optionally pass the complete server command
following --command, for example --command /path/to/venv/bin/ankiplusmcp ...
"""
import argparse
import asyncio
import sys
import tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def smoke(command):
    async with stdio_client(StdioServerParameters(command=command[0],args=command[1:])) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            listed=await session.list_tools()
            async def call(name, **args):
                response=await session.call_tool(name,args)
                if response.isError: raise RuntimeError(str(response.content))
                return response.structuredContent
            async def job(record, workspace):
                for _ in range(1200):
                    result=await call('get_job',workspace=workspace,job_id=record['id'])
                    if result['status'] not in ('queued','running'):
                        if result['status']!='completed': raise RuntimeError(str(result))
                        return result['result']
                    await asyncio.sleep(.1)
                raise RuntimeError('Job timed out')
            w=await call('create_workspace',mode='lecture',text='# Membrane\n\nSodium crosses channels.')
            ident=w['id']
            await job(await call('extract_source',workspace=ident),ident)
            source=await call('read_source',workspace=ident)
            assert 'Sodium' in source['text']
            w=await call('get_workspace',workspace=ident)
            await call('save_cards',workspace=ident,expected_revision=w['revision'],cards=[{'id':'smoke','fields':{'Text':'Sodium crosses {{c1::channels}}'}}])
            assert not (await call('check_cards',workspace=ident))['blockers']
            rendered=await job(await call('render_cards',workspace=ident),ident)
            response=await session.call_tool('get_image',{'workspace':ident,'artifact':rendered['sheets'][0]['fronts']})
            assert response.content[0].type=='image'
            w=await call('get_workspace',workspace=ident)
            plan=await call('prepare_write',workspace=ident,expected_revision=w['revision'])
            assert plan['created']==1 and plan['performed_anki_operations']==0
            print(f"PASS: {len(listed.tools)} tools; extraction, cards, preview image and payload; no Anki operations")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ankiplus-smoke-') as folder:
        asyncio.run(smoke(args.command or [sys.executable,'-m','ankiplusmcp','--workspace-root',folder,'--source-root',folder]))

if __name__=='__main__': main()
