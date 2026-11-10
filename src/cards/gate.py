"""Automatic, fail-closed review gate."""
from collections import Counter
from . import check
from .common.paths import Build
from .common.files import read_json, read_jsonl, write_json
from .common.hashing import sha256_file
from .common.errors import Refused, CardsError
from .common.output import Result
from .review.apply import report_path
from .review.parse_report import summary as report_summary


def snapshot(b):
    names=['drafts.jsonl','target.json','source/slides.json','source/objectives.json','skipped.jsonl']
    names += [str(p.relative_to(b.root)) for p in b.path('review').rglob('*') if p.is_file() and (p.name.endswith(('_report.jsonl','_report.md')) or p.name=='apply_log.json')]
    return {name:sha256_file(b.path(name)) if b.path(name).is_file() else None for name in sorted(names)}


def stable(path,data,tool):
    if path.exists():
        old=read_json(path); old.pop('_meta',None)
        if old==data: return
    write_json(path,data,tool)


def run(args):
    b=Build(args.build); state=read_json(b.state)
    rounds=[k for k in (1,2) if b.path(f'review/round{k}').exists()]
    if not rounds:
        raise Refused('E70','review not run','run cards packets and cards apply')
    k=max(rounds); folder=f'review/round{k}/'
    required=[report_path(b,f'review/round{k}',r) for r in ('maintainer','student')]+[b.path(folder+'apply_log.json')]
    if any(not p.is_file() for p in required):
        raise Refused('E70','review reports or apply log missing','complete both reviewers and run cards apply')
    notes=list(read_jsonl(b.path('drafts.jsonl'))); active={n.get('id'):n for n in notes if isinstance(n,dict)}
    applied=read_json(b.path(folder+'apply_log.json'))
    reasons=[]; verdicts={}
    reports={r:report_path(b,f'review/round{k}',r) for r in ('maintainer','student')}
    sections=b.path(folder+'maintainer-sections')
    if sections.exists():
        for section in sorted(sections.iterdir()): reports['section'+section.name]=report_path(b,f'review/round{k}',f'maintainer_section{section.name}')
    for reviewer,name in reports.items():
        if not name.is_file():
            reasons.append(f'{reviewer}: section report missing'); continue
        if name.suffix.lower()=='.md':
            owner='maintainer' if reviewer.startswith('section') else reviewer
            verdict,_=report_summary(name,owner)
        else:
            rows=list(read_jsonl(name))
            if any(not isinstance(r,dict) for r in rows):
                raise CardsError('E70',f'{name}: invalid report record','repair the reviewer JSONL and apply again')
            summaries=[r for r in rows if r.get('type')=='summary']
            verdict=summaries[0].get('verdict') if len(summaries)==1 and rows[-1].get('type')=='summary' else 'INVALID'
        verdicts[reviewer]=verdict
        if verdict not in ('PASS','PASS_WITH_FIXES'): reasons.append(f'{reviewer}: {verdict}')
        if applied.get('report_hashes',{}).get(reviewer)!=sha256_file(name):
            reasons.append(f'{reviewer}: report changed since apply')
    if applied.get('drafts_sha256')!=sha256_file(b.path('drafts.jsonl')): reasons.append('drafts changed since review apply')
    blockers=[r for r in applied.get('open_blockers',[]) if active.get(r.get('note_id'),{}).get('status') not in ('dropped','unresolved')]
    if blockers: reasons.append(f'{len(blockers)} open blockers')
    if applied.get('css_fix_needed'): reasons.append('CSS fixes remain')
    check.run(args)
    validation=read_json(b.path('checks/check.json'))
    if any(f.get('severity')=='blocker' for f in validation['findings']): reasons.append('schema or lint blockers remain')
    notes=[n for n in notes if isinstance(n,dict) and n.get('status')!='dropped' and all(isinstance(n.get(key),str) for key in ('id','kind','status')) and type(n.get('tier')) is int]
    counts=dict(Counter(n['kind'] for n in notes)); counts['tiers']=dict(Counter(str(n['tier']) for n in notes))
    suspended=[n['id'] for n in notes if n['tier']==3 or n['status']=='unresolved']
    data={'status':'failed' if reasons else 'passed','drafts_sha256':sha256_file(b.path('drafts.jsonl')),
          'round':k,'verdicts':verdicts,'open_blockers':blockers,'counts':counts,'write_suspended':suspended,'reasons':reasons,'inputs':snapshot(b)}
    stable(b.path('gate.json'),data,'cards gate')
    state['gate']={'status':data['status'],'drafts_sha256':data['drafts_sha256']}; stable(b.state,{k:v for k,v in state.items() if k!='_meta'},'cards gate')
    return Result('FINDINGS' if reasons else 'OK',reasons[:8] if reasons else [f"gate passed; {len(notes)} notes; {len(suspended)} suspended"],[b.path('gate.json')],int(bool(reasons)))
