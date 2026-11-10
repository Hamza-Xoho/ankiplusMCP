"""Allowlisted, independent reviewer inputs. Never include author reasoning."""
from pathlib import Path
import re
import shutil
from PIL import Image, ImageDraw
from cards.common.paths import Build
from cards.common.files import read_json, read_jsonl, write_json, write_jsonl, write_text
from cards.common.errors import CardsError, Refused
from cards.common.output import Result
from cards.common.size import tokens
from cards.source import slice_text

TEMPLATES = Path(__file__).resolve().parents[1]/'templates/review'


def image_path(build, relative):
    path = build.path(relative)
    try:
        if path.suffix.lower() != '.png':
            raise ValueError('PNG required')
        with Image.open(path) as image:
            if image.format != 'PNG': raise ValueError('PNG required')
            image.verify()
    except (OSError, ValueError, SyntaxError) as exc:
        raise CardsError('E60', f'{path}: line 1 field image invalid', 'render a PNG image inside the build') from exc
    return path


def packet_directory(build, relative):
    # Build.path resolves symlinks; deletion must also reject aliases inside the build.
    raw = build.root / relative
    for path in [raw, *raw.parents]:
        if path == build.root: break
        if path.is_symlink():
            raise CardsError('E60', f'{raw}: line 1 field packet symlink', 'use real packet directories')
    return build.path(relative)


def scoped_sheets(build, sheets, ids, destination):
    """Rebuild mixed sheets from per-card images so round 2 exposes no other notes."""
    result=[]
    for index, sheet in enumerate(sheets,1):
        selected=[n for n in sheet['notes'] if n in ids]
        if not selected:
            continue
        pair={'notes':selected}
        for side in ('fronts','backs'):
            relative=f'sheets/{index:02d}_{side}.png'
            out=build.path(destination/relative)
            out.parent.mkdir(parents=True,exist_ok=True)
            if selected==sheet['notes']:
                shutil.copyfile(image_path(build, sheet[side]), out)
            else:
                images=[]
                for nid in selected:
                    if not re.fullmatch(r'[A-Za-z0-9_-]+',nid):
                        raise CardsError('E60','drafts: line 1 field id unsafe','run cards check')
                    paths=sorted(build.path('renders/cards').glob(nid+'_c*_front.png')) if side=='fronts' else [build.path(f'renders/cards/{nid}_back.png')]
                    if not paths:
                        raise Refused('E60',f'{nid}: line 1 field renders missing','run cards render first')
                    for path in paths:
                        with Image.open(image_path(build, path)) as im:
                            images.append((path.stem, im.convert('RGB').copy()))
                width=max(im.width for _,im in images)
                canvas=Image.new('RGB',(width,sum(im.height+24 for _,im in images)), '#222222')
                draw=ImageDraw.Draw(canvas); y=0
                for label,im in images:
                    draw.text((3,y+3),label,fill='white'); canvas.paste(im,(0,y+24)); y+=im.height+24
                canvas.save(out)
            pair[side]=relative
        result.append(pair)
    return result


