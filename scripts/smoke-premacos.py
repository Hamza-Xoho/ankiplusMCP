#!/usr/bin/env python3
"""Local synthetic rehearsal only: no host registration or Anki connection."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def wait(service, workspace, job):
    for _ in range(1200):
        state=service.jobs.get(workspace,job['id'])
        if state['status'] not in ('queued','running'):
            if state['status']!='completed': raise RuntimeError(str(state.get('error',state)))
            return state['result']
        time.sleep(.05)
    raise RuntimeError('Job timed out')


def run_scenarios(data_root: Path) -> dict[str,dict]:
    import pymupdf
    from PIL import Image,ImageDraw,ImageFont
    from ankiplusmcp.service import Service
    from ankiplusmcp.evidence import EvidenceResolver,EvidenceRef
    from ankiplusmcp.coverage import CoverageStore,CollectionSnapshot,ExistingNote,CoverageDecision
    from ankiplusmcp.configuration import ConfigStore
    from ankiplusmcp.runs import RunStore
    from ankiplusmcp.run_models import SourceSelection
    from ankiplusmcp.run_index import RunIndex,RunQuery
    from ankiplusmcp.store import digest
    outcomes={}
    def scenario(name,operation):
        try: operation(); outcomes[name]={'status':'passed'}
        except Exception as exc: outcomes[name]={'status':'failed','error':str(exc)}
    data_root.mkdir(parents=True,exist_ok=True)
    source=data_root/'Chapters — كتاب.pdf'
    with pymupdf.open() as doc:
        for text in ('Fibroblast has basophilic cytoplasm and an oval nucleus.','Collagen fibres provide structural support.'):
            doc.new_page().insert_text((50,50),text)
        doc.set_page_labels([{'startpage':0,'prefix':'','style':'r','firstpagenum':7}]);doc.save(source)
    s=Service(data_root/'data',[data_root]); shared={}
    try:
        w=s.store.create('lecture',source_path=str(source))['id'];shared['w']=w
        sha=s.store.get(w)['source']['sha256'];copy=Path(s.store.get(w)['source']['path'])
        def chapters():
            wait(s,w,s.extract_source(w,'1'))
            citation=EvidenceResolver(s.source_catalog).resolve(w,[EvidenceRef(source_hash=sha,page=1,quote='basophilic cytoplasm')])[0]
            s.store.write_json(w,'retained-citation.json',citation.model_dump())
            shared['citation']=citation
            wait(s,w,s.extract_source(w,'2'))
            assert digest(copy)==sha and digest(source)==sha
        scenario('chapter_resume',chapters)
        def drafts():
            s.save_cards(w,[{'id':'draft','fields':{'Text':'{{c1::Fibroblast}}'},'source_ref':[1]}],0)
            s.patch_cards(w,[{'id':'draft','changes':{'fields':{'Text':'{{c1::Fibroblast}} has basophilic cytoplasm.'}}}],1)
            revision=s.store.get(w)['revision']; rendered=wait(s,w,s.render_cards(w))
            assert rendered['sheets'] and s.store.get(w)['revision']==revision
        scenario('draft_render',drafts)
        def coverage():
            runs=RunStore(data_root/'data');config=ConfigStore(data_root/'data')
            run=runs.start(w,SourceSelection(source_hash=sha,pages=[1],label='Synthetic cells'),1)
            coverage=CoverageStore(runs,config,EvidenceResolver(s.source_catalog))
            snapshot=CollectionSnapshot(collection_id='synthetic-only',query='fibroblast',notes=[ExistingNote(note_id=101,card_ids=[201])])
            decision=CoverageDecision(concept_id='fibroblast',disposition='already_covered',candidate_note_ids=[101],chosen_note_ids=[101],card_ids=[201],source_refs=[EvidenceRef(source_hash=sha,page=1,quote='basophilic cytoplasm')])
            saved=coverage.record(run.id,snapshot,[decision],batch_id='rehearsal')
            index=RunIndex(runs);assert index.search(RunQuery(note_id=101)).runs
            old={p:p.read_bytes() for p in (runs.directory/run.id).glob('*.json')}
            index.path.unlink(); s.close()
            reopened=Service(data_root/'data',[data_root])
            try:
                citation=shared['citation']
                assert EvidenceResolver(reopened.source_catalog).resolve(w,[EvidenceRef(source_hash=sha,page=1,quote=citation.quote,extraction=citation.extraction)])[0]==citation
                assert reopened.image_bytes(w,reopened.get_page_image(w,1)['artifact']).startswith(b'\x89PNG')
                rebuilt=RunStore(data_root/'data');assert RunIndex(rebuilt).rebuild()==1
                assert RunIndex(rebuilt).search(RunQuery(card_id=201)).runs[0].id==run.id
                assert CoverageStore(rebuilt,config,EvidenceResolver(reopened.source_catalog)).latest(run.id)==saved
                assert all(p.read_bytes()==content for p,content in old.items()) and digest(copy)==sha
            finally:reopened.close()
        scenario('coverage_history',coverage)
        def ocr():
            image=data_root/'FIBROBLAST.png'; im=Image.new('RGB',(800,160),'white')
            ImageDraw.Draw(im).text((20,30),'FIBROBLAST',font=ImageFont.load_default(size=48),fill='black');im.save(image)
            worker=Service(data_root/'ocr',[data_root])
            try:
                workspace=worker.store.create('cards')['id']; artifact=worker.import_image(workspace,str(image))['artifact']
                result=wait(worker,workspace,worker.ocr_image(workspace,artifact));assert result['region_count']>0
            finally:worker.close()
        scenario('real_ocr',ocr)
        def stdio():
            env={**os.environ,'TMPDIR':str(data_root)}
            result=subprocess.run([sys.executable,str(ROOT/'scripts/smoke-mcp.py'),'--command',sys.executable,'-m','ankiplusmcp','--workspace-root',str(data_root/'stdio'),'--source-root',str(data_root)],env=env,text=True,capture_output=True,timeout=120)
            if result.returncode: raise RuntimeError(result.stderr or result.stdout)
        scenario('stdio',stdio)
    finally:s.close()
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args(argv)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    try: stream=args.output.open('x')
    except OSError as exc: print(str(exc),file=sys.stderr);return 2
    with stream:
        with tempfile.TemporaryDirectory(prefix='Study notes — اختبار ') as temporary:
            try: scenarios=run_scenarios(Path(temporary))
            except Exception as exc: scenarios={name:{'status':'failed','error':str(exc)} for name in ('chapter_resume','draft_render','coverage_history','real_ocr','stdio')}
        def command(*args):
            try:return subprocess.check_output(args,cwd=ROOT,stderr=subprocess.STDOUT,text=True).strip()
            except (OSError,subprocess.CalledProcessError):return 'unavailable'
        expected={'chapter_resume','draft_render','coverage_history','real_ocr','stdio'}
        passed=set(scenarios)==expected and all(v['status']=='passed' for v in scenarios.values())
        report={'schema_version':1,'revision':command('git','rev-parse','HEAD'),'dirty':bool(command('git','status','--porcelain')),
            'platform':platform.platform(),'python':platform.python_version(),
            'tool_versions':{name:importlib.metadata.version(name) for name in ('pymupdf','pillow','playwright')},
            'tesseract':command('tesseract','--version'),'node':command('node','--version'),
            'scenarios':scenarios,'performed_anki_operations':0,'status':'local_refactor_verified' if passed else 'failed',
            **{key:'not_run' for key in ('desktop_compatibility','independent_reviewers','companion_write_recovery','onboarding_integration','private_quality_acceptance')}}
        json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
