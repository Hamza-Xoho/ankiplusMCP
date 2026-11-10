"""Coverage and note/card mix; dropped notes supply no coverage."""
from collections import Counter
from .lint import CLOZE

def summarize(notes,skips,slides,objectives):
    active=[n for n in notes if isinstance(n,dict) and n.get('status')!='dropped']
    covered={s for n in active for s in (n.get('source_ref') if isinstance(n.get('source_ref'),list) else []) if type(s) is int}
    covered.update(r['slide'] for r in skips)
    missing=[o['id'] for o in objectives if not any(n.get('objective')==o['id'] and n.get('tier')==1 for n in active)]
    enum=[o['id'] for o in objectives if 'enumerat' in o.get('text','').lower() and o['id'] in missing and any(n.get('objective')==o['id'] for n in active)]
    tiers=Counter(str(n.get('tier')) for n in active if type(n.get('tier')) is int and n['tier'] in (1,2,3))
    cards=0
    for n in active:
        f=n.get('fields')
        if not isinstance(f,dict): continue
        nums={m[1] for v in f.values() if isinstance(v,str) for m in CLOZE.finditer(v)}
        cards+=len(nums) or (1 if n.get('kind')=='basic' else 0)
    stats={'notes':len(active),'cards':cards,'tiers':{str(i):tiers[str(i)] for i in (1,2,3)},
           'tier3_share':tiers['3']/len(active) if active else 0,
           'groups':len({n['group'] for n in active if isinstance(n.get('group'),str)}),
           'per_group':dict(sorted(Counter(n['group'] for n in active if isinstance(n.get('group'),str)).items()))}
    return {'slides_uncovered':sorted(set(slides)-covered),'objectives_without_t1':missing,'objective_enumerations_below_t1':enum},stats
