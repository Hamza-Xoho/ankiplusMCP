import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow, covered, run
from ankiplusmcp.server import API, create_server


def test_production_review_tools_are_packaged_mcp_apps_with_bound_state(workflow):
    c,s,e,r,d=workflow;covered(workflow);run(c.stage(r.id));api=API(s)
    page=run(api.open_run_review(r.id))
    assert page['workspace']==r.workspace and page['session_token']
    async def inspect():
        server=create_server(s)
        tools={t.name:t for t in await server.list_tools()}
        assert tools['open_run_review'].meta['ui']['resourceUri']=='ui://ankiplus/review.html'
        assert tools['save_run_review'].meta['ui']['visibility']==['app']
        resources=await server.list_resources()
        assert any(str(v.uri)=='ui://ankiplus/review.html' for v in resources)
        result=await server.read_resource('ui://ankiplus/review.html')
        assert result[0].mime_type=='text/html;profile=mcp-app'
        assert 'Review proposed cards' in result[0].content
    run(inspect())


def test_real_sdk_review_ui_edits_excludes_reconnects_and_refuses_stale_tab(workflow):
    import asyncio,inspect,json
    from pathlib import Path
    from playwright.async_api import async_playwright,expect
    from ankiplusmcp.doctor import require_browser
    from cards.render import launch_options
    from test_workflow_quality import quality_ready
    c,s,e,r,d=workflow;covered(workflow);quality_ready(workflow);api=API(s)
    bridge='''<iframe title="AnkiPlus review" style="width:100%;height:1500px;border:0"></iframe><script>
    window.addEventListener('message',async event=>{
      const frame=document.querySelector('iframe');if(event.source!==frame.contentWindow)return;
      const q=event.data;if(q?.jsonrpc!=='2.0')return;
      const send=m=>frame.contentWindow.postMessage({jsonrpc:'2.0',...m},'*');
      if(q.method==='ui/initialize')send({id:q.id,result:{protocolVersion:q.params.protocolVersion,hostInfo:{name:'SYNTHETIC HOST',version:'1'},hostCapabilities:{serverTools:{}},hostContext:{theme:'light'}}});
      else if(q.method==='ui/notifications/initialized')send({method:'ui/notifications/tool-result',params:await hostCall('open_run_review',{})});
      else if(q.method==='tools/call')send({id:q.id,result:await hostCall(q.params.name,q.params.arguments)});
    });</script>'''
    options=launch_options(require_browser('auto'))
    async def browser():
        async def call(name,args):
            if name=='save_run_review':await asyncio.sleep(.2)
            try:
                args={'run_id':r.id,**args};result=getattr(api,name)(**args)
                if inspect.isawaitable(result):result=await result
                return {'content':[{'type':'text','text':json.dumps(result)}],'structuredContent':result}
            except DomainError as exc:return {'isError':True,'content':[{'type':'text','text':str(exc)}]}
        from ankiplusmcp.review_app import html
        async with async_playwright() as pw:
            instance=await pw.chromium.launch(**options)
            try:
                page=await instance.new_page(viewport={'width':1120,'height':1000})
                await page.route('**/*',lambda route:route.abort())
                await page.expose_function('hostCall',call)
                async def connect():
                    await page.set_content(bridge)
                    await page.locator('iframe').evaluate('(frame,html)=>frame.srcdoc=html',html())
                    frame=page.frame_locator('iframe')
                    await expect(frame.get_by_role('button',name='Save decision',exact=True)).to_be_enabled()
                    return frame
                frame=await connect()
                await expect(frame.get_by_text('Fibroblasts make collagen.',exact=True)).to_be_visible()
                await expect(frame.get_by_role('button',name='Approve and apply',exact=True)).to_be_enabled()
                edited='<img src=x onerror="window.executed=true"> Adapted answer'
                await frame.get_by_label('Back for fibroblast').fill(edited)
                await expect(frame.get_by_role('button',name='Approve and apply',exact=True)).to_be_disabled()
                await expect(frame.get_by_role('status')).to_contain_text('Unsaved')
                await frame.get_by_role('button',name='Save decision',exact=True).click()
                await expect(frame.get_by_label('Back for fibroblast')).to_be_disabled()
                await expect(frame.get_by_role('status')).to_contain_text('Saved.')
                assert s.get_cards(r.workspace)['cards'][0]['fields']['Back']==edited
                assert await frame.locator('img').count()==0
                await frame.get_by_label('Decision',exact=True).select_option('exclude')
                await frame.get_by_role('button',name='Save decision',exact=True).click()
                await expect(frame.get_by_role('status')).to_contain_text('Saved.')
                frame=await connect();await expect(frame.get_by_label('Decision',exact=True)).to_have_value('exclude')
                s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'Concurrent edit'}}}],2)
                await frame.get_by_label('Decision',exact=True).select_option('keep')
                await frame.get_by_role('button',name='Save decision',exact=True).click()
                await expect(frame.get_by_role('status')).to_contain_text('STALE')
                await frame.get_by_role('button',name='Reload saved review',exact=True).click()
                await expect(frame.get_by_label('Back for fibroblast')).to_have_value('Concurrent edit')
                output=Path('.artifacts/review-ui');output.mkdir(parents=True,exist_ok=True)
                await frame.locator('main').screenshot(path=str(output/'desktop.png'))
                await page.set_viewport_size({'width':390,'height':1000})
                assert await frame.locator('body').evaluate('(body)=>body.scrollWidth<=innerWidth')
                await frame.locator('main').screenshot(path=str(output/'mobile.png'))
                await frame.get_by_role('button',name='Reload saved review',exact=True).focus()
                await page.keyboard.press('Tab')
                await expect(frame.get_by_role('button',name='Recheck proposal',exact=True)).to_be_focused()
                border_contrast=await frame.locator('textarea').first.evaluate(r'''field=>{
                  const rgb=value=>value.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});
                  const light=value=>rgb(value).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
                  const style=getComputedStyle(field),a=light(style.borderTopColor),b=light(style.backgroundColor);
                  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }''')
                assert border_contrast>=3
                await page.emulate_media(color_scheme='dark',reduced_motion='reduce')
                contrast=await frame.locator('body').evaluate(r'''body=>{
                  const rgb=value=>value.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});
                  const luminance=value=>rgb(value).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
                  const style=getComputedStyle(body),a=luminance(style.color),b=luminance(style.backgroundColor);
                  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }''')
                assert contrast>=4.5
                assert await frame.locator('body').evaluate('(body)=>body.scrollWidth<=innerWidth')
                await frame.locator('main').screenshot(path=str(output/'mobile-dark.png'))
                assert not e.sent
            finally:await instance.close()
    run(browser())


