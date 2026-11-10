"""Section-based text sources."""
import re

def read(path):
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeError as exc:
        from ..common.errors import CardsError
        raise CardsError('E21',f'{path}: line 1 field encoding unreadable',
                         'supply a UTF-8 text file') from exc
    lines = text.splitlines()
    sections = []
    title, body = '', []
    for line in lines:
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if match:
            if title or any(x.strip() for x in body):
                sections.append((title, '\n'.join(body).strip()))
            title, body = match[1], []
        else:
            body.append(line)
    if title or body:
        sections.append((title, '\n'.join(body).strip()))
    if not any(re.match(r'^#{1,6}\s', l) for l in lines):
        sections = [('', b.strip()) for b in re.split(r'\n\s*\n',text) if b.strip()]
    return [{'n':n,'title':t or b.splitlines()[0][:100], 'text':b,
             'speaker_notes':'','figures':[], 'flags':[]} for n,(t,b) in enumerate(sections,1)]
