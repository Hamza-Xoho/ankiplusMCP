"""Public typed inputs shared by service operations and MCP schemas."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Short = Annotated[str, Field(min_length=1, max_length=200)]
Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$')]
Positive = Annotated[int, Field(strict=True, gt=0)]

class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Media(Model):
    path: Short
    filename: Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$')]

class Card(Model):
    id: Identifier
    fields: dict[Short, Annotated[str, Field(max_length=20000)]] = Field(min_length=1,max_length=30)
    kind: Literal['cloze','basic','io'] = 'cloze'
    notetype: Short = 'ColdRecall Cloze'
    deck: Short = 'Default'
    tags: list[Annotated[str, Field(min_length=1,max_length=200,pattern=r'^\S+$')]] = Field(default_factory=list,max_length=100)
    action: Literal['create','update'] = 'create'
    note_id: Positive | None = None
    card_ids: list[Positive] = Field(default_factory=list,max_length=100)
    tier: Annotated[int,Field(ge=1,le=3)] | None = None
    source_ref: list[Positive] = Field(default_factory=list,max_length=500)
    objective: str | None = Field(default=None,max_length=200)
    group: str | None = Field(default=None,max_length=200)
    media: list[Media] = Field(default_factory=list,max_length=50)
    question: str | None = Field(default=None,max_length=30000)
    answer: str | None = Field(default=None,max_length=30000)
    @model_validator(mode='after')
    def validate_note(self):
        if self.action == 'update' and self.note_id is None: raise ValueError('An update requires an existing note_id from Anki MCP.')
        if ('\n' in self.deck or '\r' in self.deck or '\n' in self.notetype or '\r' in self.notetype): raise ValueError('Deck and notetype must be single-line.')
        if (self.question is None) != (self.answer is None): raise ValueError('Supply both question and answer HTML.')
        return self

class Region(Model):
    left: float = Field(ge=0,le=1)
    top: float = Field(ge=0,le=1)
    width: float = Field(gt=0,le=1)
    height: float = Field(gt=0,le=1)
    text: str = Field(default='',max_length=500)
    group: Positive | None = None
    conf: float | None = Field(default=None,ge=0,le=100)
    @model_validator(mode='after')
    def bounds(self):
        if self.left+self.width > 1.0001 or self.top+self.height > 1.0001: raise ValueError('Region extends outside the image.')
        return self

class Finding(Model):
    card_id: Identifier
    verdict: Literal['pass','fix','reject']
    message: str = Field(default='',max_length=4000)
    rewrite: dict[Short,Annotated[str,Field(max_length=20000)]] | None = Field(default=None,max_length=30)
    source_refs: list[Positive] = Field(default_factory=list,max_length=100)

class ExternalResult(Model):
    operation: Literal['create','update','media','suspend','unsuspend','verify']
    status: Literal['success','failed','ambiguous']
    note_ids: list[Positive] = Field(default_factory=list,max_length=500)
    card_ids: list[Positive] = Field(default_factory=list,max_length=500)
    batch_artifact: str | None = Field(default=None,max_length=200)
    detail: str = Field(default='',max_length=4000)
