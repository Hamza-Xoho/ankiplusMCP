"""Adversarial reports and packet independence beyond the named contracts."""
import json
from pathlib import Path
from PIL import Image
import pytest
from tests.contract.test_p4_review import build, packet, reports, apply, finding, folder, report, log
from tests.p3_helpers import records, drafts, note, dump
from cards.common.size import tokens

@pytest.mark.parametrize('case',['fix','reject','conflict','css-pattern','malformed'])
def test_report_fixtures(build,case):
    root=Path('tests/fixtures/reports')/case
    drafts(build,[note(i) for i in range(1,4)])
    dest=build/'review/round1'; dest.mkdir(parents=True)
    for r in ('maintainer','student'):
        (dest/f'{r}_report.jsonl').write_bytes((root/f'{r}.jsonl').read_bytes())
    p=apply(build)
    assert p.returncode=={'fix':0,'reject':0,'conflict':1,'css-pattern':1,'malformed':2}[case]

@pytest.mark.parametrize('field,value',[('blocker','yes'),('rewrite',{'Bad':'x'}),('codes',['A99']),('card',1),('verdict','okay'),('note_id','missing')])
def test_invalid_report_never_mutates(build,field,value):
    reports(build,[finding(**{field:value})]); before=(build/'drafts.jsonl').read_bytes()
    p=apply(build); assert p.returncode==2 and 'maintainer' in p.stdout and 'line 1' in p.stdout
    assert (build/'drafts.jsonl').read_bytes()==before and not (build/'drafts.r1.jsonl').exists()

def test_prompt_manifest_never_lists_page_images(build):
    """A long lecture must not overflow PROMPT.md by enumerating page paths."""
    slides=[{'n':i,'title':f'Slide {i}','text':f'evidence {i}','figures':[],
             'flags':['image_only']} for i in range(1,21)]
    dump(build/'source/slides.json',{'slides':slides})
    ns=[note(i) for i in range(1,21)]
    for i,n in enumerate(ns,1): n['source_ref']=[i]
    drafts(build,ns)
    for i in range(1,21):
        p=build/f'source/pages/p{i:02d}.png'; p.parent.mkdir(parents=True,exist_ok=True)
        Image.new('RGB',(10,10),'white').save(p)
    pair={'notes':[n['id'] for n in ns]}
    for side in ('fronts','backs'):
        p=build/f'renders/sheets/all_{side}.png'; p.parent.mkdir(parents=True,exist_ok=True)
        Image.new('RGB',(20,20),'white').save(p); pair[side]=str(p)
    dump(build/'renders/sheets.json',{'sheets':[pair]})
    p=packet(build); assert p.returncode==0,p.stdout
    text=(build/'review/round1/maintainer/pages/images.md').read_text()
    assert [line[2:] for line in text.splitlines() if line.startswith('- ')] == [f'p{i:02d}.png' for i in range(1,21)]
    prompt=(build/'review/round1/maintainer/PROMPT.md').read_text()
    assert 'pages/images.md' in prompt and 'p01.png' not in prompt and tokens(prompt)<=300

def test_partial_review_round_resumes_without_mutation(build):
    """A rate-limited reviewer leaves reports and drafts intact for the rerun."""
    assert packet(build).returncode==0
    before=(build/'drafts.jsonl').read_bytes()
    report(build,'maintainer',[finding('n001')])
    assert packet(build).returncode==0
    assert (build/'review/round1/maintainer_report.jsonl').is_file()
    p=apply(build); assert p.returncode==2 and 'missing' in p.stdout.lower()
    assert (build/'drafts.jsonl').read_bytes()==before
    assert not (build/'review/round1/apply_log.json').exists()
    report(build,'student',[])
    p=apply(build); assert p.returncode in (0,1)
    assert (build/'review/round1/apply_log.json').is_file()

def test_reconcile_searches_anking_lecture_tags(build):
    p=packet(build); assert p.returncode==0,p.stdout
    text=(build/'review/round1/maintainer/reconcile.md').read_text()
    assert 'tag:*L006*' in text and 'deck:*AnKing* tag:*L006*' in text
    assert 'W4::4-Wed::L029' in text

def test_mixed_sheet_excludes_unrelated_pixels(build):
    ns=[note(i) for i in range(1,4)]; ns[2]['group']='other'; drafts(build,ns)
    pair={'notes':[n['id'] for n in ns]}
    for side in ('fronts','backs'):
        p=build/f'renders/sheets/mixed_{side}.png'; Image.new('RGB',(20,60),'red').save(p); pair[side]=str(p)
    dump(build/'renders/sheets.json',{'sheets':[pair]})
    for i in (1,2):
        for label in ('c1_front','back'):
            p=build/f'renders/cards/n{i:03d}_{label}.png'; p.parent.mkdir(exist_ok=True); Image.new('RGB',(20,20),'blue').save(p)
    from tests.p3_helpers import cli
    p=cli('packets','--build',build,'--round','2','--only','n001'); assert p.returncode==0,p.stdout
    st=build/'review/round2/student'; manifest=json.loads((st/'sheets.json').read_text())
    assert manifest['sheets'][0]['notes']==['n001','n002']
    for side in ('fronts','backs'):
        with Image.open(st/manifest['sheets'][0][side]) as im: assert (255,0,0) not in list(im.convert('RGB').get_flattened_data())

