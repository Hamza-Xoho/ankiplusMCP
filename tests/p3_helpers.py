"""Fixture conversion only: preserve v1 card fields verbatim."""
import json
import re
import subprocess
import sys

SOURCE = '#ColdRecall::#Source::MED241::L006_ER_Mitochondria_Golgi'
TARGET = {'deck':'Endoplasmic Reticulum, Mitochondria & Golgi Apparatus',
          'note_type':'ColdRecall Cloze','source_tag':SOURCE,
          'tier_tags':{str(i):f'#ColdRecall::!Tier::{i}' for i in (1,2,3)}}

def cli(*args):
    return subprocess.run([sys.executable,'-m','cards',*map(str,args)],capture_output=True,text=True)

def dump(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding='utf-8')

def records(path):
    return [r for line in path.read_text().splitlines() if (r:=json.loads(line)) and '_meta' not in r]

def drafts(b, notes):
    (b/'drafts.jsonl').write_text(''.join(json.dumps(n)+'\n' for n in notes))

def convert_v1(path, target=TARGET):
    out=[]
    for n in records(path):
        refs = n['source_ref']
        if isinstance(refs,str):
            # Ignore L006; all numeric references after the word slide(s).
            refs = [int(x) for x in re.findall(r'\d+',re.split(r'slides?',refs,flags=re.I)[-1])]
        out.append({**n,'kind':'cloze','action':'create','nid':None,'status':'draft',
                    'deck':target['deck'],'notetype':target['note_type'],'source_ref':refs,'objective':n.get('objective') or None,
                    'tags':[target['source_tag'] if '::#Source::' in t else t for t in n['tags']]})
    return out

def note(i=1,tier=1):
    return {'id':f'n{i:03d}','kind':'cloze','notetype':TARGET['note_type'],
      'deck':TARGET['deck'],'fields':{'Text':'<b>Subject</b> is {{c1::answer}}','Extra':'<div class="src">L006, slide 1</div>'},
      'tags':[SOURCE,f'#ColdRecall::!Tier::{tier}'],'tier':tier,'objective':'ILO1',
      'source_ref':[1],'group':'g01','action':'create','nid':None,'status':'draft'}

def setup(b):
    b.mkdir(parents=True,exist_ok=True)
    dump(b/'target.json',TARGET)
    dump(b/'source/slides.json',{'slides':[{'n':1,'title':'Title','text':'Subject','figures':[]}]})
    dump(b/'source/objectives.json',{'objectives':[{'id':'ILO1','text':'Describe subject','slide':1}]})
    (b/'skipped.jsonl').write_text('')
    drafts(b,[note(),note(2,3)])
    return b
