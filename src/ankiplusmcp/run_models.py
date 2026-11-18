"""Versioned history types; source workspaces and individual runs are distinct."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from .models import Identifier, Model, Positive


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SourceSelection(Model):
    source_hash: Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')] | None = None
    source_version: str | None = None
    pages: list[Positive] = Field(default_factory=list)
    label: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def canonical_pages(self):
        self.pages = sorted(set(self.pages))
        return self


class RunEvent(Model):
    schema_version: Literal[1] = 1
    id: Identifier = Field(default_factory=lambda: uuid4().hex)
    timestamp: str = Field(default_factory=utc_now)
    kind: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_identity_lists(self):
        for key in ('note_ids', 'card_ids'):
            if key in self.payload:
                values = self.payload[key]
                if not isinstance(values, list) or any(type(value) is not int or value < 1 for value in values):
                    raise ValueError(f'{key} must be a list of positive integer identities')
        return self


class EventRecord(RunEvent):
    sequence: Positive


class RunSnapshot(Model):
    id: Identifier
    workspace: Identifier
    selection: SourceSelection
    config_version: Positive | None
    events: list[EventRecord]


Run = RunSnapshot


class RunProjection(Model):
    snapshot: RunSnapshot
    token: str


class RunCatalog(Model):
    changed: list[RunProjection]
    unchanged_ids: list[str]
    errors: dict[str, str]
