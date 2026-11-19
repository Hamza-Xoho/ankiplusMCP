"""Entry point: serve the MCP over stdio (default), or run doctor/setup. No global configuration writes."""
import argparse
import importlib.metadata
import logging
import os
from pathlib import Path
import sys
from . import settings

COMMANDS = ('serve', 'doctor', 'setup', 'history')


def serve(argv):
    from .service import Service
    from .server import create_server
    parser=argparse.ArgumentParser(prog='ankiplusmcp serve',description='AnkiPlus mechanical helper MCP (stdio). Configure the official Anki MCP separately in the host.')
    parser.add_argument('--workspace-root',default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or str(settings.default_workspace_root()))
    parser.add_argument('--source-root',action='append',default=None,help='Allowed readable source directory; repeat for multiple roots. Otherwise ANKIPLUS_SOURCE_ROOTS, then folders the client offers, then a safe working directory.')
    parser.add_argument('--profile',default=None,help='Built-in profile: '+', '.join(sorted(settings.PROFILES))+'. Overrides the config file.')
    parser.add_argument('--config',default=None,help='Config TOML with profile, note_type, tag_root, browser. Defaults to ANKIPLUS_CONFIG, then the per-user config directory.')
    parser.add_argument('--browser',default=None,help='Browser for card previews: auto (default), chromium, chrome, or the absolute path of a browser program. Overrides the config file.')
    parser.add_argument('--companion-url',help='Explicit local companion HTTP endpoint; no automatic connection.')
    parser.add_argument('--anki-profile',help='Intended Anki profile name, distinct from the card style profile.')
    parser.add_argument('--anki-collection-path',help='Intended absolute collection path reported by the companion.')
    parser.add_argument('--companion-token-file',help='Optional private file containing the existing companion bearer key.')
    args=parser.parse_args(argv)
    if args.companion_url and not (args.anki_profile and args.anki_collection_path):
        parser.error('--companion-url requires --anki-profile and --anki-collection-path')
    if not args.companion_url and any((args.anki_profile,args.anki_collection_path,args.companion_token_file)):
        parser.error('Companion options require --companion-url')
    config=Path(args.config) if args.config else None
    try:
        profile=settings.load_profile(args.profile,config,os.environ)
        browser=settings.load_browser(args.browser,config,os.environ)
    except ValueError as exc: parser.error(str(exc))
    logging.basicConfig(level=logging.WARNING)
    service=Service(args.workspace_root,None,profile,browser)
    if args.companion_url:
        from .companion_connection import CompanionConnection
        try:
            service.companion_connection=CompanionConnection(args.companion_url,profile=args.anki_profile,
                collection_path=args.anki_collection_path,token_file=args.companion_token_file)
        except ValueError as exc: parser.error(str(exc))
    configured=settings.configured_source_roots(args.source_root,os.environ)
    if configured: service.store.set_source_roots(*configured)
    try: create_server(service).run(transport='stdio')
    finally: service.close()
    return 0


def main(argv=None):
    """`serve` is the default, so a bare flag list keeps meaning what it always did."""
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['--version']:
        print('ankiplusmcp '+importlib.metadata.version('ankiplusmcp'))
        return 0
    command=argv.pop(0) if argv and argv[0] in COMMANDS else 'serve'
    if command=='serve': return serve(argv)
    if command=='history':
        from .history_cli import history_main
        return history_main(argv)
    from . import doctor
    return doctor.doctor_main(argv) if command=='doctor' else doctor.setup_main(argv)


if __name__=='__main__': sys.exit(main())
