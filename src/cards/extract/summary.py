"""Pre-digest each slide into the atoms a drafter needs.

This is heuristic guidance, never authority: the drafter still reads exact
wording through `cards source --slides N`. The point is to stop a drafter
missing a fact that is plainly on the slide.
"""
import re

BULLET = re.compile(r'^\s*(?:[•●▪·‣]|[-*]|\d+[.)])\s+')
SENTENCE = re.compile(r'(?<=[.!?])\s+')
STOP = {'and', 'the', 'of', 'in', 'to', 'is', 'are', 'with', 'all', 'both', 'from', 'into',
        'on', 'for', 'within', 'that', 'this', 'which', 'its', 'their', 'a', 'an', 'as',
        'by', 'or', 'be', 'can', 'may', 'each', 'also', 'describe', 'identify', 'explain',
        'understand', 'list', 'name', 'define', 'discuss'}

# firstName, pattern: the label is what a drafter would write in `type`.
TYPES = [
    ('origin', r'\boriginat|\borigins?\b|\barises? from\b'),
    ('insertion', r'\binserts?\b|\binsertion\b'),
    ('innervation', r'\binnervat|\bnerve\b|\bsupplied by\b|\bsupply\b'),
    ('blood_supply', r'\barter(y|ies)\b|\bvein\b|\bblood\b|\bvascular'),
    ('action', r'\bactions?\b|\bflex|\bextend|\brotat|\babduct|\badduct|\belevat|\bdepress'),
    ('relation', r'\brelations?\b|\bmedial\b|\blateral\b|\bposterior\b|\banterior\b|\bsuperficial\b|\bdeep\b'),
    ('definition', r'\bis\b|\bare\b|\bincludes?\b|\bconsists? of\b|\bcomprises?\b'),
]


def stems(text):
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    return {word[:5] for word in words if word not in STOP}


def slug(text):
    value = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return value[:40].strip('-') or 'misc'


def clean(text):
    return re.sub(r'\s+', ' ', BULLET.sub('', text)).strip()


def _type(text):
    for name, pattern in TYPES:
        if re.search(pattern, text, re.I):
            return name
    return 'other'


def _fact_text(line):
    text = clean(line).rstrip(' .;:')
    text = re.sub(r'\s*[•●▪]\s*', ' ', text)
    return text.strip()


def _bullets(text):
    return [line for line in text.splitlines() if BULLET.match(line)]


def _summary(text, title):
    bullets = [clean(line) for line in _bullets(text) if clean(line)]
    if len(bullets) >= 2:
        value = ', '.join(bullet.rstrip(' .') for bullet in bullets[:4])
    else:
        value = clean(next((line for line in text.splitlines() if clean(line)), ''))
    value = value or title
    if len(value) > 160:
        value = value[:160].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'
    return value


def _facts(text, title, objective_ids):
    """Bullet points and factual sentences, deduplicated and trimmed."""
    facts, seen = [], set()
    lines = text.splitlines() or [text]
    for line in lines:
        bullet = bool(BULLET.match(line))
        for sentence in SENTENCE.split(clean(line)) if line.strip() else []:
            value = _fact_text(sentence)
            if not 15 <= len(value) <= 240 or value.casefold() == clean(title).casefold():
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            facts.append({'text': value, 'type': _type(value), 'bullet': bullet})
    facts.sort(key=lambda item: not item['bullet'])  # bullets lead, stable otherwise
    return facts[:12]


def _objectives_for(text, objectives):
    """Objective ids whose keywords also occur on this slide."""
    words = stems(text)
    matched = []
    for item in objectives:
        overlap = stems(item['text']) & words
        if len(overlap) >= 2:
            matched.append(item['id'])
    return matched


def _tier(fact, objectives, slide_objectives):
    owners = [item for item in objectives if item['id'] in slide_objectives]
    for item in owners:
        if stems(fact['text']) & stems(item['text']):
            return 1
    if len(slide_objectives) == 1:
        return 1
    return 2 if (fact['bullet'] or fact['type'] != 'other') else 3


def _objective(fact, objectives, slide_objectives):
    for item in objectives:
        if item['id'] in slide_objectives and stems(fact['text']) & stems(item['text']):
            return item['id']
    return slide_objectives[0] if len(slide_objectives) == 1 else None


def _figures(slide):
    result = []
    for figure in slide.get('figures') or []:
        labels = list(dict.fromkeys(
            region.get('text', '').strip()
            for region in figure.get('ocr_labels') or []
            if isinstance(region, dict) and region.get('text', '').strip()))
        kind = 'anatomy_diagram' if len(labels) >= 5 else ('diagram' if labels else 'image')
        result.append({'id': figure.get('fig_id'), 'file': figure.get('file'),
                       'label_count': len(labels), 'type': kind,
                       'label_summary': ', '.join(labels)[:400]})
    return result


def build(lecture, slides, objectives):
    objectives = [{'id': item['id'], 'text': clean(item['text']).rstrip('.')}
                  for item in objectives]
    title = next((clean(slide['title']) for slide in slides if clean(slide.get('title', ''))), '')
    pages = []
    for slide in slides:
        text = slide.get('text', '')
        slide_objectives = _objectives_for(' '.join([slide.get('title', ''), text]), objectives)
        group = slug(slide.get('title') or '')
        facts = []
        for fact in _facts(text, slide.get('title', ''), slide_objectives):
            facts.append({'text': fact['text'],
                          'tier': _tier(fact, objectives, slide_objectives),
                          'objective': _objective(fact, objectives, slide_objectives),
                          'group': group, 'type': fact['type']})
        pages.append({'page': slide['n'],
                      'title': clean(slide.get('title', '')),
                      'summary': _summary(text, clean(slide.get('title', ''))),
                      'key_facts': facts,
                      'figures': _figures(slide),
                      'objectives_covered': slide_objectives,
                      'word_count': slide.get('word_count', len(text.split())),
                      'flags': list(slide.get('flags') or [])})
    return {'lecture': lecture, 'title': title or lecture,
            'slides': pages, 'objectives': objectives}