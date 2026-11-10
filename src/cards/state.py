"""Build initialization, facts and resumable phase history."""
from datetime import date
import json
import os
from pathlib import Path
import re
from .common.errors import CardsError
from .common.files import VERSION, now, read_json, write_json, _write
from .common.hashing import sha256_file
from .common.output import Result
from .common.paths import Build

FACTS = {'anki_reachable': bool, 'note_type_exists': bool, 'deck_exists': bool,
         'deck_has_source_tag': bool, 'existing_note_count': int, 'deck_decision': str}
PHASES = [f'P{i}' for i in range(8)] + ['done']
# Detailed skill phase files; an empty name means the SKILL.md phase map is enough.
PHASE_INFO = [
    ('Preflight', 'source readable', 'cards state get', ''),
    ('Extract+target', 'preflight complete', 'cards extract', ''),
    ('Draft', 'source and target ready', 'cards source --all', 'draft.md'),
    ('Check+render', 'drafts ready', 'cards check', ''),
    ('Review', 'checks and renders ready', 'cards packets', ''),
    ('Gate', 'review reports applied', 'cards gate', 'write.md'),
    ('Write', 'gate passed', 'cards write', 'write.md'),
    ('Report', 'write complete', 'cards report', 'write.md'),
]

def invalid(build, field, remedy='repair build.json from the backup or correct the input'):
    raise CardsError('E12', f'{build.state}: line 1 field {field} invalid', remedy)

def load(build):
    path = build.state
    try:
        data = read_json(path)
    except CardsError:
        # Preserve raw bytes; never replace or reinterpret the corrupt state.
        backup = build.path('build.json.' + sha256_file(path)[:12] + '.corrupt.bak')
        backup.write_bytes(path.read_bytes())
        raise
    if not isinstance(data, dict):
        invalid(build, 'root')
    required = {'_meta': dict, 'build_id': str, 'job': str, 'source': dict, 'phase': str,
                'history': list, 'facts': dict, 'review': dict, 'gate': dict, 'write': dict, 'tools': dict}
    for key, kind in required.items():
        if not isinstance(data.get(key), kind):
            invalid(build, key)
    if data['phase'] not in PHASES:
        invalid(build, 'phase')
    if data['job'] != 'build':
        invalid(build, 'job')
    for key in ['path', 'sha256', 'kind']:
        if not isinstance(data['source'].get(key), str):
            invalid(build, 'source.'+key)
    if not re.fullmatch('[0-9a-f]{64}', data['source']['sha256']):
        invalid(build, 'source.sha256')
    for key, value in data['facts'].items():
        if key not in FACTS or type(value) is not FACTS[key]:
            invalid(build, 'facts.'+key)
    for entry in data['history']:
        if (not isinstance(entry, dict) or entry.get('phase') not in PHASES
                or entry.get('status') not in {'start', 'done'}
                or not isinstance(entry.get('started_at'), str)
                or (entry.get('status') == 'done' and not isinstance(entry.get('ended_at'), str))):
            invalid(build, 'history')
    if data['gate'].get('status') not in {'pending', 'passed', 'failed'}:
        invalid(build, 'gate.status')
    return data

def init(args):
    source = Path(args.source).resolve()
    if not source.is_file():
        raise CardsError('E10', f'{source}: line 1 field source is not a file', 'supply an available local source file')
    lectures = set(re.findall(r'(?i)(?<![A-Za-z0-9])L\s*(\d{1,3})(?!\d)', source.stem))
    if len(lectures) > 1 or re.search(r'(?i)\b(?:merged|combined|compilation)\b', source.stem):
        raise CardsError('E10', f'{source}: line 1 field source is a multi-lecture or merged file',
                         'use one lecture PDF per build; v1 does not merge lectures')
    digest = sha256_file(source)
    # Default to ./builds (the contract); CARDS_BUILDS lets an installed skill keep
    # builds in a stable workspace without changing the cwd-relative default.
    builds = Path(os.environ.get('CARDS_BUILDS', 'builds')).expanduser().resolve()
    for path in sorted(builds.glob('*/build.json')):
        build = Build(path.parent)
        data = load(build)
        if data['source']['sha256'] == digest:
            _write(builds/'.current', build.root.name+'\n')
            return Result(lines=[f'{data["build_id"]} · {data["phase"]}'], files=[build.state])
    match = re.search(r'([A-Za-z]+\d+)[_-]L(\d+)', source.stem)
    lecture = f'{match[1].upper()}-L{int(match[2]):03d}' if match else re.sub(r'[^\w-]+', '-', source.stem).strip('-') or 'source'
    build_id = f'{date.today().isoformat()}_{lecture}'
    build = Build(builds/build_id)
    if build.root.exists():
        build_id += '-'+digest[:12]
        build = Build(builds/build_id)
        if build.root.exists():
            raise CardsError('E10', f'{build.state}: line 1 field build_id collision', 'inspect the existing build; preserve its state')
    data = {'build_id': build_id, 'job': args.job, 'source': {'path': str(source), 'sha256': digest,
            'kind': 'pdf' if source.suffix.lower() == '.pdf' else 'text', 'slides': None}, 'phase': 'P0',
            'history': [], 'facts': {}, 'review': {'round': 0, 'maintainer': None, 'student': None},
            'gate': {'status': 'pending', 'drafts_sha256': None, 'checked_at': None},
            'write': {'created': 0, 'updated': 0, 'suspended': 0, 'errors': []}, 'tools': {'cards': VERSION}}
    write_json(build.state, data, 'cards state')
    _write(builds/'.current', build.root.name+'\n')
    return Result(lines=[f'{build_id} · P0'], files=[build.state])

