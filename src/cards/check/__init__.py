"""cards check: schema, lint, coverage and statistics."""
import re
from collections import Counter
from ..common.paths import Build
from ..common.files import read_json,write_json
from ..common.source_data import slides_data
from ..common.output import Result
from ..common.errors import CardsError
from .schema import read_rows,validate,validate_skips
from .lint import lint
from .coverage import summarize

def run(args):
    b=Build(args.build)
    slides={s['n'] for s in slides_data(b)['slides']}
    target=read_json(b.path('target.json'))
    objective_data=read_json(b.path('source/objectives.json'))
    objectives=objective_data.get('objectives') if isinstance(objective_data,dict) else None
    if (not isinstance(target,dict) or not all(k in target for k in ('deck','note_type','source_tag','tier_tags'))
        or not isinstance(target['tier_tags'],dict) or not isinstance(objectives,list)
        or not all(isinstance(o,dict) and isinstance(o.get('id'),str) and isinstance(o.get('text'),str) for o in objectives)):
        raise CardsError('E21','target/objectives: line 1 field schema invalid','regenerate target and source objectives')
    rows=read_rows(b.path('drafts.jsonl'))
    findings=validate(rows,target,slides,{o['id'] for o in objectives},b.path('drafts.jsonl'))
    ids={r['id'] for _,r in rows if isinstance(r,dict) and isinstance(r.get('id'),str) and r.get('status')!='dropped'}
    skip_path=b.path('skipped.jsonl')
    sf,skips=validate_skips(read_rows(skip_path) if skip_path.exists() else [],slides,ids,skip_path)
    findings+=sf
    notes=[r for _,r in rows]
    enum_groups={n.get('group') for n in notes if isinstance(n,dict) and isinstance(n.get('group'),str)
                 and (n.get('enumeration') is True or any(o['id']==n.get('objective') and 'enumerat' in o['text'].lower() for o in objectives))}
    for n in notes:
        if isinstance(n,dict) and n.get('status')!='dropped': findings+=lint(n,isinstance(n.get('group'),str) and n['group'] in enum_groups)
    # C05: a slide with a well-labelled figure needs an io note or a recorded figure decision.
    active_notes=[n for n in notes if isinstance(n,dict) and n.get('status')!='dropped']
    io_slides={x for n in active_notes if n.get('kind')=='io' for x in (n.get('source_ref') if isinstance(n.get('source_ref'),list) else []) if type(x) is int}
    whole={r['slide'] for r in skips if r.get('reason') in ('not_testable','out_of_scope','anking_covers') and not re.search(r'figure|image|diagram',r['item'],re.I)}
    decided=io_slides|{r['slide'] for r in skips if re.search(r'figure|image|diagram',r['item'],re.I)}
    for sl in slides_data(b)['slides']:
        if any(len(f.get('ocr_labels',[]))>=5 for f in sl.get('figures',[])) and not ({'low_text','objectives'}&set(sl.get('flags',[]))) and sl['n'] not in decided:
            findings.append({'code':'C05','severity':'blocker','slide':sl['n'],'message':f"slide {sl['n']} has a labelled figure: add an io note (cards figures) or a skipped.jsonl record whose item says 'Figure: <why not occluded>'"})
    coverage,stats=summarize(notes,skips,slides,objectives)
    for code,key in [('C01','slides_uncovered'),('C02','objectives_without_t1'),('C03','objective_enumerations_below_t1')]:
        for item in coverage[key]: findings.append({'code':code,'severity':'warn','slide':item if code=='C01' else None,'message':f'{key}: {item}'})
    if stats['tier3_share']<.05: findings.append({'code':'C04','severity':'warn','message':'tier 3 share below 5%'})
    path=b.path('checks/check.json')
    payload={'findings':findings,'coverage':coverage,'stats':stats}
    previous=read_json(path) if path.exists() else {}
    if {k:v for k,v in previous.items() if k!='_meta'}!=payload:
        write_json(path,payload,'cards check')
    if not findings: return Result(lines=[f"notes={stats['notes']} cards={stats['cards']} tiers={stats['tiers']['1']}/{stats['tiers']['2']}/{stats['tiers']['3']}"])
    counts=Counter((f['code'],f['severity']) for f in findings)
    return Result('FINDINGS',[f'{code} {severity}: {count}' for (code,severity),count in sorted(counts.items())],[path],1)
