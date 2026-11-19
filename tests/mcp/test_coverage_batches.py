from concurrent.futures import ThreadPoolExecutor
import pytest
from test_coverage import setup,decision
from ankiplusmcp.store import DomainError
from ankiplusmcp.run_models import RunEvent
from ankiplusmcp.run_index import RunIndex,RunQuery


def test_batch_stores_snapshot_once(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        inputs=[decision(sha,concept_id=f'c{i}') for i in range(100)]
        assert c.record(r.id,snap,inputs,batch_id='hundred')==inputs
        events=c.runs.read(r.id).events
        assert len(events)==2 and events[-1].kind=='coverage_batch'
        assert len(events[-1].payload['decisions'])==100
        assert 'collection_snapshot' not in events[-1].payload['decisions'][0]
        assert c.latest(r.id)==inputs
    finally:s.close()


def test_invalid_batch_records_nothing(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        with pytest.raises(DomainError):c.record(r.id,snap,[decision(sha),decision(sha,concept_id='bad',card_ids=[999])],batch_id='invalid')
        assert len(c.runs.read(r.id).events)==1
    finally:s.close()


def test_mixed_coverage_history(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        old=decision(sha);c.runs.append(r.id,RunEvent(kind='coverage_decision',payload=old.model_dump()))
        new=decision(sha,disposition='pending'); c.record(r.id,snap,[new],batch_id='new')
        assert c.latest(r.id)==[new]
        c.runs.append(r.id,RunEvent(kind='coverage_decision',payload=old.model_dump()))
        assert c.latest(r.id)==[old]
    finally:s.close()


def test_interrupted_batch_retries_once(tmp_path,monkeypatch):
    import ankiplusmcp.runs as module
    s,c,r,snap,sha=setup(tmp_path);original=module.os.replace
    try:
        def fail(src,dst):raise OSError('before rename')
        with monkeypatch.context() as m:
            m.setattr(module.os,'replace',fail)
            with pytest.raises(OSError): c.record(r.id,snap,[decision(sha)],batch_id='retry')
        assert len(c.runs.read(r.id).events)==1
        a=c.record(r.id,snap,[decision(sha)],batch_id='retry')
        assert c.record(r.id,snap,[decision(sha)],batch_id='retry')==a
        assert len(c.runs.read(r.id).events)==2
    finally:s.close()


def test_conflicting_batch_id_is_refused(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        c.record(r.id,snap,[decision(sha)],batch_id='same')
        with pytest.raises(DomainError,match='CONFLICT'):c.record(r.id,snap,[decision(sha,uncertain=True)],batch_id='same')
        assert len(c.runs.read(r.id).events)==2
    finally:s.close()


def test_batch_retry_keeps_original_preferences(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        inputs=[decision(sha,uncertain=True)];first=c.record(r.id,snap,inputs,batch_id='retry1')
        c.config.confirm(c.config.propose({'review_mode':'automatic','uncertain_match':'create'},1).id)
        assert c.record(r.id,snap,inputs,batch_id='retry1')==first
        assert first[0].disposition=='pending'
        events=c.runs.read(r.id).events;assert len(events)==2 and events[-1].payload['config_version']==1
        assert c.record(r.id,snap,inputs,batch_id='next1')[0].disposition=='propose_create'
    finally:s.close()


def test_concurrent_batch_retry_has_one_winner(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(c.record,r.id,snap,[decision(sha)],batch_id='same') for _ in range(2)]
            assert futures[0].result()==futures[1].result()
        assert len(c.runs.read(r.id).events)==2
    finally:s.close()


def test_concurrent_retry_waits_for_same_batch_configuration_read(tmp_path,monkeypatch):
    from threading import Event,Lock
    s,c,r,snap,sha=setup(tmp_path);entered=Event();release=Event();started=Event();guard=Lock();calls=0
    original=c.config.read
    def paused():
        nonlocal calls
        with guard:calls+=1;first=calls==1
        if not first:return original()
        with c.config._lock():
            entered.set();assert release.wait(5)
            return c.config._current()[0]
    monkeypatch.setattr(c.config,'read',paused)
    def retry():started.set();return c.record(r.id,snap,[decision(sha)],batch_id='same')
    try:
        with ThreadPoolExecutor(2) as pool:
            first=pool.submit(c.record,r.id,snap,[decision(sha)],batch_id='same')
            assert entered.wait(2)
            second=pool.submit(retry);assert started.wait(2)
            try:
                with pytest.raises(TimeoutError):second.result(timeout=.2)
            finally:release.set()
            assert first.result(timeout=3)==second.result(timeout=3)
        assert len(c.runs.read(r.id).events)==2 and calls==1
    finally:release.set();s.close()


def test_batch_search_keeps_note_card_units(tmp_path):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        c.record(r.id,snap,[decision(sha)],batch_id='units');index=RunIndex(c.runs)
        assert index.search(RunQuery(note_id=101)).runs and index.search(RunQuery(card_id=202)).runs
        assert not index.search(RunQuery(note_id=202)).runs and not index.search(RunQuery(card_id=101)).runs
        payload=c.runs.read(r.id).events[-1].payload
        assert payload['evidence_origin']=='caller_supplied' and payload['independently_verified'] is False
    finally:s.close()

@pytest.mark.parametrize('batch_id,count',[('',1),('a'*65,1),('../x',1),('ok',0),('ok',101)])
def test_batch_limits(tmp_path,batch_id,count):
    s,c,r,snap,sha=setup(tmp_path)
    try:
        with pytest.raises(DomainError):c.record(r.id,snap,[decision(sha,concept_id=f'c{i}') for i in range(count)],batch_id=batch_id)
        assert len(c.runs.read(r.id).events)==1
    finally:s.close()
