"""Meter command: artifacts contain detail; stdout stays small."""
from datetime import datetime
from pathlib import Path
import re
from cards.common.errors import CardsError
from cards.common.files import read_json, write_json, write_text
from cards.common.paths import Build
from cards.common.output import Result
from .transcript import session, require
from .prices import cost
from .waste import check


def instant(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def resolve(args, state):
    projects=Path.home()/'.claude/projects'
    if args.session:
        p=Path(args.session).expanduser()
        if p.is_file() or p.suffix == '.jsonl' or '/' in args.session: return p
        matches=sorted(projects.glob(f'*/{args.session}.jsonl'))
    else:
        slug=re.sub(r'[^a-zA-Z0-9]', '-', str(Path(args.latest).expanduser().resolve()))
        matches=list((projects/slug).glob('*.jsonl'))
        starts=[instant(h['started_at']).timestamp() for h in state.get('history',[])
                if h['phase']=='P0']
        if starts: matches=[p for p in matches if p.stat().st_mtime >= min(starts)]
        matches=sorted(matches,key=lambda p:(p.stat().st_mtime_ns,p.name),reverse=True)[:1]
    if len(matches)!=1:
        raise CardsError('E81','session: line 1 field transcript not found or ambiguous',
                         'pass --session with the original JSONL path')
    return matches[0]


def summary(s):
    c=s['cost']; count=sum(w['pass'] for w in s['waste'].values())
    if c['unknown_prices']:
        price='cost n/a (no price for '+', '.join(c['unknown_prices'])+')'
    else:
        names={'claude-sonnet-4-6':'Sonnet 4.6','claude-sonnet-5-5':'Sonnet 5.5'}
        model=', '.join(names.get(m,m) for m in c['model'].split(', '))
        price=f'≈${c["usd"]:.2f} ({model} prices)'
    waste='8/8 pass' if count==8 else f'{count}/8 — '+', '.join(
        f'{k} failed ({v["evidence"][0]["reason"]})' for k,v in s['waste'].items() if not v['pass'])
    return f'Usage: {len(s["calls"])} calls · peak {s["peak_ctx"]/1000:.0f}k · {price} · waste checks {waste}'


def markdown(s):
    lines=['# Session usage',summary(s),
           f'Main: {len(s["calls"])} calls; first context {s["first_ctx"]:,}; peak {s["peak_ctx"]:,}.',
           f'Auto-compactions: {sum(c["trigger"]=="auto" for c in s["compactions"])}; subagents: {len(s["subagents"])}.',
           f'Totals (all agents): {s["all_totals"]}.']
    for a in s['subagents']:
        lines.append(f'Subagent {a["id"]}: {a["type"]}; fork={a["is_fork"]}; first={a["first_ctx"]:,}; calls={len(a["calls"])}.')
    for k,v in s['waste'].items():
        lines.append(f'{k}: '+('PASS' if v['pass'] else f'FAIL ({len(v["evidence"])} evidence rows)'))
    lines+=['','## Calls','Agent | Call | Time | Model | Input | Cache write | Cache read | Output | Context | Tools',
            '--- | --- | --- | --- | --- | --- | --- | --- | --- | ---']
    for label,agent in [('main',s),*[(a['id'],a) for a in s['subagents']]]:
        for c in agent['calls']:
            lines.append(' | '.join(str(x) for x in [label,c['idx'],c['ts'],c['model'],c['input'],c['cache_write'],c['cache_read'],c['output'],c['ctx'],', '.join(c['tools'])]))
        lines.append(f'{label} totals: {agent["totals"]}')
    lines+=['','## Compactions']+[str(c) for c in s['compactions']]
    lines+=['','## Waste evidence']
    for k,w in s['waste'].items():
        for e in w['evidence']: lines.append(f'{k}: call {e["idx"]}; {e["tool"]}; {e["excerpt"]}; {e["reason"]}')
    lines+=['','## Phase attribution']+[f'{k}: {v}' for k,v in s['phases'].items()]
    return '\n'.join(lines)+'\n'


def allowances(s, build, state):
    if build is None: return
    slide_file=build.path('source/slides.json')
    flagged=set()
    if slide_file.exists():
        for slide in read_json(slide_file).get('slides',[]):
            if slide.get('flags'): flagged.add(slide['n'])
    check_file=build.path('checks/check.json')
    sheets=set()
    if check_file.exists():
        for finding in read_json(check_file).get('findings',[]):
            # Only an exact file reference is an allowance, never an arbitrary lint warning.
            if isinstance(finding.get('file'),str): sheets.add(finding['file'])
    for e in s['events']:
        if e['tool']!='Read': continue
        file=e['input'].get('file_path','')
        normalized=file.replace('\\','/')
        source=state.get('source',{}).get('path')
        if file.lower().endswith('.pdf') and (not source or file==source):
            pages=e['input'].get('pages','')
            selected=set()
            if isinstance(pages,str) and re.fullmatch(r'\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*',pages):
                for item in pages.split(','):
                    bounds=[int(x) for x in item.split('-')]
                    if bounds[-1]-bounds[0] <= 10000:
                        selected.update(range(bounds[0],bounds[-1]+1))
            e['allowed_image']=bool(selected) and selected <= flagged
        else:
            # Rendered page images can be matched to the flagged slide number.
            page=re.search(r'(?:^|/)(?:page[-_]?|p)(\d+)\.(?:png|jpg|jpeg)$',normalized)
            e['allowed_image']=bool(page and int(page[1]) in flagged)
        e['allowed_sheet']=any(normalized==f or normalized==str(build.path(f)) for f in sheets)


def validate_state(state, path):
    if not isinstance(state,dict):
        require({},'history',list,path,1)
    history=state.get('history',[])
    require({'history':history},'history',list,path,1)
    for h in history:
        for k in ('phase','status','started_at'):
            require(h,k,str,path,1,'history.')
        try:
            instant(h['started_at'])
            if h.get('ended_at'): instant(h['ended_at'])
        except ValueError as exc:
            raise CardsError('E80',f'{path}: line 1 field history timestamp','repair build history') from exc


def run(args):
    build=Build(args.build) if args.build else None
    state=read_json(build.state) if build and build.state.exists() else {}
    validate_state(state, build.state if build else 'build.json')
    path=resolve(args,state)
    out=Build(args.out)
    # Never replace any source transcript, including subagents, through --out.
    inputs={path.resolve(), *[p.resolve() for p in path.with_suffix('').glob('subagents/*')]}
    if build and build.path('log.jsonl') in inputs:
        exc=CardsError('E82',f'{path}: line 1 field build log overlaps transcript','choose a separate build directory')
        exc.readonly_paths=tuple(inputs)
        raise exc
    if any(out.path(name) in inputs for name in ('cost.json','cost.md')):
        raise CardsError('E82',f'{args.out}: line 1 field out overlaps transcript','choose a separate output directory')
    s=session(path)
    allowances(s,build,state)
    s['waste']=check(s)
    calls=s['calls']+[c for a in s['subagents'] for c in a['calls']]
    s['cost']=cost(calls)
    s['all_totals']={k:sum(c[k] for c in calls) for k in s['totals']}
    s['phases']={}
    for h in state.get('history',[]):
        if h['status']!='done' and any(x['phase']==h['phase'] and x['status']=='done' for x in state['history']): continue
        selected=[c for c in calls if instant(c['ts']) >= instant(h['started_at'])
                  and (not h.get('ended_at') or instant(c['ts']) < instant(h['ended_at']))]
        s['phases'][h['phase']]={'calls':len(selected),'cost':cost(selected)}
    s['image_reads']=[e for e in s['events'] if e['images']]
    write_json(out.path('cost.json'),s,'cards meter')
    write_text(out.path('cost.md'),markdown(s),'cards meter')
    findings=any(not w['pass'] for w in s['waste'].values())
    return Result('FINDINGS' if findings else 'OK',[summary(s)],
                  [] if args.line else [out.path('cost.json'),out.path('cost.md')],
                  int(findings), summary_only=args.line)
