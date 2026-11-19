import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from ankiplusmcp.store import DomainError
from test_coordinator import workflow,run
from test_reconciliation import approved


def test_configuration_reads_fail_busy_instead_of_blocking_an_inflight_dispatch(workflow):
    c,s,e,r,d=workflow;p=approved(workflow)
    entered=Event();release=Event();original=e.call_tool
    async def call(name,args):
        if name=='conditional_student_operation':
            entered.set();await asyncio.to_thread(release.wait,10)
        return await original(name,args)
    e.call_tool=call
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(run,c.apply(r.id,p.digest))
        try:
            assert entered.wait(3)
            with pytest.raises(DomainError,match='BUSY'):c.config.read()
        finally:release.set()
        assert future.result(timeout=10)['counts']['notes_created']==1