def run(args):
    b=Build(args.build)
    check=read_json(b.path('checks/check.json'))
    if any(f.get('severity')=='blocker' for f in check['findings']):
        raise Refused('E60','check.json: unresolved blockers','run cards check and fix blockers first')
    notes=[n for n in read_jsonl(b.path('drafts.jsonl')) if n.get('status')!='dropped']
    ids={n['id'] for n in notes}
    if args.only:
        selected=set(args.only.split(','))
        if not selected<=ids:
            raise CardsError('E60','only: line 1 field id unknown','use active draft ids')
        groups={n.get('group') for n in notes if n['id'] in selected and n.get('group')}
        notes=[n for n in notes if n['id'] in selected or n.get('group') in groups]
        ids={n['id'] for n in notes}
    slides=read_json(b.path('source/slides.json'))
    cited={s for n in notes for s in n['source_ref']}
    numbers={s['n'] for s in slides['slides'] if any(abs(s['n']-c)<=1 for c in cited)}
    target=read_json(b.path('target.json'))
    sheets=read_json(b.path('renders/sheets.json'))['sheets']
    relevant=[s for s in sheets if set(s['notes']) & ids]
    chosen=list(relevant)
    if len(relevant)>6 and args.student_subset!='all':
        tier1={n['id'] for n in notes if n['tier']==1}
        chosen=[s for s in relevant if set(s['notes']) & tier1]
        covered={x for s in chosen for x in s['notes']}
        for group in dict.fromkeys(n.get('group') for n in notes):
            members={n['id'] for n in notes if n.get('group')==group}
            if not members & covered:
                match=next((s for s in relevant if set(s['notes']) & members),None)
                if match is None:
                    raise Refused('E60','sheets.json: line 1 field notes missing','render all active notes')
                if match not in chosen: chosen.append(match)
                covered.update(match['notes'])
    if not ids <= {x for s in relevant for x in s['notes']}:
        raise Refused('E60','sheets.json: line 1 field notes missing','render all active notes')
    rounddir=Path(f'review/round{args.round}')
    # Preflight sources before replacing previous packets. Reports are siblings, never deleted.
    for s in relevant:
        for side in ('fronts','backs'):
            if not b.path(s[side]).is_file(): raise Refused('E60',f'{s[side]}: image missing','run cards render')
    for reviewer in ('maintainer','student','maintainer-sections'):
        packet_directory(b,rounddir/reviewer)
    for n in notes:
        if n.get('preview'): image_path(b,n['preview'])
    for sheet in relevant:
        for side in ('fronts','backs'): image_path(b,sheet[side])
    for reviewer in ('maintainer','student'):
        dest=rounddir/reviewer
        directory=packet_directory(b,dest)
        if directory.exists(): shutil.rmtree(directory)
        directory.mkdir(parents=True)
        for name in ('brief.md','rubric.md','report-format.md'):
            write_text(b.path(dest/name),(TEMPLATES/reviewer/name).read_text(),'cards packets')
    m=rounddir/'maintainer'; st=rounddir/'student'
    write_jsonl(b.path(m/'drafts.jsonl'),notes,'cards packets')
    write_text(b.path(m/'house-style.md'),(TEMPLATES/'house-style.md').read_text(),'cards packets')
    write_text(b.path(m/'source_slices.md'),slice_text(slides,numbers),'cards packets')
    write_text(b.path(m/'map.md'),b.path('source/map.md').read_text(),'cards packets')
    for source, name in [('source/objectives.json','objectives.json'),('checks/check.json','check.json')]:
        data=read_json(b.path(source)); data.pop('_meta',None); write_json(b.path(m/name),data,'cards packets')
    legacy=target.get('legacy_tags',[])
    queries=[f'tag:{target["source_tag"]}',*[f'tag:{tag}' for tag in legacy]]
    if not legacy:
        match=re.search(r'::([A-Z]+\d+)::L(\d+)',target['source_tag'])
        if match: queries.append(f'tag:src::{match[1].lower()}-l{match[2]}')
    # AnKing lecture tags are block/session shaped (e.g. W4::4-Wed::L029), not
    # course shaped. Search the lecture number anywhere in the tag tree; a
    # title-only search misses those notes until a reviewer finds them late.
    lecture=target.get('number')
    if lecture is None:
        match=re.search(r'(?<![A-Za-z0-9])L(\d{1,3})(?!\d)',str(target.get('source_tag','')))
        lecture=match[1] if match else None
    if lecture:
        lid=f'L{int(lecture):03d}'
        queries += [f'tag:*{lid}*',f'deck:*AnKing* tag:*{lid}*']
    terms=list(dict.fromkeys(s['title'] for s in slides['slides'] if s['n'] in cited))
    queries += [f'deck:*AnKing* "{term.replace(chr(34), chr(39))}"' for term in terms]
    write_text(b.path(m/'reconcile.md'),'# Reconcile\nRun source, legacy and AnKing searches with find_notes; inspect matches with notes_info. AnKing lecture tags look like `W4::4-Wed::L029`; treat those matches as overlap too. Propose AnKing unsuspends instead of duplicates.\n'+'\n'.join(queries),'cards packets')
    pages=[]
    for slide in slides['slides']:
        if slide['n'] in cited and slide.get('flags'):
            relative=f'source/pages/p{slide["n"]:02d}.png'
            if not b.path(relative).exists():
                raise Refused('E60',f'{relative}: line 1 field page image missing',f'run cards source --build {args.build} --page-image {slide["n"]}')
            out=m/'pages'/Path(relative).name; b.path(out).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(image_path(b,relative),b.path(out)); pages.append(str(out.relative_to(m)))
    # Never enumerate images in PROMPT.md: a long lecture would exceed the token
    # budget. The prompt names this manifest and the reviewer opens every PNG in it.
    if pages:
        write_text(b.path(m/'pages'/'images.md'),'# Page images\n\n'+''.join(f'- {Path(p).name}\n' for p in pages),'cards packets')
    manifest=scoped_sheets(b,chosen,ids,st)
    previews=[]
    for n in notes:
        if n.get('preview'):
            source=image_path(b,n['preview']); relative=Path('previews')/source.name
            b.path(st/relative).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,b.path(st/relative)); previews.append(str(relative))
    write_json(b.path(st/'sheets.json'),{'sheets':manifest,'previews':previews},'cards packets')
    omitted=[str(i) for i,s in enumerate(sheets,1) if s not in chosen]
    for reviewer in ('maintainer','student'):
        dest=rounddir/reviewer
        prompt=(TEMPLATES/'PROMPT.md').read_text().format(
            agent='anki-'+reviewer,
            inputs=('Read drafts.jsonl, source_slices.md, map.md, objectives.json, check.json, house-style.md and reconcile.md.' if reviewer=='maintainer' else 'Read sheets.json; it names every sheet and preview. Use only this packet.'),
            images=('pages/images.md' if pages else 'pages/ (none)') if reviewer=='maintainer' else 'sheets.json',
            context=('The brief placeholders mean drafts.jsonl, source_slices.md, objectives.json and house-style.md. Run reconcile.md searches instead of existing.jsonl.' if reviewer=='maintainer' else 'The brief manifest path means sheets.json in this packet.'),
            omitted=('Sheet pairs omitted: '+(', '.join(omitted) or 'none')+'.') if reviewer=='student' else '',
            report=str(b.path(rounddir/(reviewer+'_report.md'))))
        if tokens(prompt)+30>300:
            raise CardsError('E60','PROMPT.md: line 1 field size exceeds 300 tokens','shorten the build path or image list')
        write_text(b.path(dest/'PROMPT.md'),prompt,'cards packets')
    sections=b.path(rounddir/'maintainer-sections')
    if sections.exists(): shutil.rmtree(sections)
    if len(notes)>80:
        # Main maintainer packet retains all drafts for the set-level review.
        main_prompt=b.path(m/'PROMPT.md')
        write_text(main_prompt,main_prompt.read_text().partition('\n')[2]+'Review set-level rules S1–S9 only; section agents handle per-note rules.\n','cards packets')
        for start in range(0,len(notes),80):
            index=start//80+1
            dest=rounddir/'maintainer-sections'/f'{index:02d}'
            directory=packet_directory(b,dest)
            shutil.copytree(b.path(m),directory)
            subset=notes[start:start+80]
            write_jsonl(b.path(dest/'drafts.jsonl'),subset,'cards packets')
            section_cited={i for n in subset for i in n['source_ref']}
            section_numbers={slide['n'] for slide in slides['slides'] if any(abs(slide['n']-i)<=1 for i in section_cited)}
            write_text(b.path(dest/'source_slices.md'),slice_text(slides,section_numbers),'cards packets')
            page_dir=b.path(dest/'pages')
            if page_dir.exists():
                for page in page_dir.iterdir():
                    match=re.fullmatch(r'p([0-9]+)\.png',page.name)
                    if not match or int(match[1]) not in section_cited: b.path(page).unlink()
            section_pages=sorted(page.name for page in page_dir.glob('*.png')) if page_dir.exists() else []
            if section_pages:
                write_text(b.path(dest/'pages'/'images.md'),'# Page images\n\n'+''.join(f'- {page}\n' for page in section_pages),'cards packets')
            else:
                manifest=b.path(dest/'pages'/'images.md')
                if manifest.exists(): manifest.unlink()
            report=b.path(rounddir/f'maintainer_section{index:02d}_report.md')
            prompt=(TEMPLATES/'PROMPT.md').read_text().format(agent='anki-maintainer',inputs='Read drafts.jsonl, source_slices.md, map.md, objectives.json, check.json, house-style.md and reconcile.md. Review per-note A1–A13 only.',context='Use packet-local paths in the brief.',images=('pages/images.md' if section_pages else 'pages/ (none)'),omitted='',report=str(report))
            write_text(b.path(dest/'PROMPT.md'),prompt,'cards packets')
    for prompt_path in b.path(rounddir).rglob('PROMPT.md'):
        if tokens(b.path(prompt_path).read_text())>300:
            raise CardsError('E60',f'{prompt_path}: line 1 field size exceeds 300 tokens','shorten build path or prompt template')
    state=read_json(b.state); state.setdefault('review',{})['round']=args.round
    write_json(b.state,state,'cards packets')
    return Result('OK',[f'anki-maintainer: {sum(p.is_file() for p in b.path(m).rglob("*"))} files',f'anki-student: {sum(p.is_file() for p in b.path(st).rglob("*"))} files', *([f'anki-maintainer sections: {sections} (launch each PROMPT.md)'] if len(notes)>80 else [])],[b.path(m/'PROMPT.md'),b.path(st/'PROMPT.md')])