def test_failed_sdk_connection_clears_busy_state_and_announces_recovery():
    from playwright.async_api import async_playwright,expect
    from ankiplusmcp.review_app import html
    from ankiplusmcp.doctor import require_browser
    from cards.render import launch_options
    options=launch_options(require_browser('auto'))
    async def exercise():
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(**options)
            try:
                page=await browser.new_page()
                await page.route('**/*',lambda route:route.abort())
                await page.set_content('''<iframe title="Review"></iframe><script>
                window.addEventListener('message',e=>{const f=document.querySelector('iframe');if(e.source===f.contentWindow&&e.data.method==='ui/initialize')f.contentWindow.postMessage({jsonrpc:'2.0',id:e.data.id,error:{code:-32000,message:'SYNTHETIC disconnected host'}},'*')});</script>''')
                await page.locator('iframe').evaluate('(frame,html)=>frame.srcdoc=html',html())
                frame=page.frame_locator('iframe')
                await expect(frame.get_by_role('status')).to_contain_text('Host connection failed')
                await expect(frame.locator('main')).to_have_attribute('aria-busy','false')
                await expect(frame.locator('#approve')).to_be_disabled()
                await expect(frame.locator('#approve')).not_to_be_visible()
            finally:await browser.close()
    run(exercise())


def test_sdk_approval_preserves_unsaved_choices_and_reports_pending_work(workflow):
    import inspect,json
    from playwright.async_api import async_playwright,expect
    from ankiplusmcp.review_app import html
    from ankiplusmcp.doctor import require_browser
    from cards.render import launch_options
    from test_reconciliation import approved
    c,s,e,r,d=workflow
    run(c.coverage(r.id,'collagen',[d,{'concept_id':'unresolved','disposition':'pending','source_refs':d['source_refs']}]))
    approved(workflow);api=API(s);options=launch_options(require_browser('auto'))
    async def exercise():
        async def call(name,args):
            try:
                value=getattr(api,name)(**{'run_id':r.id,**args})
                if inspect.isawaitable(value):value=await value
                return {'content':[{'type':'text','text':json.dumps(value)}],'structuredContent':value}
            except DomainError as exc:return {'isError':True,'content':[{'type':'text','text':str(exc)}]}
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(**options)
            try:
                page=await browser.new_page();await page.route('**/*',lambda route:route.abort());await page.expose_function('hostCall',call)
                await page.set_content('''<iframe title="Review" style="width:100%;height:1600px"></iframe><script>
                window.addEventListener('message',async e=>{const f=document.querySelector('iframe');if(e.source!==f.contentWindow)return;const q=e.data;const send=m=>f.contentWindow.postMessage({jsonrpc:'2.0',...m},'*');
                if(q.method==='ui/initialize')send({id:q.id,result:{protocolVersion:q.params.protocolVersion,hostInfo:{name:'SYNTHETIC',version:'1'},hostCapabilities:{serverTools:{}},hostContext:{theme:'light'}}});
                else if(q.method==='ui/notifications/initialized')send({method:'ui/notifications/tool-result',params:await hostCall('open_run_review',{})});
                else if(q.method==='tools/call')send({id:q.id,result:await hostCall(q.params.name,q.params.arguments)});});</script>''')
                await page.locator('iframe').evaluate('(frame,html)=>frame.srcdoc=html',html());frame=page.frame_locator('iframe')
                await expect(frame.get_by_role('button',name='Approve and apply',exact=True)).to_be_enabled()
                await frame.get_by_label('Back for fibroblast').fill('Unsaved answer')
                await expect(frame.get_by_role('button',name='Recheck proposal',exact=True)).to_be_disabled()
                await expect(frame.get_by_role('button',name='Next',exact=True)).to_be_disabled()
                await frame.get_by_role('button',name='Reload saved review',exact=True).click()
                await expect(frame.get_by_label('Back for fibroblast')).to_have_value('Fibroblasts')
                await frame.get_by_role('button',name='Approve and apply',exact=True).click()
                await expect(frame.get_by_role('status')).to_contain_text('1 pending decision')
                assert len(e.notes)==1 and e.notes[101]['fields']['Back']=='Fibroblasts'
            finally:await browser.close()
    run(exercise())
