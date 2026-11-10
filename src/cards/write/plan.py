"""Serialize exactly the gated notes into small AnkiMCP batches."""
from collections import defaultdict
import json
from cards.common.paths import Build
from cards.common.files import read_json, read_jsonl, write_json, _write
from cards.common.hashing import sha256_file
from cards.common.errors import Refused
from cards.common.output import Result
from .importfile import emit, validate_header


def exact(path,data):
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if not path.exists() or path.read_text()!=text: _write(path,text)


def run(args):
    b=Build(args.build); state=read_json(b.state)
    if not b.path('gate.json').is_file() or state.get('gate',{}).get('status')!='passed':
        raise Refused('E71','gate not passed','run cards gate')
    g=read_json(b.path('gate.json'))
    if g.get('status')!='passed' or g.get('drafts_sha256')!=sha256_file(b.path('drafts.jsonl')) or state['gate'].get('drafts_sha256')!=g.get('drafts_sha256'):
        raise Refused('E71','gate stale: drafts changed or gate not passed','repeat review and cards gate')
    latest=max((k for k in (1,2) if b.path(f'review/round{k}').exists()),default=0)
    if g.get('round')!=latest or state.get('review',{}).get('round')!=g.get('round'):
        raise Refused('E71','gate stale: a new review round started','complete the latest review and run cards gate')
    inputs=g.get('inputs',{})
    if not inputs or any((sha256_file(b.path(p)) if b.path(p).is_file() else None)!=h for p,h in inputs.items()):
        raise Refused('E71','gate stale: review or validation inputs changed','run cards gate again')
    current={str(p.relative_to(b.root)) for p in b.path('review').rglob('*') if p.is_file() and (p.name.endswith(('_report.jsonl','_report.md')) or p.name=='apply_log.json')}
    if current!={p for p in inputs if p.startswith('review/')}:
        raise Refused('E71','gate stale: review changed','run cards gate again')
    notes=[n for n in read_jsonl(b.path('drafts.jsonl')) if n['status']!='dropped']
    groups=defaultdict(list); updates=[]
    for n in notes:
        if n['action']=='update': updates.append({'note_id':n['nid'],'fields':n['fields']})
        else: groups[(n['deck'],n['notetype'])].append(n)
    payloads=[]; imports=[]
    for (deck,model),ns in sorted(groups.items()):
        validate_header(deck,model)
        for offset in range(0,len(ns),100):
            payloads.append({'deck_name':deck,'model_name':model,'notes':[{'fields':n['fields'],'tags':n['tags']} for n in ns[offset:offset+100]]})
        imports.append((deck,model,ns))
    # Preflight every output path before creating any artifact.
    names=[f'write/batches/{i:02d}.json' for i in range(1,len(payloads)+1)]
    importnames=['write/import.txt' if i==0 else f'write/import-{i+1:02d}.txt' for i in range(len(imports))]
    for p in names+importnames+['write/updates.json','write/suspend.json','write/expected.json','write/provenance.json']: b.path(p)
    for p,data in zip(names,payloads): exact(b.path(p),data)
    for p,(deck,model,ns) in zip(importnames,imports): emit(b.path(p),ns,deck,model)
    keep={b.path(p) for p in names+importnames}
    for p in [*b.path('write/batches').glob('*.json'),*b.path('write').glob('import*.txt')]:
        resolved=b.path(str(p.relative_to(b.root)))
        if resolved not in keep: resolved.unlink()
    exact(b.path('write/updates.json'),updates)
    reason={n['id']:'unresolved' if n['status']=='unresolved' else 'tier3' for n in notes if n['tier']==3 or n['status']=='unresolved'}
    exact(b.path('write/suspend.json'),{'draft_ids':list(reason),'reason':reason})
    target=read_json(b.path('target.json')); search='tag:'+target['source_tag']
    expected={'created':sum(len(v) for v in groups.values()),'updated':len(updates),'suspend_notes':len(reason),
              'verify':[search,search+' -tag:#ColdRecall::!Tier::3 is:suspended']}
    old=read_json(b.path('write/expected.json')) if b.path('write/expected.json').exists() else {}
    if {k:v for k,v in old.items() if k!='_meta'}!=expected: write_json(b.path('write/expected.json'),expected,'cards write')
    provenance={'gate_sha256':sha256_file(b.path('gate.json')),'artifacts':{p:sha256_file(b.path(p)) for p in names+importnames+['write/updates.json','write/suspend.json','write/expected.json']}}
    path=b.path('write/provenance.json')
    old=read_json(path) if path.exists() else {}
    if {k:v for k,v in old.items() if k!='_meta'}!=provenance: write_json(path,provenance,'cards write')
    return Result(lines=[f"{len(payloads)} batches; created {expected['created']}; updated {len(updates)}; suspend {len(reason)}",*expected['verify']],files=[b.path('write/expected.json')])
