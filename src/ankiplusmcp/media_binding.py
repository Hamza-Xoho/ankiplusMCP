"""Retain exact companion media evidence without changing original sources."""
import base64
import hashlib
import os
from pathlib import Path
import tempfile
from .runs import _sync_directory
from .store import DomainError


def publish_bytes(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes()!=data:raise DomainError('MEDIA','An immutable media evidence file differs; preserve it for recovery.')
        return
    fd,temporary=tempfile.mkstemp(prefix='.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path);_sync_directory(path.parent)
    finally:Path(temporary).unlink(missing_ok=True)


async def bind_media(coordinator,adapter,workspace,state,planned,retained,findings,draft_id):
    """Predict only explicitly staged uploads; retain/read every other local dependency."""
    for name,observed in list(state['media'].items()):
        if name in planned:
            m=planned[name]
            state['media'][name]={'filename':name,'size':m['size'],'sha256':m['sha256']}
            continue
        if observed is None or observed.get('external') is True:
            findings.append({'code':'MEDIA_UNAVAILABLE','card_id':draft_id,'severity':'blocker',
                'message':'A referenced media item is absent or external; resolve it before quality authorization.'})
            continue
        value=await adapter.read_media(name)
        if any(value.get(k)!=observed.get(k) for k in ('filename','size','sha256')):
            raise DomainError('CONFLICT','Referenced media changed while staging; refresh the proposal.')
        data=base64.b64decode(value['data'],validate=True)
        suffix=Path(name).suffix.lower()
        relative='collection-media/'+hashlib.sha256(data).hexdigest()+suffix
        path=coordinator.s.store.path(workspace,relative)
        publish_bytes(path,data)
        m={'path':relative,'sha256':observed['sha256']}
        if name in retained and retained[name]['sha256']!=m['sha256']:
            raise DomainError('MEDIA','Conflicting bytes use one collection media name.')
        retained[name]=m
