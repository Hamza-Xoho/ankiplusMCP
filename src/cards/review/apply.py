"""Validate both reports before mutating drafts; merge once with an audit trail."""
import json
import re
from collections import defaultdict
from cards.common.paths import Build
from cards.common.files import read_json, read_jsonl, write_json, write_jsonl
from cards.common.hashing import sha256_file
from cards.common.errors import CardsError
from cards.common.output import Result
from cards.check.lint import lint
from . import parse_report


def invalid(path,line,field):
    raise CardsError('E61',f'{path}: line {line} field {field} invalid','repair the reviewer report')


def report_path(build,folder,reviewer):
    """Prefer the Markdown report; accept the legacy JSONL one on resume."""
    for suffix in ('.md','.jsonl'):
        path=build.path(f'{folder}/{reviewer}_report{suffix}')
        if path.is_file(): return path
    return build.path(f'{folder}/{reviewer}_report.md')


def read_report(path,reviewer,ids,fields=None):
    if not path.is_file(): invalid(path,1,'report missing')
    rows=[]; closed=False
    for line,text in enumerate(path.read_text().splitlines(),1):
        try: r=json.loads(text)
        except json.JSONDecodeError: invalid(path,line,'JSON')
        if not isinstance(r,dict): invalid(path,line,'record')
        if '_meta' in r:
            if line==1 and len(r)==1: continue
            invalid(path,line,'_meta')
        if closed: invalid(path,line,'record after summary')
        if r.get('reviewer')!=reviewer: invalid(path,line,'reviewer')
        kind=r.get('type')
        if kind=='note':
            if ids is not None and (not isinstance(r.get('note_id'),str) or r['note_id'] not in ids): invalid(path,line,'note_id')
            if r.get('verdict') not in ('pass','fix','reject'): invalid(path,line,'verdict')
            if type(r.get('blocker')) is not bool: invalid(path,line,'blocker')
            if not isinstance(r.get('evidence'),str): invalid(path,line,'evidence')
            if 'card' not in r or (r['card'] is not None and (not isinstance(r['card'],str) or not re.fullmatch(r'c[1-9][0-9]*',r['card']))): invalid(path,line,'card')
            allowed={f'A{i}' for i in range(1,14)} if reviewer=='maintainer' else {f'V{i}' for i in range(1,10)}
            if not isinstance(r.get('codes'),list) or any(not isinstance(c,str) or c not in allowed for c in r['codes']): invalid(path,line,'codes')
            rewrite=r.get('rewrite')
            if isinstance(rewrite,str) and rewrite.strip().lower()=='unchanged': rewrite=None
            if 'rewrite' not in r or (rewrite is not None and (not isinstance(rewrite,dict) or not all(isinstance(v,str) for v in rewrite.values()))): invalid(path,line,'rewrite')
            if isinstance(rewrite,dict):
                # Tolerate keys that are not note fields (for example Tags) and fields marked unchanged.
                known=set(fields[r['note_id']]) if fields is not None else set(rewrite)
                rewrite={k:v for k,v in rewrite.items() if k.lower() not in ('tags','tag')}
                if fields is not None and not set(rewrite)<=known: invalid(path,line,'rewrite fields')
                rewrite={k:v for k,v in rewrite.items() if v.strip().lower()!='unchanged'} or None
            r['rewrite']=rewrite
            if reviewer=='student':
                a=r.get('attempt')
                if not isinstance(a,dict) or not isinstance(a.get('answer'),str) or a.get('result') not in ('right','alternative','unknowable'): invalid(path,line,'attempt')
                if 'V2' in r['codes'] and a['result']=='alternative': r['codes']=[*r['codes'],'A2']; r['blocker']=True
        elif kind=='set':
            allowed={f'S{i}' for i in range(1,10)} if reviewer=='maintainer' else {f'V{i}' for i in range(1,10)}
            if not isinstance(r.get('code'),str) or r['code'] not in allowed: invalid(path,line,'code')
            if not isinstance(r.get('notes'),list) or any(not isinstance(n,str) or (ids is not None and n not in ids) for n in r['notes']): invalid(path,line,'notes')
            if not all(isinstance(r.get(k),str) for k in ('finding','fix')): invalid(path,line,'finding/fix')
        elif kind=='summary':
            if r.get('verdict') not in ('PASS','PASS_WITH_FIXES','FAIL') or not isinstance(r.get('stats'),dict): invalid(path,line,'summary')
            closed=True
        else: invalid(path,line,'type')
        rows.append(r)
    if not closed: invalid(path,len(rows)+1,'closing summary missing')
    return rows


