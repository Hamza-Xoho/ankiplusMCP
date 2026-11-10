"""Phase 4 acceptance through the real CLI; reports are handwritten fixtures."""
import json
from pathlib import Path
import pytest
from PIL import Image
from cards.common.size import tokens
from tests.p3_helpers import cli, dump, drafts, records, note, setup

T = Path('.claude/skills/anki2/templates/review')

@pytest.fixture
def build(tmp_path):
    b = setup(tmp_path/'build ü')
    dump(b/'build.json', {'review':{'round':0}})
    dump(b/'checks/check.json', {'findings':[]})
    (b/'source/map.md').write_text('1 Subject')
    sheets=[]
    for i, ids in enumerate([['n001','n002']]):
        pair={'notes':ids}
        for side in ('fronts','backs'):
            p=b/f'renders/sheets/{i}_{side}.png'; p.parent.mkdir(parents=True,exist_ok=True)
            Image.new('RGB',(20,20),'white').save(p); pair[side]=str(p)
        sheets.append(pair)
    dump(b/'renders/sheets.json', {'sheets':sheets})
    return b

def packet(b,*extra): return cli('packets','--build',b,'--round','1',*extra)
def apply(b,k=1,*extra): return cli('apply','--build',b,'--round',k,*extra)
def folder(b,r='maintainer'): return b/f'review/round1/{r}'
def report(b, reviewer, rows, k=1):
    p=b/f'review/round{k}/{reviewer}_report.jsonl'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join(json.dumps({**r,'reviewer':reviewer})+'\n' for r in [*rows,{'type':'summary','verdict':'PASS_WITH_FIXES' if rows else 'PASS','stats':{}}]))
def finding(n='n001',**kw):
    return {'type':'note','note_id':n,'card':None,'verdict':'fix','codes':['A3'],'blocker':True,'evidence':'article leak','rewrite':{'Text':'Correct {{c1::answer}}','Extra':'unchanged'},**kw}
def reports(b,rows=(),student=(),k=1): report(b,'maintainer',rows,k); report(b,'student',student,k)
def log(b,k=1): return json.loads((b/f'review/round{k}/apply_log.json').read_text())

def test_fr13_refuses_with_blockers(build):
    dump(build/'checks/check.json',{'findings':[{'severity':'blocker'}]})
    p=packet(build); assert p.returncode==3 and 'blocker' in p.stdout and not (build/'review').exists()
def test_fr13_maintainer_slices_cover_citations(build):
    dump(build/'source/slides.json',{'slides':[{'n':i,'title':str(i),'text':f'evidence {i}','figures':[]} for i in range(1,6)]})
    ns=[note(),note(2)]; ns[0]['source_ref']=[3]; ns[1]['source_ref']=[5]; drafts(build,ns)
    assert packet(build).returncode==0
    s=(folder(build)/'source_slices.md').read_text()
    assert all(f'## Slide {i}' in s and f'evidence {i}' in s for i in range(2,6)) and '## Slide 1' not in s

def test_fr13_packet_allowlist_only(build):
    (build/'author-reasoning.txt').write_text('SECRET')
    assert packet(build).returncode==0
    assert {p.name for p in folder(build).iterdir()} <= {'PROMPT.md','brief.md','rubric.md','report-format.md','house-style.md','drafts.jsonl','source_slices.md','map.md','objectives.json','check.json','reconcile.md','pages'}
    for r in ('maintainer','student'):
        for p in folder(build,r).rglob('*'):
            if p.is_file() and p.parent!=folder(build,r): assert p.suffix=='.png' and p.parent.name in ('pages','sheets','previews')
    assert {p.name for p in folder(build,'student').iterdir()} <= {'PROMPT.md','brief.md','rubric.md','report-format.md','sheets.json','sheets','previews'}
def test_fr13_student_has_no_text_sources(build):
    assert packet(build).returncode==0
    for p in folder(build,'student').rglob('*'):
        if p.is_file(): assert p.suffix not in {'.html','.jsonl'} and 'Subject' not in (p.read_text() if p.suffix!='.png' else '')
def test_fr13_prompt_small(build):
    assert packet(build).returncode==0
    assert all(tokens((folder(build,r)/'PROMPT.md').read_text())<=300 for r in ('student','maintainer'))
def test_fr13_prompt_single_turn_images(build):
    assert packet(build).returncode==0
    for r in ('student','maintainer'): assert 'one turn' in (folder(build,r)/'PROMPT.md').read_text()
def test_fr13_prompt_names_pinned_agent(build):
    p=packet(build); assert p.returncode==0 and 'anki-maintainer' in p.stdout and 'anki-student' in p.stdout and 'fork' not in p.stdout

