"""Bounded connected responses retain exact permanent evidence via continuation."""
import json
from test_coordinator import workflow,covered,run
from ankiplusmcp.server import API


def test_large_application_summary_has_bounded_pages_and_all_outcomes(workflow):
    c,s,e,r,d=workflow;covered(workflow);p=run(c.stage(r.id));api=API(s)
    for n in range(120):c.event(r.id,'operation_result',{'operation_id':str(n),'operation':'add_note','status':'confirmed','note_ids':[n+1],'card_ids':list(range(100000000000,100000000500))})
    page=api.get_run_results(r.id)
    assert len(json.dumps(page))<40000
    assert page['total']==120 and page['next_offset'] is not None
    rows=[]
    while True:
        rows.extend(page['results'])
        if page['next_offset'] is None:break
        page=api.get_run_results(r.id,offset=page['next_offset'])
    assert len(rows)==120 and len({row['operation_id'] for row in rows})==120


def test_proposal_previews_are_bounded_and_exact_event_is_slice_readable(workflow):
    c,s,e,r,d=workflow
    s.patch_cards(r.workspace,[{'id':'fibroblast','changes':{'fields':{'Back':'x'*20000,'Front':'q'*20000}}}],1)
    covered(workflow);p=run(c.stage(r.id));api=API(s)
    preview=api.get_run_proposal(r.id)
    assert len(json.dumps(preview))<30000
    assert preview['cards'][0]['truncated_fields']
    events=api.get_run_history(r.id)
    sequence=next(row['sequence'] for row in events['events'] if row['kind']=='proposal_staged')
    chunks=[];offset=0
    while True:
        part=api.read_run_record(r.id,sequence,offset)
        chunks.append(part['text']);offset=part['next_offset']
        if offset is None:break
    exact=json.loads(''.join(chunks))
    assert exact['payload']['proposal']['cards'][0]['fields']==p.cards[0]['fields']


def test_review_evidence_previews_do_not_repeat_full_long_quotes(workflow):
    from ankiplusmcp.review_session import ReviewSession
    c,s,e,r,d=workflow
    from test_sources import wait
    quote='Fibroblast collagen '*60
    w=s.store.create('lecture',text='# Cells\n'+quote)['id']
    wait(s,w,s.extract_source(w))
    s.save_cards(w,[s._cards(r.workspace)[0]],0)
    new=c.start(w,[1]);source=s.store.get(w)['source']['sha256']
    d['source_refs']=[{'source_hash':source,'page':1,'quote':quote} for _ in range(20)]
    run(c.coverage(new.id,'collagen',[d]));run(c.stage(new.id));page=run(ReviewSession(c).open(new.id))
    assert len(json.dumps(page))<18000
    assert len(page['items'][0]['source_evidence'])==20
