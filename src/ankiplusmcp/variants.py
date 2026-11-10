"""Optional desktop/light samples using the same inert template representation."""
from cards.render.templates import page
from cards.common.paths import Build

def samples(store, workspace, prefix, rows, css, desktop_sample, light, cancel):
    if not desktop_sample and not light: return []
    from playwright.sync_api import sync_playwright
    from cards.render import ASSETS
    from PIL import Image
    css=css if css is not None else (ASSETS/'style.css').read_text()
    result=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            context=browser.new_context(java_script_enabled=False,service_workers='block',accept_downloads=False)
            context.route('**/*',lambda route:route.abort())
            tab=context.new_page()
            for variant,width,count in [('desktop',1024,desktop_sample),('light',390,min(3,len(rows)) if light else 0)]:
                for row in rows[:count]:
                    if cancel(): return result
                    html=page(css,row['question'],Build(store.directory(workspace)),{})
                    if variant=='light':
                        html=html.replace("class='mobile iphone night_mode'","class='mobile iphone'").replace("class='card card1 nightMode night_mode'","class='card card1'")
                    tab.set_viewport_size({'width':width,'height':40})
                    tab.set_content(html,wait_until='load')
                    relative=f'{prefix}/{row["id"]}_{variant}.png'
                    tab.screenshot(path=str(store.path(workspace,relative)),full_page=True,animations='disabled')
                    with Image.open(store.path(workspace,relative)) as im:
                        if im.width>width: im.crop((0,0,width,im.height)).save(store.path(workspace,relative))
                    result.append(relative)
        finally: browser.close()
    return result
