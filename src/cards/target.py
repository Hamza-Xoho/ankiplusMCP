"""Filename identity and flat deck names, ported from v1."""
import os, re

# COURSE_L001_DATE_topic  (date optional; L/Lec/Lecture; separators _ - or space)
PATTERN = re.compile(
    r"^(?P<course>[A-Za-z]{2,8}\s?\d{2,4})"      # MED241, BIO 101
    r"[_\-\s]+"
    r"(?:L|LEC|LECTURE)?[_\-\s]?(?P<num>\d{1,3})" # L001, Lecture 3, 07
    r"(?:[_\-\s]+(?P<date>\d{4}-\d{2}-\d{2}))?"   # optional ISO date
    r"[_\-\s]+(?P<topic>.+)$",
    re.IGNORECASE,
)

DEFAULT_ROOT = "#ColdRecall"

# words that stay lowercase inside a sentence-case title
_SMALL = {"and", "or", "of", "the", "in", "on", "to", "a", "an", "for", "with", "vs"}


def _titleise(slug):
    """anatomical-planes-position-and-terms -> Anatomical planes position and terms"""
    words = re.split(r"[-_\s]+", slug.strip())
    words = [w for w in words if w]
    if not words:
        return ""
    out = []
    for i, w in enumerate(words):
        # keep acronyms/roman numerals as-is
        if w.isupper() and len(w) > 1:
            out.append(w)
        elif i == 0:
            out.append(w[:1].upper() + w[1:].lower())
        elif w.lower() in _SMALL:
            out.append(w.lower())
        else:
            out.append(w.lower())
    return " ".join(out)


def _space_amp(text):
    """'Mitochondria& Golgi' -> 'Mitochondria & Golgi' (one space each side of &)."""
    return re.sub(r"\s*&\s*", " & ", text)


def tag_part(text):
    """One level of an Anki tag. Anki tags cannot contain spaces, and '::' is
    reserved for hierarchy, so: spaces -> '_', drop anything outside a safe set
    (parentheses and quotes break Anki searches), collapse repeats.
    'Cardiac cycle & ECG (part 2)' -> 'Cardiac_cycle_&_ECG_part_2'."""
    t = re.sub(r"\s+", "_", str(text).strip())
    t = t.replace("::", "_")
    t = re.sub(r"[^A-Za-z0-9_\-&.]", "", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def build(course, number, topic, subject=None, system=None, root=DEFAULT_ROOT):
    course_disp = re.sub(r"\s+", " ", course).strip()
    deck = topic.replace("::", " - ")
    src = f"{root}::#Source::{tag_part(course_disp)}::L{int(number):03d}_{tag_part(topic)}"
    out = {
        "deck": deck,
        "course": course_disp,
        "number": int(number),
        "topic": topic,
        "source_tag": src,
        "tier_tags": {str(t): f"{root}::!Tier::{t}" for t in (1, 2, 3)},
    }
    base = [src]
    if subject:
        out["subject_tag"] = f"{root}::^Subjects::{tag_part(subject)}"
        base.append(out["subject_tag"])
    if system:
        out["system_tag"] = f"{root}::^Systems::{tag_part(system)}"
        base.append(out["system_tag"])
    out["base_tags"] = base
    slug = re.sub(r"[^a-z0-9]+", "-", (topic or "").lower()).strip("-")
    out["legacy_src_tag"] = f"src::{re.sub(r'[^a-z0-9]+', '', course_disp.lower())}-l{int(number):03d}"
    out["legacy_topic_tag"] = f"topic::{slug}"
    return out


def parse(filename, subject=None, system=None, root=DEFAULT_ROOT):
    stem = os.path.splitext(os.path.basename(filename))[0]
    m = PATTERN.match(stem)
    if not m:
        return {"deck": None, "confident": False, "stem": stem,
                "why": "filename does not match COURSE_L###_[date]_topic — ask the "
                       "user for course (or book), number and title, then re-run with "
                       "--course/--number/--title"}
    course = re.sub(r"\s+", "", m.group("course")).upper()
    num = int(m.group("num"))
    topic_slug = m.group("topic")
    # strip a trailing date if it landed in the topic
    topic_slug = re.sub(r"[_\-\s]*\d{4}-\d{2}-\d{2}[_\-\s]*", " ", topic_slug).strip()
    topic = _titleise(topic_slug)
    out = build(course, num, topic, subject, system, root)
    # keep the exact legacy slug the original ankipro scheme produced
    out["legacy_topic_tag"] = "topic::" + re.sub(r"[^a-z0-9]+", "-", topic_slug.lower()).strip("-")
    out["confident"] = True
    return out

from .common.paths import Build
from .common.source_data import source_path, slides_data
from .common.files import read_json, write_json
from .common.errors import CardsError
from .common.output import Result

def run(args):
    folder = Build(args.build)
    slides = slides_data(folder)['slides']
    path, state = source_path(folder)
    manual = (args.course,args.number,args.title)
    if any(x is not None for x in manual):
        if not all(x is not None for x in manual) or args.number<1 or not args.course.strip() or not args.title.strip():
            raise CardsError('E31','target: line 1 field manual identity incomplete','supply --course --number --title together')
        out = build(args.course,args.number,_titleise(args.title) if args.title.islower() else args.title.strip(),args.subject,args.system)
        out['confident'] = True
    else:
        out = parse(path.name,args.subject,args.system)
    target_path = folder.path('target.json')
    if not out['confident']:
        write_json(target_path,{'confident':False,'deck':None},'cards target')
        return Result('FINDINGS',['What course, number and title should this lecture use?'],[target_path],1)
    listing = read_json(args.existing_decks)
    if not isinstance(listing,list) or not all(isinstance(x,str) for x in listing):
        raise CardsError('E31',f'{args.existing_decks}: line 1 field decks invalid','supply a JSON array of deck names')
    course = out['course']
    first = next((s['title'] for s in slides if s['n']==1),'')
    title = _space_amp(re.sub(r'\s+',' ',first.replace('::',' - '))).strip()
    title = re.sub(r'\s+(?:\d{4}-\d{2}-\d{2}|(?:slide\s*)?\d+(?:\s*/\s*\d+)?)\s*$','',title,flags=re.I).strip()
    usable = len(title)>=3 and title.casefold()!=course.casefold()
    deck = (title if usable else out['topic'].replace('::',' - '))[:100]
    own = state.get('facts',{}).get('deck_has_source_tag',False)
    if deck in listing and not own:
        suffix = f" ({course.replace('::',' - ')} L{out['number']:03d})"
        deck = deck[:max(0,100-len(suffix))]+suffix
    out.update(deck=deck,deck_source='slide1' if usable else 'filename',create_deck=deck not in listing,
               title=out.pop('topic'), note_type='ColdRecall Cloze')
    out['legacy_tags'] = [out.pop('legacy_src_tag'),out.pop('legacy_topic_tag'),
                          f"src::{tag_part(course)}::L{out['number']:03d}"]
    out.setdefault('subject_tag',None)
    out.setdefault('system_tag',None)
    write_json(target_path,out,'cards target')
    return Result(lines=[f"deck: {deck}",f"create_deck: {str(out['create_deck']).lower()}",out['source_tag']],files=[target_path])
