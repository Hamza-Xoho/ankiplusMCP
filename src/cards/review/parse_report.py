"""Parse the Markdown review reports subagents write.

The old JSONL reports are strict to *produce* and fragile to read back. The
Markdown form is easy for a reviewer to write; this module turns it into the
same internal `rows` that `cards apply` already consumes. Parse errors always
name the file, the exact line and the field.
"""
import re

from cards.common.errors import CardsError

NOTE = re.compile(r'^##\s+Note\s+([A-Za-z0-9_-]+)\s*(?:[—–-]\s*(.*))?$', re.I)
SET = re.compile(r'^##\s+Set Finding\s*(?:[—–-]\s*(.*))?$', re.I)
SUMMARY = re.compile(r'^##\s+Summary\s*$', re.I)
HEADER = re.compile(r'^#\s+Review Report\s*(?:[—–-]\s*(.*))?$', re.I)
FIELD = re.compile(r'^\*\*\s*([^*]+?)\s*\*\*\s*(.*)$')
HEADLINE = re.compile(r'^(PASS|FIX|REJECT)\b\s*(?:[—–-]\s*(.*))?$', re.I)
BLOCKER = re.compile(r'\(\s*blocker\s*\)', re.I)
RESULT = ('right', 'alternative', 'unknowable')
ARROW = re.compile(r'(?:→|->|=>)\s*(right|alternative|unknowable)\b', re.I)
# Reviewers write per-cloze attempts; the note's result is the worst one.
SEVERITY = {'right': 0, 'unknowable': 1, 'alternative': 2}

FIELDS = {'text': 'Text', 'extra': 'Extra', 'header': 'Header', 'back extra': 'Back Extra',
          'comments': 'Comments', 'occlusion': 'Occlusion', 'image': 'Image'}


def invalid(path, line, field):
    raise CardsError('E61', f'{path}: line {line} field {field} invalid',
                     'repair the reviewer Markdown report')


def _read(path):
    try:
        return path.read_text(encoding='utf-8')
    except (UnicodeError, OSError) as exc:
        raise CardsError('E61', f'{path}: line 1 field report unreadable',
                         'write the report as UTF-8 Markdown') from exc


def _codes(reviewer, value, path, line):
    codes = [code.upper() for code in re.findall(r'\b([A-Za-z]\d+)\b', value or '')]
    allowed = ({f'A{i}' for i in range(1, 14)} if reviewer == 'maintainer'
               else {f'V{i}' for i in range(1, 10)})
    if any(code not in allowed for code in codes):
        invalid(path, line, 'codes')
    return list(dict.fromkeys(codes))


def _fields(lines, path, single_line_fields=()):
    """`**Name:** value` plus continuation lines until the next field."""
    values, name, buffer, start = {}, None, [], None

    def flush():
        if name is None:
            return
        text = ' '.join(part for part in buffer if part).strip()
        text = re.sub(r'^`{1,3}\s*|\s*`{1,3}$', '', text).strip()
        values[name] = (start, text)

    for number, line in lines:
        match = FIELD.match(line)
        if match:
            flush()
            name = match.group(1).strip().rstrip(':').strip().lower()
            buffer, start = [match.group(2).strip()], number
        elif name is not None:
            if line.startswith('#'):
                invalid(path, number, 'field')
            if name not in single_line_fields:
                buffer.append(line.strip())
    flush()
    return values


def _truthy(value):
    return value.strip().lower() in {'yes', 'true', '1', 'blocker'}


def _rewrite(reviewer, fields, known, path, line):
    rewrite = {}
    for name, (number, value) in fields.items():
        if not name.startswith('rewrite'):
            continue
        field = name[len('rewrite'):].strip()
        key = FIELDS.get(field, ' '.join(word.capitalize() for word in field.split()))
        if key.lower() in ('tags', 'tag', 'objective'):
            continue
        if known is not None and key not in known:
            # Ignore no-op foreign fields, but never silently lose a correction.
            if key in FIELDS.values() and value.lower() == 'unchanged':
                continue
            invalid(path, number, 'rewrite fields')
        if value and value.lower() != 'unchanged':
            rewrite[key] = value
    return rewrite or None


def _attempt(reviewer, fields, path, line):
    if reviewer != 'student':
        return None
    answer = result = None
    for name, (number, value) in fields.items():
        if name in ('attempt', 'attempt answer', 'answer'):
            answer = value
        elif name in ('attempt result', 'result'):
            result = value.strip().lower()
    if answer is not None and result is None:
        found = [item.lower() for item in ARROW.findall(answer)]
        if found:
            result = max(found, key=SEVERITY.__getitem__)
            if len(found) == 1:
                answer = re.split(r'\s*(?:→|->|=>)\s*', answer, maxsplit=1)[0].strip()
    if not isinstance(answer, str) or result not in RESULT:
        invalid(path, line, 'attempt')
    return {'answer': answer, 'result': result}


