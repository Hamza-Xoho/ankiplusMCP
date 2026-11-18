"""Disposable synthetic coverage journal measurement; no collection connection."""
import argparse
import json
import platform
import subprocess
import tempfile
import time
from pathlib import Path
from ankiplusmcp.configuration import ConfigStore
from ankiplusmcp.coverage import CoverageStore,CollectionSnapshot,CoverageDecision,ExistingNote
from ankiplusmcp.evidence import EvidenceResolver
from ankiplusmcp.service import Service
from ankiplusmcp.runs import RunStore
from ankiplusmcp.run_models import SourceSelection
from ankiplusmcp.run_index import RunIndex,RunQuery


def measure(root,concepts,notes):
    s=Service(root,[root])
    try:
        workspace=s.store.create('cards')['id']; runs=RunStore(root)
        run=runs.start(workspace,SourceSelection(label='Synthetic'),1)
        coverage=CoverageStore(runs,ConfigStore(root),EvidenceResolver(s.source_catalog))
        snapshot=CollectionSnapshot(collection_id='synthetic',query='synthetic',notes=[ExistingNote(note_id=i+1,card_ids=[i+1001],fields={'Text':'Synthetic note '+str(i)}) for i in range(notes)])
        reads=[]; original=runs._records
        def read(path): reads.append(1); return original(path)
        runs._records=read
        decisions=[CoverageDecision(concept_id=f'concept{i}',disposition='propose_create') for i in range(concepts)]
        begin=time.perf_counter(); saved=coverage.record(run.id,snapshot,decisions);elapsed=time.perf_counter()-begin
        assert saved==decisions
        files=sorted((runs.directory/run.id).glob('[0-9]'*20+'.json'))
        journal_bytes=sum(p.stat().st_size for p in files)
        # Count exact serialized snapshot byte ranges inside the actual compact event files.
        copies=[]
        for p in files:
            event=json.loads(p.read_bytes()); payload=event['payload']
            if 'collection_snapshot' in payload:
                encoded=json.dumps(payload['collection_snapshot'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                assert encoded in p.read_bytes();copies.append(len(encoded))
        repeated=sum(copies)-max(copies,default=0)
        before=len(reads);begin=time.perf_counter(); RunIndex(runs).search(RunQuery());search=time.perf_counter()-begin
        assert coverage.latest(run.id)==saved
        return dict(concepts=concepts,notes=notes,journal_bytes=journal_bytes,repeated_snapshot_bytes=repeated,repeated_fraction=repeated/journal_bytes,event_count=len(files)-1,snapshot_copies=len(copies),history_reads_write=before,history_reads_search=len(reads)-before-1,write_seconds=elapsed,search_seconds=search)
    finally:s.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coverage-benchmark-') as temporary:
        cases=[measure(Path(temporary)/f'{n}-{m}',n,m) for n in (1,10,100) for m in (0,20,500)]
    result=dict(python=platform.python_version(),platform=platform.platform(),revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=cases)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as output:json.dump(result,output,indent=2)
    print(json.dumps(cases[-3:],indent=2))

if __name__=='__main__':main()
