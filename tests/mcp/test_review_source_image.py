"""Actual cited PDF page images are available through the bound production App."""
import asyncio
import base64
import pytest
from test_coordinator import workflow,run
from test_sources import wait
from ankiplusmcp.server import API
from ankiplusmcp.review_session import ReviewSession
from ankiplusmcp.store import DomainError


def pdf_run(workflow):
    import pymupdf
    c,s,e,r,d=workflow
    pdf=s.store.root.parent/'image-evidence.pdf'
    with pymupdf.open() as doc:
        page=doc.new_page(width=400,height=300)
        page.draw_rect((20,20,180,180),color=(0,0,1),fill=(0,0,1))
        page.insert_text((30,230),'Fibroblasts make collagen.')
        doc.save(pdf)
    w=s.store.create('lecture',source_path=str(pdf))['id'];wait(s,w,s.extract_source(w))
    s.save_cards(w,[s._cards(r.workspace)[0]],0);r=c.start(w,[1])
    d={**d,'source_refs':[{'source_hash':s.store.get(w)['source']['sha256'],'page':1}]}
    run(c.coverage(r.id,'collagen',[d]));run(c.stage(r.id))
    return c,s,e,r,d


def test_cited_page_image_is_bound_to_current_session_and_exact_reference(workflow):
    c,s,e,r,d=pdf_run(workflow);api=API(s);view=run(ReviewSession(c).open(r.id))
    args={'run_id':r.id,'session_token':view['session_token'],'expected_review_digest':view['digest'],'concept_id':'fibroblast','reference_index':0}
    value=api.read_run_review_source_image(**args)
    assert value.content[0].type=='image' and value.content[0].mimeType=='image/png'
    assert base64.b64decode(value.content[0].data).startswith(b'\x89PNG')
    with pytest.raises(DomainError,match='SESSION'):api.read_run_review_source_image(**{**args,'session_token':'forged'})
    with pytest.raises(DomainError,match='STALE'):api.read_run_review_source_image(**{**args,'expected_review_digest':'old'})
    with pytest.raises(DomainError,match='SOURCE_REF'):api.read_run_review_source_image(**{**args,'reference_index':1})
    assert not e.sent


def test_real_review_app_displays_the_bound_cited_pdf_image(workflow):
    import inspect,json
    from playwright.async_api import async_playwright,expect
    from ankiplusmcp.review_app import html
    from ankiplusmcp.doctor import require_browser
    from cards.render import launch_options
    c,s,e,r,d=pdf_run(workflow);api=API(s);options=launch_options(require_browser('auto'))
    async def exercise():
        async def call(name,args):
            try:
                value=getattr(api,name)(**{'run_id':r.id,**args})
                if inspect.isawaitable(value):value=await value
                if hasattr(value,'content'):return value.model_dump(mode='json',by_alias=True,exclude_none=True)
                return {'content':[{'type':'text','text':json.dumps(value)}],'structuredContent':value}
            except DomainError as exc:
                error={'status':'error','error':{'code':exc.code,'message':str(exc),'remedy':exc.remedy}}
                return {'isError':True,'content':[{'type':'text','text':json.dumps(error)}],'structuredContent':error}
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(**options)
            try:
                page=await browser.new_page(viewport={'width':390,'height':1000})
                await page.route('**/*',lambda route:route.abort());await page.expose_function('hostCall',call)
                await page.set_content('''<iframe title="Review" style="width:100%;height:1600px;border:0"></iframe><script>
                window.addEventListener('message',async e=>{const f=document.querySelector('iframe');if(e.source!==f.contentWindow)return;const q=e.data;const send=m=>f.contentWindow.postMessage({jsonrpc:'2.0',...m},'*');
                if(q.method==='ui/initialize')send({id:q.id,result:{protocolVersion:q.params.protocolVersion,hostInfo:{name:'SYNTHETIC',version:'1'},hostCapabilities:{serverTools:{}},hostContext:{theme:'light'}}});
                else if(q.method==='ui/notifications/initialized')send({method:'ui/notifications/tool-result',params:await hostCall('open_run_review',{})});
                else if(q.method==='tools/call')send({id:q.id,result:await hostCall(q.params.name,q.params.arguments)});});</script>''')
                await page.locator('iframe').evaluate('(frame,html)=>frame.srcdoc=html',html())
                frame=page.frame_locator('iframe')
                await frame.get_by_role('button',name='View PDF page 1',exact=True).click()
                image=frame.get_by_role('img',name='image-evidence.pdf, PDF page 1',exact=True)
                await expect(image).to_be_visible()
                assert await image.evaluate('(image)=>image.complete&&image.naturalWidth>0')
                assert await frame.locator('body').evaluate('(body)=>body.scrollWidth<=innerWidth')
                from pathlib import Path
                output=Path('.artifacts/review-ui');output.mkdir(parents=True,exist_ok=True)
                height=await frame.locator('body').evaluate('(body)=>body.scrollHeight')
                await page.locator('iframe').evaluate('(frame,height)=>frame.style.height=(height+50)+"px"',height)
                await frame.locator('main').screenshot(path=str(output/'source-image-mobile.png'))
                s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'Concurrent edit'}}}],1)
                await frame.get_by_role('button',name='View PDF page 1',exact=True).click()
                await expect(frame.get_by_role('status')).to_contain_text('source view changed')
                assert '{' not in await frame.get_by_role('status').text_content()
                assert not e.sent
            finally:await browser.close()
    run(exercise())
