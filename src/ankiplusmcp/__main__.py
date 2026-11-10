"""Entry point: serve the MCP over stdio (default), or run doctor/setup. No global configuration writes."""
import argparse
import importlib.metadata
import logging
import os
from pathlib import Path
import sys
from . import settings

COMMANDS = ('serve', 'doctor', 'setup')


def serve(argv):
    from .service import Service
    from .server import create_server
    parser=argparse.ArgumentParser(prog='ankiplusmcp serve',description='AnkiPlus mechanical helper MCP (stdio). Configure the official Anki MCP separately in the host.')
    parser.add_argument('--workspace-root',default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or str(settings.default_workspace_root()))
    parser.add_argument('--source-root',action='append',default=None,help='Allowed readable source directory; repeat for multiple roots. Otherwise ANKIPLUS_SOURCE_ROOTS, then folders the client offers, then a safe working directory.')
    parser.add_argument('--profile',default=None,help='Built-in profile: '+', '.join(sorted(settings.PROFILES))+'. Overrides the config file.')
    parser.add_argument('--config',default=None,help='Config TOML with profile, note_type, tag_root. Defaults to ANKIPLUS_CONFIG, then the per-user config directory.')
    args=parser.parse_args(argv)
    try: profile=settings.load_profile(args.profile,Path(args.config) if args.config else None,os.environ)
    except ValueError as exc: parser.error(str(exc))
    logging.basicConfig(level=logging.WARNING)
    service=Service(args.workspace_root,None,profile)
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
    from . import doctor
    return doctor.doctor_main(argv) if command=='doctor' else doctor.setup_main(argv)


if __name__=='__main__': sys.exit(main())