def _note(reviewer, ident, rest, line, body, ids, fields, path):
    match = HEADLINE.match(rest.strip()) if rest else None
    if not match:
        invalid(path, line, 'verdict')
    verdict = match.group(1).lower()
    if ids is not None and ident not in ids:
        invalid(path, line, 'note_id')
    values = _fields(body, path)
    codes = _codes(reviewer, match.group(2), path, line)
    blocker = bool(BLOCKER.search(rest or ''))
    card = None
    if 'card' in values:
        card = values['card'][1].strip().strip('`')
        card = None if card.lower() in ('', 'none', 'null') else card
        if card is not None and not re.fullmatch(r'c[1-9][0-9]*', card):
            invalid(path, values['card'][0], 'card')
    evidence = values.get('evidence', (line, ''))[1]
    if 'blocker' in values:
        blocker = _truthy(values['blocker'][1])
    known = fields[ident] if fields is not None and ident in fields else None
    rewrite = _rewrite(reviewer, values, known, path, line)
    if known is None and rewrite is not None:
        rewrite = {key: value for key, value in rewrite.items() if key in FIELDS.values()}
    attempt = _attempt(reviewer, values, path, line)
    row = {'type': 'note', 'reviewer': reviewer, 'note_id': ident, 'card': card,
           'verdict': verdict, 'codes': codes, 'blocker': blocker and verdict != 'pass',
           'evidence': evidence, 'rewrite': rewrite}
    if reviewer == 'student':
        row['attempt'] = attempt
        if 'V2' in codes and attempt['result'] == 'alternative':
            row['codes'] = [*codes, 'A2']
            row['blocker'] = True
    return row


def _set(reviewer, rest, line, body, ids, path):
    match = re.search(r'\b([A-Za-z]\d+)\b', rest or '')
    if not match:
        invalid(path, line, 'code')
    code = match.group(1).upper()
    allowed = ({f'S{i}' for i in range(1, 10)} if reviewer == 'maintainer'
               else {f'V{i}' for i in range(1, 10)})
    if code not in allowed:
        invalid(path, line, 'code')
    values = _fields(body, path)
    # A semicolon separates the ID list from optional reviewer commentary.
    raw_notes, _, commentary = values.get('notes affected', (line, ''))[1].partition(';')
    if ids is not None and any(re.search(r'(?<![\w-])' + re.escape(ident) + r'(?![\w-])', commentary)
                               for ident in ids):
        invalid(path, line, 'notes: use commas between IDs')
    notes = [part.strip().strip('`') for part in re.split(r'[,\s]+', raw_notes)
             if part.strip()]
    if ids is not None and any(note not in ids for note in notes):
        invalid(path, line, 'notes')
    if not notes:
        invalid(path, line, 'notes affected')
    finding = values.get('finding', (line, ''))[1]
    fix = values.get('fix', (line, ''))[1]
    if not finding or not fix:
        invalid(path, line, 'finding/fix')
    return {'type': 'set', 'reviewer': reviewer, 'code': code, 'notes': notes,
            'finding': finding, 'fix': fix}


def _summary(reviewer, line, body, path):
    # Stats are a single-line record; closing prose is not part of a count.
    values = _fields(body, path, single_line_fields={'stats'})
    verdict = values.get('verdict', (line, ''))[1].strip().upper()
    if verdict not in ('PASS', 'PASS_WITH_FIXES', 'FAIL'):
        invalid(path, line, 'summary')
    stats = {}
    raw = values.get('stats', (line, ''))[1]
    for part in filter(None, (item.strip() for item in raw.split(','))):
        key, sep, value = part.partition('=')
        value = re.sub(r'\s*\(.*', '', value).strip()
        if not sep or not re.fullmatch(r'-?\d+', value):
            invalid(path, values['stats'][0], 'stats')
        stats[key.strip()] = int(value)
    if not stats:
        invalid(path, line, 'stats')
    return {'type': 'summary', 'reviewer': reviewer, 'verdict': verdict, 'stats': stats}


def parse(path, reviewer, ids=None, fields=None):
    """Rows in file order: note and set records, then exactly one summary."""
    lines = _read(path).splitlines()
    sections, current = [], None
    header = None
    for number, line in enumerate(lines, 1):
        found = HEADER.match(line)
        if found:
            name = (found.group(1) or '').strip().lstrip('-').strip()
            header = (number, name.lower().removeprefix('anki-').strip())
            continue
        if line.startswith('## '):
            if SUMMARY.match(line):
                kind, match = 'summary', None
            elif (match := NOTE.match(line)):
                kind = 'note'
            elif (match := SET.match(line)):
                kind = 'set'
            else:
                invalid(path, number, 'section')
            current = {'kind': kind, 'line': number, 'match': match, 'body': []}
            sections.append(current)
            continue
        if current is not None:
            current['body'].append((number, line))
    if header and header[1] and header[1] != reviewer:
        invalid(path, header[0], 'reviewer')
    rows, closed = [], False
    for section in sections:
        if closed:
            invalid(path, section['line'], 'record after summary')
        if section['kind'] == 'note':
            rows.append(_note(reviewer, section['match'].group(1), section['match'].group(2),
                              section['line'], section['body'], ids, fields, path))
        elif section['kind'] == 'set':
            rows.append(_set(reviewer, section['match'].group(1), section['line'],
                             section['body'], ids, path))
        else:
            rows.append(_summary(reviewer, section['line'], section['body'], path))
            closed = True
    if not closed:
        invalid(path, len(lines) + 1, 'closing summary missing')
    return rows


def summary(path, reviewer=None):
    """The summary verdict alone, for the gate; INVALID when malformed."""
    try:
        found = _header_reviewer(path)
        if reviewer and found != reviewer:
            return 'INVALID', {}
        rows = [row for row in parse(path, found) if row['type'] == 'summary']
    except CardsError:
        return 'INVALID', {}
    return (rows[0]['verdict'], rows[0]['stats']) if len(rows) == 1 else ('INVALID', {})


def _header_reviewer(path):
    text = _read(path)
    for line in text.splitlines():
        found = HEADER.match(line)
        if found:
            name = (found.group(1) or '').strip().lstrip('-').strip().lower()
            return name.removeprefix('anki-').strip() or 'maintainer'
    return 'maintainer'