#!/usr/bin/env python3
"""Prepare synthetic probes; never edit global host config or connect Anki."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

SERVER=r'''"""THROWAWAY compatibility probe. Synthetic state only; no Anki client or listener."""
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from filelock import FileLock
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server

URI='ui://ankiplus-probe/review.html'
MIME='text/html;profile=mcp-app'
INITIAL={'revision':0,'cards':[
    {'id':'sample-a','text':'A synthetic sample to edit','selected':True},
    {'id':'sample-b','text':'A synthetic sample to exclude','selected':True}],
    'performed_anki_operations':0,'sample_only':True}

class ProbeState:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        if self.root.is_symlink(): raise ValueError('Probe data cannot be a symlink')
        self.path=self.root/'state.json'
        self.lock=FileLock(self.root/'.state.lock',timeout=3)
    def _read(self):
        if self.path.is_symlink(): raise ValueError('Probe state cannot be a symlink')
        return json.loads(self.path.read_text()) if self.path.exists() else deepcopy(INITIAL)
    def read(self):
        with self.lock:return self._read()
    def decide(self,expected_revision,decisions):
        with self.lock:
            state=self._read()
            if type(expected_revision) is not int or expected_revision!=state['revision']:raise ValueError('STALE: reopen the current sample')
            if not isinstance(decisions,list) or not 1<=len(decisions)<=2:raise ValueError('Supply 1–2 sample decisions')
            ids={c['id'] for c in state['cards']};seen=set()
            for d in decisions:
                if not isinstance(d,dict) or set(d)!={'id','selected','text'}:raise ValueError('Invalid decision shape')
                if d['id'] not in ids or d['id'] in seen:raise ValueError('Invalid/repeated sample ID')
                if type(d['selected']) is not bool or not isinstance(d['text'],str) or not 1<=len(d['text'].strip())<=2000:raise ValueError('Invalid selection or text')
                seen.add(d['id'])
            for d in decisions:
                next(c for c in state['cards'] if c['id']==d['id']).update(d)
            state['revision']+=1
            fd,name=tempfile.mkstemp(prefix='.state-',dir=self.root)
            try:
                with os.fdopen(fd,'w') as stream:
                    json.dump(state,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
                os.replace(name,self.path)
            finally:Path(name).unlink(missing_ok=True)
            return state

def result(value):
    return types.CallToolResult(content=[types.TextContent(type='text',text=json.dumps(value))],structuredContent=value)

def create_server(data_root):
    state=ProbeState(data_root)
    server=Server('ankiplus-compat-probe',version='0.0.1',instructions='Synthetic compatibility experiment, not AnkiPlus production. No Anki operations. Open the review UI; never claim it rendered from a tool result alone.')
    empty={'type':'object','properties':{},'additionalProperties':False}
    schemas={
        'open_sample_review':empty,
        'read_sample_state':empty,
        'observe_content_channels':empty,
        'save_sample_decisions':{'type':'object','required':['expected_revision','decisions'],'additionalProperties':False,'properties':{
            'expected_revision':{'type':'integer','minimum':0},'decisions':{'type':'array','minItems':1,'maxItems':2,'items':{
                'type':'object','required':['id','selected','text'],'additionalProperties':False,'properties':{
                    'id':{'type':'string','enum':['sample-a','sample-b']},'selected':{'type':'boolean'},'text':{'type':'string','minLength':1,'maxLength':2000}}}}}}}
    @server.list_tools()
    async def tools():
        return [types.Tool(name=name,description={
            'open_sample_review':'Open the synthetic select/edit/exclude review UI. No collection writes.',
            'read_sample_state':'Read persisted synthetic sample selections and revision.',
            'observe_content_channels':'Return deliberately different text/structured markers for host forwarding measurement.',
            'save_sample_decisions':'Save only synthetic selections from the UI; never authorize or write Anki.'}[name],
            inputSchema=schema,
            annotations=types.ToolAnnotations(readOnlyHint=name!='save_sample_decisions',destructiveHint=False,openWorldHint=False),
            _meta={'ui/resourceUri':URI,'ui':{'resourceUri':URI,**({'visibility':['app']} if name=='save_sample_decisions' else {})}} if name in ('open_sample_review','save_sample_decisions') else None)
            for name,schema in schemas.items()]
    @server.list_resources()
    async def resources():return [types.Resource(uri=URI,name='Synthetic review',mimeType=MIME)]
    @server.read_resource()
    async def read_resource(uri):
        if str(uri)!=URI:raise ValueError('Unknown resource')
        html=Path(__file__).with_name('review.html')
        if not html.is_file():raise ValueError('UI bundle missing; run the preparation build')
        return [ReadResourceContents(html.read_text(),MIME,{'ui':{'csp':{'connectDomains':[],'resourceDomains':[]},'prefersBorder':True}})]
    @server.call_tool()
    async def call(name,arguments):
        # Only controlled synthetic observations; no request metadata/secrets are logged.
        observed={'tool':name}
        client=server.request_context.session.client_params
        if client:observed['client']={'info':client.clientInfo.model_dump(),'capabilities':client.capabilities.model_dump(exclude_none=True)}
        with (state.root/'observations.jsonl').open('a') as stream:stream.write(json.dumps(observed)+'\n')
        try:
            if name=='observe_content_channels':return types.CallToolResult(content=[types.TextContent(type='text',text='TEXT_CHANNEL_ONLY: indigo')],structuredContent={'STRUCTURED_CHANNEL_ONLY':'copper'})
            if name in ('open_sample_review','read_sample_state'):return result(state.read())
            if name=='save_sample_decisions':return result(state.decide(**arguments))
            raise ValueError('Unknown probe tool')
        except ValueError as exc:return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text=str(exc))])
    return server

async def serve(root):
    server=create_server(root)
    async with stdio_server() as (read,write):await server.run(read,write,server.create_initialization_options())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-root',type=Path,default=Path(__file__).with_name('data'));parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        if not Path(__file__).with_name('review.html').is_file():print('UI bundle missing; run npm ci and npm run build',file=__import__('sys').stderr);return 2
        print('Probe files ready; actual Desktop support remains not_run');return 0
    asyncio.run(serve(args.data_root));return 0
if __name__=='__main__':raise SystemExit(main())
'''

UI=r'''import { App } from '@modelcontextprotocol/ext-apps';
const app=new App({name:'AnkiPlus synthetic compatibility probe',version:'0.0.1'});
let revision;
const status=document.querySelector('#status');
function show(result){
  if(result.isError) throw new Error(result.content?.find(c=>c.type==='text')?.text || 'Tool failed');
  const state=result.structuredContent;
  if(!state?.sample_only) throw new Error('Missing synthetic state');
  revision=state.revision;
  const cards=document.querySelector('#cards');cards.replaceChildren();
  for(const card of state.cards){
    const item=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent=card.id;item.append(legend);
    const label=document.createElement('label');const selected=document.createElement('input');selected.type='checkbox';selected.checked=card.selected;selected.dataset.id=card.id;
    label.append(selected,document.createTextNode(' Keep this sample'));item.append(label);
    const text=document.createElement('textarea');text.value=card.text;text.setAttribute('aria-label',`Text for ${card.id}`);text.maxLength=2000;item.append(text);cards.append(item);
  }
  status.textContent=`Saved revision ${revision}. Synthetic state only; no Anki operations.`;
  document.querySelector('#save').disabled=false;
}
app.ontoolresult=result=>{try{show(result)}catch(error){status.textContent=error.message}};
document.querySelector('#reload').onclick=async()=>{try{show(await app.callServerTool({name:'read_sample_state',arguments:{}}))}catch(error){status.textContent=error.message}};
document.querySelector('#save').onclick=async()=>{
  const button=document.querySelector('#save');button.disabled=true;
  const decisions=[...document.querySelectorAll('fieldset')].map(item=>({id:item.querySelector('input').dataset.id,selected:item.querySelector('input').checked,text:item.querySelector('textarea').value}));
  try{show(await app.callServerTool({name:'save_sample_decisions',arguments:{expected_revision:revision,decisions}}))}
  catch(error){status.textContent=error.message+' Reopen the current sample before retrying.'}
};
app.connect().catch(error=>{status.textContent='Host connection failed: '+error.message});
'''

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic review probe</title>
<style>body{font:16px system-ui,sans-serif;margin:0;padding:24px;color:#17221e;background:#f7f8f5}main{max-width:680px;margin:auto}h1{font-size:23px;margin:0 0 12px}p{line-height:1.5}fieldset{border:1px solid #aebbb3;border-radius:6px;margin:18px 0;padding:14px}legend{font-weight:650}label{display:block;margin-bottom:10px}textarea{box-sizing:border-box;width:100%;min-height:88px;font:inherit;padding:10px;border:1px solid #78867c;border-radius:3px}button{font:inherit;padding:10px 16px;border:1px solid #174f3d;border-radius:4px;background:#174f3d;color:white;margin-right:8px}button:disabled{opacity:.5}button:focus-visible,textarea:focus-visible,input:focus-visible{outline:3px solid #db9c33;outline-offset:3px}#status{min-height:3em}small{display:block;margin-top:18px}</style>
<main><h1>Synthetic card review</h1><p>Test whether this host supports selecting, editing and excluding sample text. Nothing here approves or changes an Anki collection.</p><div id="cards"></div><p id="status" role="status">Waiting for the Desktop host…</p><button id="save" disabled>Save sample decisions</button><button id="reload">Reload saved state</button><small>Compatibility experiment only. Not the production review interface.</small></main><script>__BUNDLE__</script></html>'''

BUILD=r'''import { build } from 'esbuild';
import { readFileSync,writeFileSync } from 'node:fs';
const built=await build({entryPoints:['review.js'],bundle:true,write:false,format:'iife',platform:'browser',target:'es2022',minify:true,legalComments:'inline'});
const js=built.outputFiles[0].text.replaceAll('</script','<\\/script');
writeFileSync('review.html',readFileSync('review.template.html','utf8').replace('__BUNDLE__',()=>js));
console.log('Built self-contained probe UI; no external runtime resources.');
'''


def prepare(output: Path) -> dict:
    output=Path(output).absolute()
    if any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('Use a real output directory, not a symlink')
    output.mkdir(parents=True,exist_ok=False)
    package={'name':'ankiplus-compat-probe','version':'0.0.1','private':True,'type':'module','scripts':{'build':'node build.mjs'},'dependencies':{'@modelcontextprotocol/ext-apps':'2.0.4'},'devDependencies':{'esbuild':'0.28.2'}}
    for name,text in {'probe_server.py':SERVER,'review.js':UI,'review.template.html':HTML,'build.mjs':BUILD,'package.json':json.dumps(package,indent=2)+'\n'}.items():(output/name).write_text(text,encoding='utf-8')
    lock=ROOT/'docs/refactor/desktop-experiment-package-lock.json'
    if lock.is_file():(output/'package-lock.json').write_bytes(lock.read_bytes())
    registration={'mcpServers':{'ankiplus-compat-probe':{'command':sys.executable,'args':[str(output/'probe_server.py'),'--data-root',str(output/'data')]}}}
    (output/'registration.json').write_text(json.dumps(registration,ensure_ascii=False,indent=2)+'\n')
    (output/'.mcp.json').write_bytes((output/'registration.json').read_bytes())
    report={'schema_version':1,'root':str(output),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'performed_anki_operations':0,'desktop_compatibility':'not_run','reviewer_execution':'not_run','independent_reviewers':{'status':'not_run'},'companion':{'status':'not_run','operations':[],'mutation_authorization':'not_granted; separate explicit isolated-profile authorization required'}}
    report['source_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    report['generated_sha256']={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
        for name in ('probe_server.py','review.js','review.template.html','build.mjs','package.json','package-lock.json','.mcp.json')}
    (output/'experiment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    template={'overall_status':'not_run','source':{'revision':report['revision'],'dirty':report['source_dirty']},
        'environment':{'macOS':None,'architecture':None,'desktop_app':None,'code_runtime':None,'subscription':None},
        'surfaces':{surface:{'execution_location':None,'embedded_review':'not_run','edit_exclude':'not_run',
            'reconnect':'not_run','stale_refusal':'not_run','ui_click_model_turn':'not_measured',
            'content_channels':'not_run','evidence':[]} for surface in ('chat','code','cowork')},
        'reviewers':{'status':'not_run','blind_recall':'unverified_parallel_front_back_exposure','maintainer':{'agent_id':None,'model':None,'effort':None,'report':None,'transcript':None},
            'student':{'agent_id':None,'model':None,'effort':None,'report':None,'transcript':None},'provenance_verified':False},
        'companion':{'status':'not_run','version':None,'transport':None,'tool_schema_file':None,
            'capability_matrix':None,'writes':'not_authorized','performed_anki_operations':0},
        'host_config':{'backup':None,'only_probe_entry_changed':'not_run','scoped_cleanup':'not_run'},
        'combined_workflow':'unverified','unresolved':[]}
    (output/'HOST-RESULTS.template.json').write_text(json.dumps(template,indent=2)+'\n')
    return report


def prepare_reviewers(output: Path) -> dict:
    """Render real synthetic sheets and reuse the engine's allowlisted packet builder."""
    from types import SimpleNamespace
    from cards.common.files import write_json, write_jsonl, write_text
    from cards.check import run as check
    from cards.render import ASSETS, render_rows
    from cards.render.templates import fill
    from cards.review.packets import TEMPLATES, run as packets
    output=Path(output).absolute(); build=output/'reviewer-build'
    build.mkdir(exist_ok=False)
    source_tag='#ColdRecall::#Source::COMPAT::L001'
    target={'deck':'Synthetic compatibility','note_type':'ColdRecall Cloze','source_tag':source_tag,'tier_tags':{str(i):f'#ColdRecall::!Tier::{i}' for i in (1,2,3)}}
    write_json(build/'build.json',{'review':{}},'compatibility probe')
    write_json(build/'target.json',target,'compatibility probe')
    write_json(build/'source/slides.json',{'slide_count':1,'slides':[{'n':1,'title':'Fibroblast','text':'Fibroblasts have basophilic cytoplasm and an oval nucleus.','figures':[],'flags':[]}]},'compatibility probe')
    write_text(build/'source/map.md','# Synthetic source\n1 Fibroblast','compatibility probe')
    write_json(build/'source/objectives.json',{'objectives':[{'id':'ILO1','text':'Describe fibroblast cytoplasm and nucleus','slide':1}]},'compatibility probe')
    notes=[]
    for ident,adjective in [('n001','basophilic'),('n002','eosinophilic')]:
        notes.append({'id':ident,'kind':'cloze','notetype':target['note_type'],'deck':target['deck'],
            'fields':{'Text':f'<b>Fibroblast</b> cytoplasm is {{{{c1::{adjective}}}}}','Extra':'Synthetic source, slide 1'},
            'tags':[source_tag,'#ColdRecall::!Tier::1'],'tier':1,'objective':'ILO1','source_ref':[1],'group':ident,
            'action':'create','nid':None,'status':'draft'})
    write_jsonl(build/'drafts.jsonl',notes,'compatibility probe');write_jsonl(build/'skipped.jsonl',[],'compatibility probe')
    check(SimpleNamespace(build=build))
    from ankiplusmcp.doctor import require_browser
    front=(ASSETS/'front.html').read_text();back=(ASSETS/'back.html').read_text()
    previews=[]
    for note in notes:
        question=fill(front,note['fields'],note['tags'],1,'front')
        answer=fill(back,note['fields'],note['tags'],None,'back',question)
        previews.append({'id':note['id'],'question':question,'answer':answer})
    render_rows(previews,build,browser=require_browser('auto'))
    packets(SimpleNamespace(build=build,round=1,only=None,student_subset='all'))
    base=build/'review/round1'
    # The probe validates independent packet execution, not collection searching.
    # No companion is connected; actual search compatibility is a separate gate.
    write_text(base/'maintainer/reconcile.md','# Synthetic collection context\nNo premade or existing notes are supplied in this isolated fixture. No collection connection is authorized for this probe.\n','compatibility probe')
    for role in ('maintainer','student'):
        for name in ('rubric.md','brief.md','report-format.md'):
            (base/role/name).write_bytes((TEMPLATES/role/name).read_bytes())
        prompt=base/role/'PROMPT.md'
        prompt.write_text(prompt.read_text().replace(f'Use anki-{role}.',f'Use compat-{role}.').replace('Run reconcile.md searches instead of existing.jsonl.','Read reconcile.md for the supplied synthetic collection context.'))
    agents=output/'.claude/agents';agents.mkdir(parents=True,exist_ok=True)
    hashes={}
    for role in ('maintainer','student'):
        original=(ROOT/f'.claude/agents/anki-{role}.md').read_text()
        header,body=original.split('---',2)[1:]
        lines=[]
        for line in header.strip().splitlines():
            if line.startswith('name:'):line=f'name: compat-{role}'
            elif line.startswith('description:'):line=f'description: Run only when explicitly asked for the synthetic independent {role} compatibility probe with a packet PROMPT.md path.'
            elif line.startswith('tools:'):line='tools: Read, Write'
            lines.append(line)
        (agents/f'compat-{role}.md').write_text('---\n'+'\n'.join(lines)+'\n---'+body)
        hashes[role]=hashlib.sha256(original.encode()).hexdigest()
    (output/'CLAUDE.md').write_text('This is a synthetic compatibility experiment. Use the named compat-maintainer/compat-student agents only when explicitly requested, supplying only the packet PROMPT.md path. Each starts fresh and reads only its packet. Reports remain at their named paths. Anki operations are unauthorized here. Read EXPECTATIONS.md only after both reports have been saved; it is evaluator-only input.\n')
    # Never pass the answer key or author discussion to either reviewer.
    (output/'EXPECTATIONS.md').write_text('Evaluator only, after reports: n002 contradicts the supplied source (eosinophilic versus basophilic). The maintainer should detect the source-fidelity defect. Student review must record front answers and inspect all sheets; there is no predetermined visual verdict. Cannot verify blind recall: the preserved packet requests fronts and backs in the same parallel read turn. Fresh reviewer execution may be proven, but blind-answer timing remains unverified pending an explicit decision about staged image exposure. Neither report is independent merely because its filename exists. Save agent IDs/model/effort and the actual input prompt/transcript provenance separately.\n')
    info={'maintainer':str(base/'maintainer'),'student':str(base/'student'),'agent_source_hashes':hashes,'independently_verified':False,
        'blind_recall_evidence':'blocked_by_existing_parallel_image_packet'}
    (output/'reviewer-packets.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'.artifacts/compatibility/desktop-probe');parser.add_argument('--build-ui',action='store_true');parser.add_argument('--reviewers',action='store_true');args=parser.parse_args(argv)
    try:
        report=prepare(args.output)
        if args.build_ui:
            subprocess.run(['npm','ci','--no-audit','--no-fund'],cwd=report['root'],check=True)
            subprocess.run(['npm','run','build'],cwd=report['root'],check=True)
            report['generated_sha256']['review.html']=hashlib.sha256((Path(report['root'])/'review.html').read_bytes()).hexdigest()
        if args.reviewers: report['reviewer_packets']=prepare_reviewers(Path(report['root']))
        (Path(report['root'])/'experiment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