def test_decline_drops_with_reason(build):
    reports(build,[finding()]); assert apply(build,1,'--decline','n001:outside objectives').returncode==0
    assert records(build/'skipped.jsonl')[0]['note']=='outside objectives'

def test_verbatim_template_sections():
    raw=Path('.claude/skills/anki/SKILL.md').read_text()
    t=Path('.claude/skills/anki2/templates/review')
    for p in (t/'house-style.md',t/'maintainer/brief.md',t/'student/brief.md',t/'student/rubric.md'):
        assert p.read_text().strip() in raw
    text=(t/'maintainer/rubric.md').read_text()
    a,b=text.split('### Rubric — the maintainer, the set')
    assert a.strip() in raw and ('### Rubric — the maintainer, the set'+b).strip() in raw

@pytest.mark.parametrize('field,value',[('note_id',[]),('codes',[{}])])
def test_report_unhashable_values_located(build,field,value):
    reports(build,[finding(**{field:value})]); p=apply(build)
    assert p.returncode==2 and 'maintainer_report' in p.stdout and 'line 1' in p.stdout

def test_packet_directory_symlink_preserves_source(build):
    dest=build/'review/round1'; dest.mkdir(parents=True); (dest/'maintainer').symlink_to(build/'source',target_is_directory=True)
    before=(build/'source/slides.json').read_bytes(); p=packet(build)
    assert p.returncode==2 and (build/'source/slides.json').read_bytes()==before

@pytest.mark.parametrize('name',['drafts.jsonl','fake.png'])
def test_student_preview_is_image_only(build,name):
    if name=='fake.png': (build/name).write_text('SECRET')
    ns=records(build/'drafts.jsonl'); ns[0]['preview']=name; drafts(build,ns)
    p=packet(build); assert p.returncode==2 and 'image' in p.stdout
    assert not (folder(build,'student')/'previews'/name).exists()

def test_large_batch_has_section_packets(build):
    ns=[note(i) for i in range(1,82)]; ns[-1]['source_ref']=[5]; drafts(build,ns)
    dump(build/'source/slides.json',{'slides':[{'n':i,'title':str(i),'text':str(i),'figures':[]} for i in range(1,6)]})
    s=json.loads((build/'renders/sheets.json').read_text())['sheets'][0]; s['notes']=[n['id'] for n in ns]
    dump(build/'renders/sheets.json',{'sheets':[s]})
    p=packet(build); assert p.returncode==0,p.stdout
    section_dirs=sorted((build/'review/round1/maintainer-sections').iterdir())
    assert len(section_dirs)>=2
    assert '## Slide 1' not in (section_dirs[-1]/'source_slices.md').read_text()
    assert '## Slide 5' in (section_dirs[-1]/'source_slices.md').read_text()
    ids=[n['id'] for d in section_dirs for n in records(d/'drafts.jsonl')]
    assert ids==[n['id'] for n in ns]
    assert len(records(folder(build)/'drafts.jsonl'))==81
    assert 'set-level' in (folder(build)/'PROMPT.md').read_text()

def test_student_rewrite_error_uses_own_line(build):
    reports(build,[finding()],[finding(codes=['V1'],rewrite={'Bad':'x'},attempt={'answer':'x','result':'right'})])
    p=apply(build); assert p.returncode==2 and 'student_report.jsonl: line 1' in p.stdout

def test_sheet_content_cannot_be_disguised_text(build):
    manifest=json.loads((build/'renders/sheets.json').read_text())
    Path(manifest['sheets'][0]['fronts']).write_text('secret source')
    p=packet(build); assert p.returncode==2 and 'image' in p.stdout

def test_missing_flagged_page_refuses_with_remedy(build):
    slides=json.loads((build/'source/slides.json').read_text()); slides['slides'][0]['flags']=['image_only']; dump(build/'source/slides.json',slides)
    p=packet(build); assert p.returncode==3 and '--page-image 1' in p.stdout

def test_corrupt_png_returns_located_error(build):
    manifest=json.loads((build/'renders/sheets.json').read_text())
    path=Path(manifest['sheets'][0]['fronts']); data=bytearray(path.read_bytes())
    pos=data.index(b'IDAT'); length=int.from_bytes(data[pos-4:pos],'big'); data[pos+4+length]^=1
    path.write_bytes(data)
    p=packet(build); assert p.returncode==2 and 'image invalid' in p.stdout and not p.stderr
