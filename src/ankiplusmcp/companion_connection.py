"""Explicit loopback HTTP connection; never discover real Anki automatically."""
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from .anki_adapter import AnkiAdapter
from .store import DomainError


class CompanionConnection:
    def __init__(self, url, *, profile, collection_path, token_file=None):
        try:
            parsed=urlsplit(url)
            valid=(parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')
                and parsed.port not in (None,80,8080) and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment)
        except ValueError: valid=False
        if not valid:
            raise DomainError('CONFIG','Companion requires an explicit loopback HTTP endpoint with an unreserved port.')
        self.url,self.profile,self.collection_path,self.token_file=url,profile,collection_path,token_file

    @asynccontextmanager
    async def __call__(self):
        headers={}
        if self.token_file:
            from pathlib import Path
            try: token=Path(self.token_file).read_text().strip()
            except OSError:
                raise DomainError('CONFIG','Companion credential file is unreadable.') from None
            if not token or '\n' in token or '\r' in token:
                raise DomainError('CONFIG','Companion credential file is invalid.')
            headers['Authorization']='Bearer '+token
        try:
            async with httpx.AsyncClient(headers=headers,follow_redirects=False,trust_env=False,timeout=30) as client:
                async with streamable_http_client(self.url,http_client=client) as (read,write,_):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        yield AnkiAdapter(session,profile=self.profile,collection_path=self.collection_path)
        except DomainError:
            raise
        except Exception:
            raise DomainError('TRANSPORT','Companion connection failed; any sent operation must be reconciled before retry.') from None
