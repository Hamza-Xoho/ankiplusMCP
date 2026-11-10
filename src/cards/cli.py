"""Argument parsing and dispatch only."""
import argparse
import sys
from . import state, meter, extract, source, target, check, render, figures
from .review import packets, apply
from . import gate, report
from . import build
from .write import plan
from .common.dispatch import execute
from .common.errors import CardsError
from .common.paths import Build

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CardsError('E10', f'arguments: line 1 field {message}', 'see cards state --help')

def parser():
    root = Parser(prog='cards', allow_abbrev=False)
    commands = root.add_subparsers(dest='command', required=True)
    s = commands.add_parser('state', help='build state and resume', allow_abbrev=False)
    actions = s.add_subparsers(dest='action', required=True)
    p = actions.add_parser('init', help='create or resume a build', allow_abbrev=False)
    p.add_argument('source')
    p.add_argument('--job', choices=['build'], default='build')
    for action in ['get', 'set', 'phase', 'next', 'record-write']:
        p = actions.add_parser(action, allow_abbrev=False)
        p.add_argument('--build', required=True)
        if action == 'set':
            p.add_argument('assignments', nargs='+', metavar='key=value')
        if action == 'phase':
            p.add_argument('phase', choices=state.PHASES)
            p.add_argument('status', choices=['start', 'done'])
    p = commands.add_parser('meter', help='measure session usage', allow_abbrev=False)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--session', metavar='ID|PATH')
    source.add_argument('--latest', metavar='PROJECT')
    p.add_argument('--build')
    p.add_argument('--out', required=True)
    p.add_argument('--line', action='store_true')
    p = commands.add_parser('build', help='run the pipeline to the next pause', allow_abbrev=False)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--pdf', metavar='PATH')
    mode.add_argument('--continue', dest='cont', action='store_true')
    mode.add_argument('--resume', action='store_true')
    p.add_argument('--build')
    p = commands.add_parser('extract', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--slides')
    p = commands.add_parser('source', allow_abbrev=False)
    p.add_argument('--build', required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--slides')
    group.add_argument('--all', action='store_true')
    group.add_argument('--grep')
    group.add_argument('--figure')
    group.add_argument('--page-image', type=int)
    p = commands.add_parser('target', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--existing-decks', required=True)
    p.add_argument('--course')
    p.add_argument('--number', type=int)
    p.add_argument('--title')
    p.add_argument('--subject')
    p.add_argument('--system')
    p = commands.add_parser('check', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p = commands.add_parser('render', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--only')
    p.add_argument('--per-sheet', type=int, default=8)
    p.add_argument('--anki-html')
    p = commands.add_parser('figures', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--fig')
    p.add_argument('--summary', action='store_true')
    p.add_argument('--regions')
    p.add_argument('--keep')
    p.add_argument('--mode', choices=['one','all'], default='one')
    p = commands.add_parser('packets', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--round', type=int, choices=[1, 2], required=True)
    p.add_argument('--only')
    p.add_argument('--student-subset', choices=['all', 'half'], default='half')
    p = commands.add_parser('apply', allow_abbrev=False)
    p.add_argument('--build', required=True)
    p.add_argument('--round', type=int, choices=[1, 2], required=True)
    p.add_argument('--decline', action='append', default=[], metavar='ID:REASON')
    for name in ('gate','write','report'):
        p = commands.add_parser(name, allow_abbrev=False)
        p.add_argument('--build', required=True)
    return root

def dispatch(argv):
    args = parser().parse_args(argv)
    return {'state': state.run, 'meter': meter.run, 'build': build.run, 'extract': extract.run, 'source': source.run, 'target': target.run, 'check': check.run, 'render': render.run, 'figures': figures.run, 'packets': packets.run, 'apply': apply.run, 'gate': gate.run, 'write': plan.run, 'report': report.run}[args.command](args)

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    return execute(lambda: dispatch(argv), build=build_from_args(argv), args=argv[1:], cmd='cards '+(argv[0] if argv else 'state'))

def build_from_args(argv):
    for index, arg in enumerate(argv):
        if arg == '--build' and index+1 < len(argv):
            return Build(argv[index+1])
        if arg.startswith('--build='):
            return Build(arg.partition('=')[2])
    return None
