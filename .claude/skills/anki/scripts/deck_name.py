#!/usr/bin/env python3
"""
deck_name.py — derive the Anki deck name and AnKing-style tags for a source.

Two ways to call it:

  1. From a lecture filename (preferred — never invent what the filename says):
       python3 deck_name.py MED241_L001_2026-09-09_anatomical-planes-position-and-terms.pdf

  2. By hand, when the filename does not follow the convention and the user
     has told you the course (or book), the lecture/chapter number and title:
       python3 deck_name.py --course "Oral Histology" --number 12 --title "Enamel formation"

  Optional on either: --subject Histology  --system Dental  --root "#ColdRecall"

Output (JSON):
  {"deck": "MED241::1. Anatomical planes position and terms",
   "source_tag": "#ColdRecall::#Source::MED241::L001_Anatomical_planes_position_and_terms",
   "tier_tags": {"1": "#ColdRecall::!Tier::1", "2": "...", "3": "..."},
   "subject_tag": "#ColdRecall::^Subjects::Anatomy",       # only if --subject
   "system_tag": "#ColdRecall::^Systems::Musculoskeletal", # only if --system
   "base_tags": [source_tag, subject_tag?, system_tag?],    # put on every note
   "legacy_src_tag": "src::med241-l001",                   # older ankipro scheme
   "legacy_topic_tag": "topic::anatomical-planes-position-and-terms",
   "confident": true}

FILENAME CONVENTION:  COURSE _ L### _ [YYYY-MM-DD] _ topic-slug .pdf
    deck  ->  COURSE::<n>. <Topic in sentence case>

Anki's create_deck allows only TWO levels of nesting, so the deck is always
course :: lecture. Organisation beyond that lives in the tags, the way AnKing
does it: one root, then branches by source, subject, system and tier.

If the filename does not match, `confident` is false (exit code 2) and the
caller must ask the user rather than guessing.
"""
import argparse, json, os, re, sys

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
    deck_parent = course_disp
    deck = f"{deck_parent}::{number}. {topic}" if topic else f"{deck_parent}::{number}."
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


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("filename", nargs="?", help="lecture file, e.g. MED241_L001_..._topic.pdf")
    a.add_argument("--course", help="course code or book title (manual mode)")
    a.add_argument("--number", type=int, help="lecture or chapter number (manual mode)")
    a.add_argument("--title", help="lecture or chapter title (manual mode)")
    a.add_argument("--subject", help="discipline, e.g. Anatomy, Histology, Pharmacology")
    a.add_argument("--system", help="organ system, e.g. Cardio, Renal (medicine/dentistry)")
    a.add_argument("--root", default=DEFAULT_ROOT, help="tag root (default %(default)s)")
    ns = a.parse_args()

    if ns.course or ns.number is not None or ns.title:
        if not (ns.course and ns.number is not None and ns.title):
            a.error("manual mode needs all three: --course, --number and --title")
        r = build(ns.course, ns.number, _titleise(ns.title) if ns.title.islower() else ns.title.strip(),
                  ns.subject, ns.system, ns.root)
        r["confident"] = True
    elif ns.filename:
        r = parse(ns.filename, ns.subject, ns.system, ns.root)
    else:
        a.error("give a filename, or --course/--number/--title")
    print(json.dumps(r, indent=2, ensure_ascii=False))
    if not r["confident"]:
        sys.exit(2)