def load_report(path,reviewer,ids=None,fields=None):
    """Read Markdown reports, and legacy JSONL ones on resume."""
    if not path.is_file(): invalid(path,1,'report missing')
    if path.suffix.lower()=='.md':
        return parse_report.parse(path,reviewer,ids,fields)
    try:
        first=next((line for line in path.read_text().splitlines()
                    if line.strip() and not line.startswith('<!--')),'')
    except (UnicodeError,OSError) as exc:
        raise CardsError('E61',f'{path}: line 1 field report unreadable','write a UTF-8 report') from exc
    if not first.lstrip().startswith('{'):
        return parse_report.parse(path,reviewer,ids,fields)
    return read_report(path,reviewer,ids,fields)


def result(log,path):
    issue=bool(log['conflicts'] or log['open_blockers'] or log['css_fix_needed'] or log['set_findings'])
    decision='agents' if len(log['changed_ids'])>8 else 'self-review'
    return Result('FINDINGS' if issue else 'OK',[
        f"applied {len(log['applied'])}; declined {len(log['declined'])}; conflicts {len(log['conflicts'])}; dropped {len(log['dropped'])}",
        'changed: '+(','.join(log['changed_ids']) or 'none'),f'round 2: {decision}',
        *[f"conflict: {c['id']}" for c in log['conflicts']],
        *[f"rewrite rejected by lint: {x['id']} {','.join(x['codes'])}" for x in log.get('lint_rejected',[])],
        *(['css_fix_needed'] if log['css_fix_needed'] else [])], [path],1 if issue else 0)