def test_fr13_round2_scope(build):
    ns=[note(i) for i in range(1,5)]; ns[2]['group']=ns[3]['group']='other'; drafts(build,ns)
    p=cli('packets','--build',build,'--round','2','--only','n001'); assert p.returncode==0, p.stdout
    assert [n['id'] for n in records(build/'review/round2/maintainer/drafts.jsonl')]==['n001','n002']
    manifest=json.loads((build/'review/round2/student/sheets.json').read_text()); assert all(set(s['notes'])<= {'n001','n002'} for s in manifest['sheets'])

def test_c8_student_subset_rule(build):
    ns=[note(i,tier=1 if i==2 else 2) for i in range(1,9)]
    for n in ns: n['group']='a' if n['id']<'n006' else 'b'
    drafts(build,ns); sheets=[]
    for i,n in enumerate(ns):
        s={'notes':[n['id']]}
        for side in ('fronts','backs'):
            p=build/f'renders/sheets/{i}_{side}.png'; Image.new('RGB',(20,20)).save(p); s[side]=str(p)
        sheets.append(s)
    dump(build/'renders/sheets.json',{'sheets':sheets})
    assert packet(build).returncode==0
    selected=json.loads((folder(build,'student')/'sheets.json').read_text())['sheets']
    ids={n for s in selected for n in s['notes']}
    assert 'n002' in ids and any(n in ids for n in ('n006','n007','n008')) and len(selected)<8
    omitted=[str(i) for i in range(1,9) if ns[i-1]['id'] not in ids]
    assert 'Sheet pairs omitted: '+', '.join(omitted)+'.' in (folder(build,'student')/'PROMPT.md').read_text()
def test_fr16_reconcile_searches(build):
    assert packet(build).returncode==0
    text=(folder(build)/'reconcile.md').read_text(); assert 'tag:#ColdRecall::#Source::MED241::L006' in text and 'AnKing' in text and 'tag:src::med241-l006' in text and 'deck:*AnKing* "Title"' in text

def test_fr15_applies_rewrites_and_rejections(build):
    reports(build,[finding(),finding('n002',verdict='reject',rewrite=None)])
    assert apply(build).returncode==0
    ns=records(build/'drafts.jsonl'); assert len(ns)==1 and ns[0]['fields']['Text']=='Correct {{c1::answer}}' and ns[0]['status']=='fixed' and ns[0]['fields']['Extra']==note()['fields']['Extra']
    assert log(build)['applied']==['n001']
    assert records(build/'skipped.jsonl')[0]['reason']=='rejected_in_review' and log(build)['dropped']==['n002']
def test_fr15_conflict_untouched(build):
    old=(build/'drafts.jsonl').read_bytes(); reports(build,[finding()], [finding(codes=['V1'],attempt={'answer':'x','result':'unknowable'},rewrite={'Text':'Different'})])
    p=apply(build); assert p.returncode==1 and 'n001' in p.stdout
    assert records(build/'drafts.jsonl')[0]['fields']==records(build/'drafts.r1.jsonl')[0]['fields'] and log(build)['conflicts']
def test_fr15_v2_escalates_to_a2(build):
    reports(build,student=[finding(codes=['V2'],blocker=False,rewrite=None,attempt={'answer':'other','result':'alternative'})])
    assert apply(build).returncode==1
    assert any('A2' in f['codes'] and f['blocker'] for f in log(build)['open_blockers'])
def test_fr15_css_findings_flagged(build):
    drafts(build,[note(i) for i in range(1,4)])
    before=records(build/'drafts.jsonl')
    reports(build,student=[finding(f'n{i:03d}',codes=['V6'],evidence='same overflow',attempt={'answer':'x','result':'right'}) for i in range(1,4)])
    assert apply(build).returncode==1
    assert log(build)['css_fix_needed'] and records(build/'drafts.jsonl')==before
def test_fr15_malformed_report_exit2(build):
    reports(build); (build/'review/round1/student_report.jsonl').write_text('{bad\n')
    before=(build/'drafts.jsonl').read_bytes(); p=apply(build)
    assert p.returncode==2 and 'student' in p.stdout and 'line 1' in p.stdout and (build/'drafts.jsonl').read_bytes()==before
@pytest.mark.parametrize('count,word',[(8,'self-review'),(9,'agents')])
def test_fr15_round2_threshold(build,count,word):
    drafts(build,[note(i) for i in range(1,count+1)]); reports(build,[finding(f'n{i:03d}') for i in range(1,count+1)])
    p=apply(build); assert p.returncode==0 and word in p.stdout

