"""D-6/D-7 validation. Schema failures are located blocker findings."""
from collections import Counter
import json
import re
from ..common.errors import CardsError

REQUIRED={'id','kind','notetype','deck','fields','tags','tier','objective','source_ref','group','action','status'}

def read_rows(path):
    rows=[]
    with path.open(encoding='utf-8') as stream:
        for line,text in enumerate(stream,1):
            try: row=json.loads(text)
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise CardsError('E21',f'{path}: line {line} field JSON invalid','repair the JSONL record') from exc
            if isinstance(row,dict) and '_meta' in row: continue
            rows.append((line,row))
    return rows

def validate(rows,target,slides,objectives,path):
    findings=[]
    ids=Counter(r.get('id') for _,r in rows if isinstance(r,dict) and isinstance(r.get('id'),str))
    for line,n in rows:
        def flag(code,field,message):
            findings.append({'code':code,'severity':'blocker','note_id':n.get('id') if isinstance(n,dict) and isinstance(n.get('id'),str) else None,
                'file':str(path),'line':line,'field':field,'message':message})
        if not isinstance(n,dict):
            flag('S01','record','expected a note object'); continue
        missing=REQUIRED-n.keys()
        if missing: flag('S01',','.join(sorted(missing)),'required fields missing')
        ident=n.get('id')
        if not isinstance(ident,str) or not re.fullmatch(r'n\d{3,}',ident) or ids[ident]>1:
            flag('S02','id','expected a unique stable nNNN id')
        if (n.get('kind') not in ('cloze','io','basic') or n.get('status') not in ('draft','fixed','dropped','unresolved')
            or n.get('action') not in ('create','update') or (n.get('action')=='update' and (type(n.get('nid')) is not int or n['nid']<=0))):
            flag('S03','kind/status/action/nid','invalid enum or update nid')
        fields=n.get('fields')
        if not isinstance(fields,dict) or not fields or not all(isinstance(k,str) and isinstance(v,str) for k,v in fields.items()):
            flag('S04','fields','expected note-type string fields')
        elif n.get('kind')=='cloze' and (not isinstance(fields.get('Text'),str) or not re.search(r'\{\{c[1-9]\d*::.+?\}\}',fields['Text'],re.S)):
            flag('S04','fields.Text','cloze note requires a cloze in Text')
        elif n.get('kind')=='io' and not all(fields.get(k) for k in ('Image','Occlusion')):
            flag('S04','fields','IO requires Image and Occlusion')
        if type(n.get('tier')) is not int or n['tier'] not in (1,2,3): flag('S05','tier','expected integer 1–3')
        tags=n.get('tags')
        if (not isinstance(tags,list) or not all(isinstance(t,str) for t in tags)
            or target.get('source_tag') not in tags or target.get('tier_tags',{}).get(str(n.get('tier'))) not in tags):
            flag('S06','tags','required source and matching tier tags missing')
        refs=n.get('source_ref')
        if not isinstance(refs,list) or not refs or any(type(s) is not int or s not in slides for s in refs):
            flag('S07','source_ref','expected existing slide numbers')
        expected=target.get('io_note_type','Image Occlusion') if n.get('kind')=='io' else target.get('note_type')
        if n.get('deck')!=target.get('deck') or n.get('notetype')!=expected:
            flag('S08','deck/notetype','does not match target')
        if (not isinstance(n.get('group'),str) or not n['group'] or
            (n.get('objective') is not None and (not isinstance(n['objective'],str) or n['objective'] not in objectives))):
            flag('S09','objective/group','unknown objective or invalid group')
        if n.get('kind')=='io':
            if (not isinstance(n.get('media'),list) or not n['media'] or not isinstance(n.get('preview'),str)
                or any(not isinstance(m,dict) or not all(isinstance(m.get(k),str) and m[k] for k in ('path','filename')) for m in n.get('media',[]))):
                flag('S04','media/preview','IO requires media paths and a preview')
    return findings

def validate_skips(rows,slides,ids,path):
    findings=[]; valid=[]
    for line,r in rows:
        good=(isinstance(r,dict) and type(r.get('slide')) is int and r['slide'] in slides
              and isinstance(r.get('item'),str) and bool(r['item'])
              and r.get('reason') in ('not_testable','anking_covers','covered_by','out_of_scope','other','rejected_in_review'))
        if good and r['reason']=='anking_covers': good=type(r.get('nid')) is int and r['nid']>0
        if good and r['reason']=='covered_by': good=r.get('note_id') in ids
        if good: valid.append(r)
        else: findings.append({'code':'S09','severity':'blocker','file':str(path),'line':line,'field':'skip','message':'invalid D-7 skip record','note_id':None})
    return findings,valid
