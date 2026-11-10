"""Pure waste judgments. Allowances must come from explicit build evidence."""
import json
import re

def evidence(event, reason):
    return {'idx':event['idx'],'tool':event.get('tool','session'),
            'excerpt':json.dumps(event.get('input',{}),ensure_ascii=False)[:120], 'reason':reason}

def verdict(items):
    return not items, items

def w1(s):
    return verdict([evidence(c,'automatic compaction') for c in s['compactions'] if c['trigger']=='auto'])

def w2(s):
    return verdict([evidence(e,'unflagged lecture image read') for e in s['events']
                    if e['tool']=='Read' and e['images'] and not e.get('allowed_image',False)
                    and '/renders/sheets/' not in '/'+e['input'].get('file_path','')])

def w3(s):
    items=[evidence({'idx':1,'tool':'Agent','input':{'id':a['id'],'type':a['type']}},'fork or unpinned reviewer')
           for a in s['subagents'] if a['is_fork'] or a['type'] not in {'anki-maintainer','anki-student'}]
    # A launch is evidence even when the process never produced a transcript.
    for e in s['events']:
        if e['tool']=='Agent' and e['input'].get('subagent_type') not in {'anki-maintainer','anki-student'}:
            items.append(evidence(e,'fork or unpinned reviewer launch'))
    return verdict(items)

def key(e):
    return e['tool'], json.dumps(e['input'],sort_keys=True,ensure_ascii=False)

def all_events(s):
    return [s['events'], *[a['events'] for a in s['subagents']]]

def w4(s):
    seen, items = set(), []
    for events in all_events(s):
        for e in events:
            k=key(e)
            if len(k[1]) > 2000 and k in seen: items.append(evidence(e,'large payload sent again'))
            seen.add(k)
    return verdict(items)

def w5(s):
    items=[]
    for events in all_events(s):
        failed=set()
        for e in events:
            k=key(e)
            local = e['tool']=='Bash' and re.search(r'(?:localhost|127\.\d+\.\d+\.\d+|\[?::1\]?)[:\s]+\d+|(?:localhost|127\.\d+\.\d+\.\d+).*?(?:--port|-p)\s*\d+',e['input'].get('command',''))
            if k in failed or local: items.append(evidence(e,'retry after error or local-port workaround'))
            if e['failed']: failed.add(k)
    return verdict(items)

def w6(s):
    written, items = set(), []
    for e in s['events']:
        path=e['input'].get('file_path','')
        if path.split('/')[-1]=='drafts.jsonl' and e['tool'] in {'Write','Edit'}:
            if path in written or e['tool']=='Edit': items.append(evidence(e,'drafts edited after first write'))
            written.add(path)
    return verdict(items)

def w7(s):
    return verdict([evidence(e,'unflagged contact sheet in main context') for e in s['events']
                    if e['tool']=='Read' and '/renders/sheets/' in '/'+e['input'].get('file_path','')
                    and not e.get('allowed_sheet',False)])

def w8(s):
    return verdict([evidence({'idx':1,'tool':'Agent','input':{'id':a['id'],'first_ctx':a['first_ctx']}},
                             'reviewer context exceeds baseline by more than 25k')
                    for a in s['subagents'] if a['first_ctx'] > s['first_ctx']+25000])

CHECKS = {f'W-{n}':fn for n,fn in enumerate((w1,w2,w3,w4,w5,w6,w7,w8),1)}

def check(s):
    return {code:{'pass':ok,'evidence':ev} for code,fn in CHECKS.items() for ok,ev in [fn(s)]}