def test_fr15_unresolved_after_round2(build):
    reports(build,[finding(rewrite=None)],k=2); assert apply(build,2).returncode==1
    n=records(build/'drafts.jsonl')[0]; assert n['status']=='unresolved' and any('Review_unresolved' in t for t in n['tags'])
def test_fr15_previous_drafts_kept(build):
    before=(build/'drafts.jsonl').read_bytes(); reports(build,[finding()]); assert apply(build).returncode==0
    assert (build/'drafts.r1.jsonl').read_bytes()==before
    assert apply(build).returncode==0 and (build/'drafts.r1.jsonl').read_bytes()==before

def test_fr28_agent_frontmatter():
    for r,effort,turns,tools in [('maintainer','high','14','Read, Grep, Glob, Write, mcp__anki__find_notes, mcp__anki__notes_info'),('student','medium','6','Read, Write')]:
        raw=Path(f'.claude/agents/anki-{r}.md').read_text().split('---')[1]
        d=dict(line.split(': ',1) for line in raw.strip().splitlines())
        assert {k:d[k] for k in ('model','effort','tools','permissionMode','omitClaudeMd','maxTurns')}==dict(model='claude-sonnet-5-5',effort=effort,tools=tools,permissionMode='dontAsk',omitClaudeMd='true',maxTurns=turns)
def test_c3_templates_complete():
    for r in ('maintainer','student'):
        for name in ('brief','rubric','report-format'): assert (T/r/f'{name}.md').is_file()
    assert (T/'house-style.md').is_file()
    for prefix,count,r in [('A',13,'maintainer'),('S',9,'maintainer'),('V',9,'student')]:
        text=(T/r/'rubric.md').read_text(); assert all(f'**{prefix}{i} ' in text for i in range(1,count+1))

@pytest.mark.parametrize('command',['packets','apply'])
def test_g3_status_line_first(build,command):
    reports(build); p=cli(command,'--build',build,'--round','1'); assert p.stdout.splitlines()[0] in ('OK','FINDINGS','ERROR')
@pytest.mark.parametrize('command',['packets','apply'])
def test_g3_stdout_budget(build,command):
    reports(build); p=cli(command,'--build',build,'--round','1'); assert len(p.stdout)<=2000 and len(p.stdout.splitlines())<=40
@pytest.mark.parametrize('command',['packets','apply'])
def test_g4_exit_codes_mapped(build,command):
    reports(build); assert cli(command,'--build',build,'--round','1').returncode==0
    assert cli(command,'--build',build,'--round','0').returncode==2
    assert cli(command,'--bad').returncode==2
@pytest.mark.parametrize('command',['packets','apply'])
def test_g5_rerun_identical(build,command):
    reports(build,[finding()]); assert cli(command,'--build',build,'--round','1').returncode==0
    def snapshot():
        import re
        import hashlib
        return {str(p.relative_to(build)):hashlib.sha256(p.read_bytes()).hexdigest() for p in build.rglob('*.png')} | {str(p.relative_to(build)):re.sub(r'\d{4}-\d\d-\d\dT[^ "<]+','TIME',p.read_text()) for p in build.rglob('*') if p.is_file() and p.suffix in ('.json','.md','.jsonl') and p.name!='log.jsonl'}
    before=snapshot(); assert cli(command,'--build',build,'--round','1').returncode==0; assert snapshot()==before
@pytest.mark.parametrize('command',['packets','apply'])
def test_g6_no_writes_outside_build(build,command):
    reports(build); outside=build.parent/'readonly'; outside.mkdir(); p=outside/'source.md'; p.write_text('SOURCE'); outside.chmod(0o555)
    assert cli(command,'--build',build,'--round','1').returncode==0
    assert p.read_text()=='SOURCE' and list(outside.iterdir())==[p]
@pytest.mark.parametrize('command',['packets','apply'])
def test_g7_provenance_present(build,command):
    reports(build); assert cli(command,'--build',build,'--round','1').returncode==0
    p=folder(build)/'PROMPT.md' if command=='packets' else build/'review/round1/apply_log.json'
    text=p.read_text(); assert 'cards '+command in text
    import re
    assert re.search(r'20\d\d-\d\d-\d\dT',text) and '0.1.0' in text
    if command=='apply': assert set(json.loads(text)['_meta']) >= {'tool','version','created'}
@pytest.mark.parametrize('command',['packets','apply'])
def test_g10_help_short(command):
    p=cli(command,'--help'); assert p.returncode==0 and len(p.stdout.splitlines())<=20