def run(args):
    b=Build(args.build); directory=f'review/round{args.round}'
    draft=b.path('drafts.jsonl'); backup=b.path(f'drafts.r{args.round}.jsonl'); logpath=b.path(directory+'/apply_log.json')
    notes=list(read_jsonl(draft)); base=list(read_jsonl(backup)) if backup.exists() else notes
    byid={n['id']:n for n in base}
    rows=[]; hashes={}
    for reviewer in ('maintainer','student'):
        path=report_path(b,directory,reviewer)
        rows.extend(load_report(path,reviewer,set(byid),{n:v['fields'] for n,v in byid.items()}))
        hashes[reviewer]=sha256_file(path)
    section_root=b.path(directory+'/maintainer-sections')
    if section_root.exists():
        for section in sorted(section_root.iterdir()):
            path=report_path(b,directory,f'maintainer_section{section.name}')
            rows.extend(load_report(path,'maintainer',set(byid),{n:v['fields'] for n,v in byid.items()}))
            hashes['section'+section.name]=sha256_file(path)
    declines=[]
    for entry in args.decline:
        ident,sep,reason=entry.partition(':')
        if not sep or not reason.strip() or ident not in byid:
            raise CardsError('E61','decline: line 1 field ID:REASON invalid','supply an active note id and reason')
        declines.append({'id':ident,'reason':reason})
    if logpath.exists():
        old=read_json(logpath)
        if old.get('report_hashes')==hashes and old.get('declined')==declines and old.get('drafts_sha256')==sha256_file(draft):
            return result(old,logpath)
        raise CardsError('E61',f'{logpath}: line 1 field already applied round changed','resolve against preserved drafts in a new review round')
    log={'applied':[],'declined':declines,'conflicts':[],'changed_ids':[],'dropped':[], 'unresolved':[], 'css_fix_needed':[], 'open_blockers':[], 'set_findings':[r for r in rows if r['type']=='set'], 'report_hashes':hashes}
    css=defaultdict(set)
    for r in rows:
        if r['type']=='note' and set(r['codes']) & {'V3','V4','V5','V6','V7','V9'} and r['verdict']=='fix':
            css[(tuple(r['codes']),r['evidence'].strip().casefold())].add(r['note_id'])
    css_ids=set()
    for (codes,evidence),ids in css.items():
        if len(ids)>=3:
            css_ids.update(ids); log['css_fix_needed'].append({'codes':list(codes),'evidence':evidence,'notes':sorted(ids)})
    grouped=defaultdict(list)
    for r in rows:
        if r['type']=='note': grouped[r['note_id']].append(r)
    dropped=set(); declined={d['id'] for d in declines}
    for n in notes:
        ident=n['id']; findings=grouped[ident]; before=json.dumps(n,sort_keys=True)
        rewrites=[]
        for r in findings:
            if r['verdict']=='fix' and r['rewrite'] is not None:
                fields={**n['fields'],**{k:v for k,v in r['rewrite'].items() if v!='unchanged'}}
                if fields not in rewrites: rewrites.append(fields)
        conflict=len(rewrites)>1 or (rewrites and any(r['verdict']=='reject' for r in findings))
        if len(rewrites)==1 and not conflict:
            # A rewrite must not introduce a lint blocker the draft did not have; keep the draft and re-review it.
            had={f['code'] for f in lint(n) if f['severity']=='blocker'}
            new_blockers=sorted({f['code'] for f in lint({**n,'fields':rewrites[0]}) if f['severity']=='blocker'}-had)
            if new_blockers:
                log.setdefault('lint_rejected',[]).append({'id':ident,'codes':new_blockers})
                conflict=True; rewrites=[]
        if conflict:
            log['conflicts'].append({'id':ident,'findings':findings})
        elif ident in declined or any(r['verdict']=='reject' for r in findings):
            dropped.add(ident); log['dropped'].append(ident)
        elif rewrites and ident not in css_ids:
            n['fields']=rewrites[0]; n['status']='fixed'; log['applied'].append(ident)
        blockers=[r for r in findings if r['blocker'] and r['verdict']!='pass' and (conflict or ident in css_ids or r['rewrite'] is None)]
        if ident in dropped: blockers=[]
        log['open_blockers'].extend(blockers)
        if blockers and args.round==2:
            n['status']='unresolved'
            tag='#ColdRecall::Review_unresolved'
            if tag not in n['tags']: n['tags'].append(tag)
            log['unresolved'].append(ident)
        if ident in dropped or before!=json.dumps(n,sort_keys=True) or any(x['id']==ident for x in log.get('lint_rejected',[])): log['changed_ids'].append(ident)
    skipped=list(read_jsonl(b.path('skipped.jsonl'))) if b.path('skipped.jsonl').exists() else []
    for n in notes:
        if n['id'] in dropped:
            skipped.append({'note_id':n['id'],'slide':n['source_ref'][0] if n['source_ref'] else None,'item':n['fields'].get('Text',n['id']),'reason':'rejected_in_review','note':next((d['reason'] for d in declines if d['id']==n['id']),'reviewer rejection')})
    if not backup.exists(): backup.write_bytes(draft.read_bytes())
    write_jsonl(draft,[n for n in notes if n['id'] not in dropped],'cards apply')
    write_jsonl(b.path('skipped.jsonl'),skipped,'cards apply')
    log['drafts_sha256']=sha256_file(draft)
    write_json(logpath,log,'cards apply')
    state=read_json(b.state); state.setdefault('review',{}).update(round=args.round,round2_allowed=bool(log['changed_ids']) and args.round<2)
    write_json(b.state,state,'cards apply')
    return result(log,logpath)
