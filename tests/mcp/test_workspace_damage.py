"""Damaged workspaces remain retained without hiding unrelated resumable work."""
import pytest
from ankiplusmcp.store import Store,DomainError


@pytest.mark.parametrize('broken',['[]','{invalid','{"id":"wrong","revision":0,"mode":"cards"}'])
def test_unreadable_workspace_isolated_in_discovery(tmp_path,broken):
    store=Store(tmp_path,[tmp_path]);good=store.create('cards');bad=store.create('cards')
    store.path(bad['id'],'workspace.json').write_text(broken)
    result=store.list()
    assert [w['id'] for w in result['workspaces']]==[good['id']]
    assert result['errors'][0]['id']==bad['id']
    assert store.path(bad['id'],'workspace.json').read_text()==broken
    with pytest.raises(DomainError):store.get(bad['id'])
