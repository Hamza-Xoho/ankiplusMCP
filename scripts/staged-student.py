#!/usr/bin/env python3
"""Prepare/release the disposable two-card student experiment; never launch a reviewer."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from filelock import FileLock
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TILES = ['n001_c1', 'n002_c1']
TEMPLATES = ROOT / 'src/cards/templates/review/student'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def read(path):
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlinks are not allowed in experiment evidence')
    return path.read_bytes()


def durable(path, data):
    """Exclusive immutable publication; identical replay repairs interrupted release."""
    if path.exists() or path.is_symlink():
        if read(path) != data:
            raise ValueError('Committed experiment evidence changed')
        return
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


PROTOCOL = '''# Disposable staged student protocol

This supplemental exposure protocol overrides only the simultaneous-image step
and output destination of the preserved student agent, brief and shared prompt.
The rubric, report format, model Sonnet 5.5, effort medium and TOTAL maxTurns 6
remain unchanged. No maintainer run, Anki tools, prior reports, author history,
source text or answer key are permitted. This seeded fixture is diagnostic.

Stage 1: read PROMPT.md, this protocol, brief.md, rubric.md, report-format.md and
fronts.json. Inspect fronts.png once. Write front-attempts.json as an object with
exactly n001_c1 and n002_c1 as keys and an answer or "don't know" for each.
Stop for supervised release. Do not read any other directory or back data.

Stage 2 requires verified SAME-reviewer continuation on the LOCAL Mac host.
Only after the supervisor validates, hashes and durably commits the answers does
it release backs.png and backs.json. Read that image once, compare with the
committed answers and write student_report.md in the unchanged report format.
Never rewrite attempts. Do not reopen fronts. The six-turn budget is cumulative.

A supervisor must inspect the actual tool read/write order and per-request
model/effort evidence. Files alone cannot prove what a model saw. No execution or
blind recall pass is established by preparing or releasing these files.
'''


def prepare(source, output):
    source, output = Path(source).absolute(), Path(output).absolute()
    manifest = json.loads(read(source / 'sheets.json'))
    sheets = manifest['sheets']
    if len(sheets) != 1 or sheets[0]['notes'] != ['n001', 'n002'] or manifest.get('previews'):
        raise ValueError('Only the original two-card, single-sheet synthetic fixture is supported')
    images = {}
    for side in ('fronts', 'backs'):
        relative = Path(sheets[0][side])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Image must be inside the source packet')
        path = source / relative
        data = read(path)
        with Image.open(path) as image:
            if image.format != 'PNG':
                raise ValueError('PNG required')
            image.verify()
        images[side] = data
    templates = {}
    for name in ('brief.md', 'rubric.md', 'report-format.md'):
        templates[name] = read(source / name)
        if templates[name] != read(TEMPLATES / name):
            raise ValueError('Student templates differ from the preserved originals')
    output.mkdir(parents=True, exist_ok=False)
    packet, supervisor = output / 'packet', output / 'supervisor'
    packet.mkdir()
    supervisor.mkdir(mode=0o700)
    for name, data in templates.items():
        durable(packet / name, data)
    durable(packet / 'fronts.png', images['fronts'])
    durable(supervisor / 'withheld.png', images['backs'])
    durable(packet / 'fronts.json', encoded({'tile_ids': TILES, 'image': 'fronts.png'}))
    durable(packet / 'STAGED-PROTOCOL.md', PROTOCOL.encode())
    durable(packet / 'PROMPT.md', b'Use compat-staged-student. Read STAGED-PROTOCOL.md first. Stage 1 exposes only fronts; commit every answer before supervised continuation. Final report: student_report.md.\n')
    # Only a disposable alias is changed. Production/frozen agent bytes remain untouched.
    original = read(ROOT / '.claude/agents/anki-student.md').decode()
    header, body = original.split('---', 2)[1:]
    header = header.replace('name: anki-student', 'name: compat-staged-student')
    alias = ('---' + header + '---' + body + '\nSUPPLEMENTAL OVERRIDE: Follow STAGED-PROTOCOL.md for staged image release, the attempts file, and the final report destination. All other instructions remain.\n')
    durable(supervisor / 'compat-staged-student.md', alias.encode())
    result = {'schema_version': 1, 'packet': str(packet), 'tile_ids': TILES,
              'reviewer_execution': 'not_run', 'continuation_support': 'not_verified',
              'front_sha256': sha(images['fronts']), 'back_sha256': sha(images['backs']),
              'original_agent_sha256': sha(original.encode()),
              'template_sha256': {name: sha(data) for name, data in templates.items()}}
    durable(supervisor / 'preparation.json', encoded(result))
    return result


def release(experiment):
    experiment = Path(experiment).absolute()
    packet, supervisor = experiment / 'packet', experiment / 'supervisor'
    # Check parent boundaries before acquiring a writable lock.
    for path in (packet, supervisor, supervisor / '.release.lock'):
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError('Symlink experiment boundary')
    with FileLock(supervisor / '.release.lock', timeout=5):
        prepared = json.loads(read(supervisor / 'preparation.json'))
        front = read(packet / 'fronts.png')
        back = read(supervisor / 'withheld.png')
        if sha(front) != prepared['front_sha256'] or sha(back) != prepared['back_sha256']:
            raise ValueError('Experiment image bytes changed')
        for name, digest in prepared['template_sha256'].items():
            if sha(read(packet / name)) != digest:
                raise ValueError('Student template changed')
        raw = read(packet / 'front-attempts.json')
        attempts = json.loads(raw)
        if not isinstance(attempts, dict) or set(attempts) != set(TILES) or any(
            not isinstance(a, str) or not a.strip() or len(a) > 4000 for a in attempts.values()
        ):
            raise ValueError('Commit a complete answer or don\'t know for every front tile')
        # These durable writes happen before any back image enters the packet.
        durable(supervisor / 'committed-attempts.json', raw)
        receipt = {'attempts_sha256': sha(raw), 'front_sha256': sha(front), 'back_sha256': sha(back),
                   'reviewer_execution': 'not_verified', 'ordering_evidence': 'host_trace_required'}
        durable(supervisor / 'release.json', encoded(receipt))
        durable(packet / 'backs.png', back)
        durable(packet / 'backs.json', encoded({'image': 'backs.png', 'attempts_sha256': sha(raw)}))
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    prep = subs.add_parser('prepare')
    prep.add_argument('--source', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    rel = subs.add_parser('release')
    rel.add_argument('--experiment', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output) if args.action == 'prepare' else release(args.experiment), indent=2))


if __name__ == '__main__':
    main()
