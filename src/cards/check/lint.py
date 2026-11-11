"""Deterministic house-style rules, ported from the v1 renderer."""
import html
import re
CLOZE=re.compile(r'\{\{c(\d+)::(.*?)(?:::((?:(?!\}\}).)*?))?\}\}',re.S)
STOP_U={'and','or','both','the','a','an','of','in','to','is','are','with','all'}

def plain(s):
    return html.unescape(re.sub(r'<[^>]+>','',CLOZE.sub(lambda m:m[2],s)))

def lint(n,enumeration=False,tag_root='#ColdRecall'):
    f=n.get('fields'); out=[]
    if not isinstance(f,dict) or not all(isinstance(v,str) for v in f.values()): return out
    text=f.get('Text',f.get('Front','')); extra=f.get('Extra',f.get('Back Extra',''))
    def flag(code,msg):
        severity='blocker' if code in ('L03','L04','L05','L06','L10') else 'warn'
        if enumeration and code in ('L04','L09'): severity='warn'
        out.append({'code':code,'severity':severity,'note_id':n.get('id'),'message':msg})
    if plain(text).rstrip().endswith('.'): flag('L01','trailing full stop')
    under=re.findall(r'<u\b[^>]*>(.*?)</u>',text+extra,re.I|re.S)
    if len(under)>3 or any(plain(u).strip().lower() in STOP_U for u in under): flag('L02','excess or filler underline')
    for m in CLOZE.finditer(text):
        if ',' in plain(m[2]): flag('L03',f'comma inside c{m[1]}')
        if m[3] and len(plain(m[3]))>20: flag('L12','hint exceeds 20 characters')
        if re.search(r'\(–|–[A-Z]',plain(m[2])) and not re.search(r'class=[\"\'][^\"\']*\bnw\b',m[2]): flag('L13','unwrapped formula inside blank')
    if len(set(CLOZE.findall(text))) and len({m[1] for m in CLOZE.finditer(text)})>5: flag('L04','more than five cloze numbers')
    if any('&amp;amp;' in s or re.search(r'&lt;/?[a-z]',s,re.I) for s in f.values()): flag('L05','escaped HTML in field')
    if '\n' in extra or '\r' in extra: flag('L06','raw newline in Extra')
    body=re.sub(r'<div\b[^>]*class=[\"\']src[\"\'][^>]*>.*?</div>','',extra,flags=re.S|re.I)
    lines=[x for x in re.split(r'<br\s*/?>|\n|</(?:div|li|p)>',body,flags=re.I) if plain(x).strip()]
    if len(lines)>3 or len(plain(body))>200: flag('L07','Extra exceeds three lines or 200 characters')
    if len(plain(text))>200: flag('L08','card text exceeds 200 characters')
    if len(re.findall(r'<(?:b|strong)\b',text,re.I))>4: flag('L09','more than four bold runs')
    tags=n.get('tags')
    if isinstance(tags,list) and any(isinstance(t,str) and not t.startswith(tag_root+'::') for t in tags): flag('L10','foreign tag tree')
    outside=re.sub(r'<div\b[^>]*class=[\"\']src[\"\'][^>]*>.*?</div>','',text+extra,flags=re.S|re.I)
    if re.search(r'\bL\d{3}\b|\bslides?\s+\d+',plain(outside),re.I): flag('L11','citation outside src div')
    return out
