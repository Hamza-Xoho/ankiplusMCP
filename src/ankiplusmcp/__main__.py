"""Run ankiplusmcp over stdio; no global configuration writes."""
import argparse
import logging
import os
from pathlib import Path
from .service import Service
from .server import create_server

def main():
    parser=argparse.ArgumentParser(description='AnkiPlus mechanical helper MCP (stdio). Configure the official Anki MCP separately in the host.')
    parser.add_argument('--workspace-root',default=os.environ.get('ANKIPLUS_WORKSPACE_ROOT',str(Path.cwd()/'workspaces')))
    parser.add_argument('--source-root',action='append',default=None,help='Allowed readable source directory; repeat for multiple roots. Defaults to cwd.')
    args=parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    service=Service(args.workspace_root,args.source_root or [str(Path.cwd())])
    try: create_server(service).run(transport='stdio')
    finally: service.close()

if __name__=='__main__': main()
