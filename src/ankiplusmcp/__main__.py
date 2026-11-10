"""Run ankiplusmcp over stdio; no global configuration writes."""
import argparse
import logging
import os
from pathlib import Path
from .service import Service
from .server import create_server
from . import settings

def main():
    parser=argparse.ArgumentParser(description='AnkiPlus mechanical helper MCP (stdio). Configure the official Anki MCP separately in the host.')
    parser.add_argument('--workspace-root',default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT') or str(settings.default_workspace_root()))
    parser.add_argument('--source-root',action='append',default=None,help='Allowed readable source directory; repeat for multiple roots. Otherwise ANKIPLUS_SOURCE_ROOTS, then folders the client offers, then a safe working directory.')
    args=parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    service=Service(args.workspace_root,None)
    configured=settings.configured_source_roots(args.source_root,os.environ)
    if configured: service.store.set_source_roots(*configured)
    try: create_server(service).run(transport='stdio')
    finally: service.close()

if __name__=='__main__': main()
