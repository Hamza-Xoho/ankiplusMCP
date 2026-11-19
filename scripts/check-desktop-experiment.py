#!/usr/bin/env python3
"""Check the disposable probe against stdio and an emulated host, never Desktop/Anki."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def schema_measurement(tools):
    data=json.dumps(tools,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return {'tool_count':len(tools),'utf8_bytes':len(data),
            'serialization':'compact JSON, ensure_ascii=False, entire tools array',
            'tokenizer':'not_measured','host_context_loading':'not_measured'}


async def protocol(root,output):
    measurements={}
    for name,args in [('probe',[str(root/'probe_server.py'),'--data-root',str(output/'stdio-state')]),
                      ('production',['-m','ankiplusmcp','serve','--workspace-root',str(output/'schema-only-workspaces')])]:
        params=StdioServerParameters(command=sys.executable,args=args,env=dict(os.environ))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                listed=await session.list_tools()
                tools=[t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in listed.tools]
                (output/f'{name}-tools.json').write_text(json.dumps(tools,ensure_ascii=False,indent=2)+'\n')
                measurements[name]=schema_measurement(tools)
                if name=='probe':
                    resource=await session.read_resource('ui://ankiplus-probe/review.html')
                    assert resource.contents[0].mimeType=='text/html;profile=mcp-app'
                    assert 'Synthetic card review' in resource.contents[0].text
                    channels=await session.call_tool('observe_content_channels',{})
                    (output/'channel-result.json').write_text(channels.model_dump_json(by_alias=True,exclude_none=True)+'\n')
                    assert channels.structuredContent=={'STRUCTURED_CHANNEL_ONLY':'copper'}
                    assert channels.content[0].text=='TEXT_CHANNEL_ONLY: indigo'
    return measurements


# Minimal JSON-RPC host emulator. Real App SDK runs inside the iframe; this is
# explicitly not evidence about Claude's embedding, permissions or model context.
BRIDGE='''<iframe title="Synthetic MCP App" style="width:100%;height:1000px;border:0"></iframe>
<script>
window.rpcMethods=[];
window.addEventListener('message',async event=>{
 const frame=document.querySelector('iframe');if(event.source!==frame.contentWindow)return;
 const request=event.data;if(request?.jsonrpc!=='2.0')return;
 rpcMethods.push(request.method);
 const send=message=>frame.contentWindow.postMessage({jsonrpc:'2.0',...message},'*');
 if(request.method==='ui/initialize'){
  send({id:request.id,result:{protocolVersion:request.params.protocolVersion,
    hostInfo:{name:'LOCAL EMULATED HOST',version:'0.0.1'},hostCapabilities:{serverTools:{}},hostContext:{theme:'light'}}});
 }else if(request.method==='ui/notifications/initialized'){
  send({method:'ui/notifications/tool-result',params:await window.hostCall('read_sample_state',{})});
 }else if(request.id!==undefined){
  if(request.method==='tools/call')send({id:request.id,result:await window.hostCall(request.params.name,request.params.arguments)});
  else send({id:request.id,error:{code:-32601,message:'Unsupported emulator method'}});
 }
});
</script>'''


def browser(root,output):
    from playwright.sync_api import sync_playwright, expect
    from ankiplusmcp.doctor import require_browser
    from cards.render import launch_options
    spec=importlib.util.spec_from_file_location('disposable_probe',root/'probe_server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    state=module.ProbeState(output/'browser-state');calls=[]
    def call(name,args):
        calls.append(name)
        try:
            if name=='read_sample_state':result=state.read()
            elif name=='save_sample_decisions':result=state.decide(**args)
            else:raise ValueError('Unexpected emulator tool')
            return {'content':[{'type':'text','text':json.dumps(result)}],'structuredContent':result}
        except ValueError as exc:return {'isError':True,'content':[{'type':'text','text':str(exc)}]}
    options=launch_options(require_browser('auto'))
    with sync_playwright() as pw:
        instance=pw.chromium.launch(**options)
        try:
            page=instance.new_page(viewport={'width':900,'height':1100})
            page.route('**/*',lambda route:route.abort())
            page.expose_function('hostCall',call)
            def connect():
                page.set_content(BRIDGE)
                page.locator('iframe').evaluate('(frame,html)=>frame.srcdoc=html',(root/'review.html').read_text())
                frame=page.frame_locator('iframe')
                expect(frame.get_by_role('button',name='Save sample decisions')).to_be_enabled()
                return frame
            frame=connect()
            edited='<img src=x onerror="window.executed=true"> Edited synthetic sample'
            frame.get_by_label('Text for sample-a').fill(edited)
            frame.locator('input[data-id="sample-b"]').uncheck()
            frame.get_by_role('button',name='Save sample decisions').click()
            expect(frame.get_by_role('status')).to_contain_text('Saved revision 1')
            assert state.read()['cards'][0]['text']==edited
            assert state.read()['cards'][1]['selected'] is False
            assert frame.locator('img').count()==0
            assert page.evaluate('document.querySelector("iframe").contentWindow.executed') is None
            # Recreate iframe/handshake, retaining only server-side state.
            frame=connect()
            expect(frame.get_by_label('Text for sample-a')).to_have_value(edited)
            expect(frame.locator('input[data-id="sample-b"]')).not_to_be_checked()
            state.decide(1,[{'id':'sample-a','text':'Concurrent revision','selected':True}])
            frame.get_by_role('button',name='Save sample decisions').click()
            expect(frame.get_by_role('status')).to_contain_text('STALE')
            assert state.read()['revision']==2
            frame.get_by_role('button',name='Reload saved state').click()
            expect(frame.get_by_role('status')).to_contain_text('Saved revision 2')
            page.set_viewport_size({'width':390,'height':1100})
            assert frame.locator('body').evaluate('(body)=>body.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/'emulated-host.png'),full_page=True)
            methods=page.evaluate('window.rpcMethods')
            assert 'ui/message' not in methods and 'ui/update-model-context' not in methods
            return {'status':'passed','host':'local emulator, not Claude',
                    'checks':['edit','exclude','persist/reconnect','stale refusal','reload','inert text','390px layout'],
                    'rpc_methods':methods,'tool_calls':calls,'performed_anki_operations':0}
        finally:instance.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not (args.root/'review.html').is_file():parser.error('Build the disposable UI first')
    args.output.mkdir(parents=True,exist_ok=False)
    report={'status':'local_probe_verified','desktop_compatibility':'not_run',
            'independent_reviewers':'not_run','companion':'not_run','performed_anki_operations':0}
    report['prepared_source']=json.loads((args.root/'experiment.json').read_text())
    report['bundle_sha256']=hashlib.sha256((args.root/'review.html').read_bytes()).hexdigest()
    report['schemas']=asyncio.run(protocol(args.root,args.output))
    report['browser_emulator']=browser(args.root,args.output)
    (args.output/'local-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
