"""Explicit local history commands, separate from the card-review interface."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

from . import settings
from .run_index import RunIndex, RunQuery
from .runs import RunStore
from .store import DomainError


def _text(value):
    return ''.join(character if character.isprintable() else ' ' for character in str(value))


def _summary(run):
    return {'id': run.id, 'workspace': run.workspace, 'label': run.selection.label,
            'source_hash': run.selection.source_hash, 'pages': run.selection.pages,
            'created': run.events[0].timestamp, 'updated': run.events[-1].timestamp,
            'config_version': run.config_version, 'event_count': len(run.events)}


def _markdown(run):
    lines = ['# AnkiPlus run', '', f'Run: {_text(run.id)}',
             f'Source: {_text(run.selection.label or run.workspace)}',
             f'Source hash: {run.selection.source_hash or "not available"}',
             f'Initial configuration: {run.config_version or "unknown"}', '',
             'Operation evidence retains its recorded origin; a caller report is not independent verification.', '']
    for event in run.events:
        encoded = json.dumps(event.model_dump(), indent=2, ensure_ascii=False)
        fence = '`' * max(3, max((len(match) + 1 for match in re.findall(r'`+', encoded)), default=3))
        lines.extend([f'## {event.sequence}. {_text(event.kind)}', '', fence + 'json', encoded, fence, ''])
    return '\n'.join(lines)


def history_main(argv):
    parser = argparse.ArgumentParser(prog='ankiplusmcp history', description='Find or export local run history without opening a review screen.')
    parser.add_argument('action', choices=('list', 'show', 'export', 'rebuild', 'import-legacy'))
    parser.add_argument('run_id', nargs='?')
    parser.add_argument('--workspace-root', default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or str(settings.default_workspace_root()))
    parser.add_argument('--source-hash')
    parser.add_argument('--note-id', type=int)
    parser.add_argument('--card-id', type=int)
    parser.add_argument('--stage')
    parser.add_argument('--outcome')
    parser.add_argument('--query')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--output')
    parser.add_argument('--from', dest='legacy_directory')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        store = RunStore(Path(args.workspace_root).expanduser())
        if args.action == 'list':
            result = RunIndex(store).search(RunQuery(source_hash=args.source_hash, note_id=args.note_id, card_id=args.card_id,
                stage=args.stage, outcome=args.outcome, text=args.query, offset=args.offset, limit=args.limit))
            data = {'runs': [_summary(run) for run in result.runs], 'next_offset': result.next_offset, 'errors': result.errors}
            if not args.json:
                for run in data['runs']:
                    print(f"{run['id']}  {_text(run['label'] or run['workspace'])}  {run['updated']}")
                if result.next_offset is not None:
                    print(f'Next offset: {result.next_offset}')
                if result.errors:
                    print('Some run records need recovery: ' + ', '.join(result.errors), file=sys.stderr)
                return 0
        elif args.action == 'rebuild':
            data = {'indexed_runs': RunIndex(store).rebuild()}
        elif args.action == 'import-legacy':
            if not args.run_id or not args.legacy_directory:
                raise DomainError('INPUT', 'Specify the workspace ID and --from DIRECTORY.')
            data = {'runs': [_summary(run) for run in store.import_legacy(args.run_id, Path(args.legacy_directory).expanduser())]}
        else:
            if not args.run_id:
                raise DomainError('INPUT', 'Specify a run ID.')
            run = store.read(args.run_id)
            if args.action == 'show':
                if not args.json:
                    print(_markdown(run))
                    return 0
                data = run.model_dump()
            else:
                if not args.output:
                    raise DomainError('INPUT', 'Choose an output file with --output.')
                output = Path(args.output).expanduser()
                content = run.model_dump_json(indent=2) + '\n' if args.json else _markdown(run)
                with output.open('x', encoding='utf-8') as stream:
                    stream.write(content)
                data = {'output': str(output), 'run_id': run.id}
        print(json.dumps(data, ensure_ascii=False))
        return 0
    except (DomainError, OSError, ValueError) as exc:
        error = {'code': getattr(exc, 'code', 'HISTORY'), 'message': str(exc)}
        print(json.dumps({'error': error}) if args.json else 'History: ' + _text(error['message']))
        return 2