def next_phase(data):
    phase = data['phase']
    if phase == 'done':
        return phase
    if data['history'] and data['history'][-1]['phase'] == phase and data['history'][-1]['status'] == 'done':
        return PHASES[PHASES.index(phase)+1]
    return phase

def record_write(build, data):
    """Record observed write counts from write/receipts.json; refuses on any failed batch or suspend."""
    path = build.path('write/receipts.json')
    if not path.exists():
        raise CardsError('E12', f'{path}: line 1 field receipts missing', 'finish the Anki writes first')
    r = read_json(path)
    failed = sum(int(b.get('failed', 0)) for b in r.get('batches', [])) + sum(1 for b in r.get('batches', []) if b.get('status') != 'success')
    suspend = r.get('suspend') or {}
    if failed or (suspend and suspend.get('status') != 'success'):
        raise CardsError('E12', f'{path}: line 1 field write receipts report a failure', 'resolve the failed batch before recording')
    rnd = data['review'].get('round', 0)
    from .review.apply import report_path
    reports = [report_path(build, f'review/round{rnd}', who) for who in ('maintainer', 'student')]
    data['write'] = {**data.get('write', {}), 'created': sum(int(b.get('created', 0)) for b in r.get('batches', [])),
                     'updated': len(r.get('updates', [])), 'skipped_duplicate': sum(int(b.get('skipped_duplicate', 0)) for b in r.get('batches', [])), 'suspended': int(suspend.get('notes', 0)), 'errors': [], 'status': 'done'}
    data['review']['independent'] = bool(rnd) and all(p.exists() for p in reports)
    write_json(build.state, data, 'cards state')
    return Result(lines=[f'{data["build_id"]} · write recorded: created {data["write"]["created"]} · updated {data["write"]["updated"]} · suspended {data["write"]["suspended"]}'], files=[build.state])


def run(args):
    if args.action == 'init':
        return init(args)
    build = Build(args.build)
    data = load(build)
    if args.action == 'get':
        return Result(lines=[f'{data["build_id"]} · {data["phase"]}',
                             f'round {data["review"].get("round", 0)} · gate {data["gate"]["status"]}',
                             f'created {data["write"].get("created", 0)} · updated {data["write"].get("updated", 0)} · suspended {data["write"].get("suspended", 0)}'])
    if args.action == 'next':
        phase = next_phase(data)
        if phase == 'done':
            return Result(lines=['done · build complete'])
        title, entry, command, filename = PHASE_INFO[int(phase[1])]
        lines=[f'{phase} {title}', f'Entry: {entry}', f'{command} --build {build.root}']
        if filename:
            lines.append(f'Load phases/{filename} from the installed ankiv2 skill')
        else:
            lines.append('Read the phase map in the installed ankiv2 SKILL.md')
        return Result(lines=lines)
    if args.action == 'record-write':
        return record_write(build, data)
    if data['phase'] == 'done':
        invalid(build, 'phase: transition after done', 'use state init to resume the source')
    if args.action == 'set':
        updates = {}
        for assignment in args.assignments:
            key, sep, raw = assignment.partition('=')
            if not sep or not key.startswith('facts.') or key[6:] not in FACTS:
                invalid(build, key, 'set only documented facts.* keys')
            fact = key[6:]
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw
            if type(value) is not FACTS[fact] or (fact == 'existing_note_count' and value < 0):
                invalid(build, key, f'supply a {FACTS[fact].__name__} value')
            updates[fact] = value
        if any(data['facts'].get(key) != value for key, value in updates.items()):
            data['facts'].update(updates)
            write_json(build.state, data, 'cards state')
    elif args.action == 'phase':
        current, target = data['phase'], args.phase
        allowed = target == current or PHASES.index(target) == PHASES.index(current)+1 or (current, target) in {('P4', 'P3'), ('P5', 'P4')}
        if not allowed or (target == 'P6' and data['gate']['status'] != 'passed'):
            invalid(build, f'phase: illegal transition {current} → {target}', 'complete the preceding phase; P6 requires a passed gate')
        last = data['history'][-1] if data['history'] else {}
        if target != current and (last.get('phase') != current or last.get('status') != 'done'):
            invalid(build, 'phase: transition before completion', 'mark the current phase done first')
        if last.get('phase') != target or last.get('status') != args.status:
            if args.status == 'done' and (last.get('phase') != target or last.get('status') != 'start'):
                invalid(build, 'history: phase not started', 'start the phase before marking it done')
            stamp = now()
            data['phase'] = target
            data['history'].append({'phase': target, 'status': args.status,
                                    'started_at': last['started_at'] if args.status == 'done' else stamp,
                                    'ended_at': stamp if args.status == 'done' else None})
            write_json(build.state, data, 'cards state')
    return Result(lines=[f'{data["build_id"]} · {data["phase"]}'], files=[build.state])
