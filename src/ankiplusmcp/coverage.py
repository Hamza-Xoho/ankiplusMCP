"""Inspectably record coverage judgements, without pretending they are verified facts."""
import hashlib
import json
import re
from uuid import uuid4
from typing import Literal

from pydantic import Field, model_validator

from .configuration import ConfigStore
from .evidence import EvidenceRef, EvidenceResolver
from .models import Identifier, Model, Positive, Short
from .run_models import RunEvent, utc_now
from .runs import RunStore
from .store import DomainError


class ExistingNote(Model):
    note_id: Positive
    card_ids: list[Positive] = Field(default_factory=list, max_length=500)
    suspended_card_ids: list[Positive] = Field(default_factory=list, max_length=500)
    fields: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def card_identity(self):
        if len(set(self.card_ids)) != len(self.card_ids) or not set(self.suspended_card_ids) <= set(self.card_ids):
            raise ValueError('Suspended cards must belong to the note, and card identities must be unique.')
        return self


class CollectionSnapshot(Model):
    collection_id: Short
    query: str = Field(min_length=1, max_length=2000)
    observed_at: str = Field(default_factory=utc_now)
    notes: list[ExistingNote] = Field(default_factory=list, max_length=500)

    @model_validator(mode='after')
    def unique_identities(self):
        notes = [note.note_id for note in self.notes]
        cards = [card for note in self.notes for card in note.card_ids]
        if len(set(notes)) != len(notes) or len(set(cards)) != len(cards):
            raise ValueError('Collection snapshot contains duplicate note/card ownership.')
        return self


class CoverageDecision(Model):
    concept_id: Identifier
    draft_id: Identifier | None = None
    disposition: Literal['already_covered', 'propose_unsuspend', 'propose_create', 'explicit_update', 'pending']
    candidate_note_ids: list[Positive] = Field(default_factory=list, max_length=500)
    chosen_note_ids: list[Positive] = Field(default_factory=list, max_length=500)
    card_ids: list[Positive] = Field(default_factory=list, max_length=500)
    source_refs: list[EvidenceRef] = Field(default_factory=list, max_length=20)
    uncertain: bool = False
    source_disagreement: bool = False


class CoverageStore:
    def __init__(self, runs: RunStore, config: ConfigStore, evidence: EvidenceResolver):
        self.runs, self.config, self.evidence = runs, config, evidence

    def record(self, run_id: str, snapshot: CollectionSnapshot, decisions: list[CoverageDecision], *, batch_id: str | None = None) -> list[CoverageDecision]:
        batch_id=uuid4().hex if batch_id is None else batch_id
        if not isinstance(batch_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',batch_id):
            raise DomainError('COVERAGE','Invalid coverage batch identifier.')
        snapshot=CollectionSnapshot.model_validate(snapshot)
        supplied=[CoverageDecision.model_validate(d).model_copy(deep=True) for d in decisions]
        if not 1<=len(supplied)<=100: raise DomainError('LIMIT','Record between 1 and 100 coverage decisions.')
        request={'run_id':run_id,'snapshot':snapshot.model_dump(),'decisions':[d.model_dump() for d in supplied]}
        request_digest=hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        event_id='coverage-'+batch_id
        def existing(run):
            for event in run.events:
                if event.id==event_id:
                    if event.kind!='coverage_batch' or event.payload.get('request_digest')!=request_digest:
                        raise DomainError('CONFLICT','Coverage batch identifier was reused with changed input.')
                    return [CoverageDecision.model_validate({k:v for k,v in d.items() if k in CoverageDecision.model_fields}) for d in event.payload['decisions']]
            return None
        run = self.runs.read(run_id)
        previous=existing(run)
        if previous is not None: return previous
        if run.config_version is None:
            raise DomainError('CONFIG', 'Historical run has unknown preferences; start a configured run before making new decisions.')
        # The initial run version is history; explicitly saved preferences govern
        # later decisions, while each event retains the version actually used.
        config = self.config.read()
        snapshot = CollectionSnapshot.model_validate(snapshot)
        parsed = supplied
        if not 1 <= len(parsed) <= 100:
            raise DomainError('LIMIT', 'Record between 1 and 100 coverage decisions.')
        if len({decision.concept_id for decision in parsed}) != len(parsed):
            raise DomainError('COVERAGE', 'Resolve repeated concept identifiers before recording a batch.')
        notes = {note.note_id: note for note in snapshot.notes}
        records = []
        for decision in parsed:
            if not set(decision.candidate_note_ids + decision.chosen_note_ids) <= set(notes):
                raise DomainError('COVERAGE', 'Decision names a note absent from the supplied collection snapshot.')
            if not set(decision.chosen_note_ids) <= set(decision.candidate_note_ids):
                raise DomainError('COVERAGE', 'Chosen notes must be among the recorded candidates.')
            owned = {card for note_id in decision.chosen_note_ids for card in notes[note_id].card_ids}
            if not set(decision.card_ids) <= owned:
                raise DomainError('COVERAGE', 'Selected card does not belong to the chosen note IDs.')
            if run.selection.source_hash is not None:
                if not decision.source_refs:
                    raise DomainError('SOURCE_REF', 'Source-based coverage requires a supporting page or passage.')
                if any(ref.source_hash != run.selection.source_hash or
                       (run.selection.pages and ref.page not in run.selection.pages) for ref in decision.source_refs):
                    raise DomainError('SOURCE_REF', 'Coverage falls outside the selected source version or chapter.')
            evidence = self.evidence.resolve(run.workspace, decision.source_refs) if decision.source_refs else []
            if decision.source_disagreement:
                decision.disposition = 'pending'
            elif decision.uncertain:
                if config.review_mode == 'manual' or config.uncertain_match == 'pending':
                    decision.disposition = 'pending'
                elif config.uncertain_match == 'create':
                    decision.disposition = 'propose_create'
                    decision.chosen_note_ids, decision.card_ids = [], []
                elif decision.chosen_note_ids:
                    decision.disposition = 'propose_unsuspend' if decision.card_ids else 'pending'
                else:
                    decision.disposition = 'pending'
            if decision.disposition in ('already_covered', 'propose_unsuspend', 'explicit_update') and not decision.chosen_note_ids:
                raise DomainError('COVERAGE', 'Reusing a card requires a selected existing note.')
            if decision.disposition == 'propose_create' and (decision.chosen_note_ids or decision.card_ids):
                raise DomainError('COVERAGE', 'A new-card proposal cannot also mutate existing cards.')
            if decision.disposition == 'propose_unsuspend':
                suspended = {card for note_id in decision.chosen_note_ids for card in notes[note_id].suspended_card_ids}
                selected = list(decision.card_ids)
                if not selected:
                    decision.disposition = 'pending'
                elif set(selected).isdisjoint(suspended):
                    decision.disposition = 'already_covered'
                else:
                    decision.card_ids = [card for card in selected if card in suspended]
            if decision.disposition == 'already_covered':
                suspended = {card for note_id in decision.chosen_note_ids for card in notes[note_id].suspended_card_ids}
                if not decision.card_ids or not set(decision.card_ids).isdisjoint(suspended):
                    decision.disposition = 'pending'
            records.append(RunEvent(kind='coverage_decision', payload={
                **decision.model_dump(), 'note_ids': decision.chosen_note_ids,
                'config_version': config.config_version,
                'collection_snapshot': snapshot.model_dump(), 'source_evidence': [item.model_dump() for item in evidence],
                'evidence_origin': 'caller_supplied', 'independently_verified': False}))
        payload={'payload_version':1,'batch_id':batch_id,'request_digest':request_digest,
            'collection_snapshot':snapshot.model_dump(),'config_version':config.config_version,
            'decisions':[{**d.model_dump(),'source_evidence':event.payload['source_evidence']} for d,event in zip(parsed,records)],
            'note_ids':sorted({i for d in parsed for i in d.chosen_note_ids}),
            'card_ids':sorted({i for d in parsed for i in d.card_ids}),
            'evidence_origin':'caller_supplied','independently_verified':False}
        try:
            self.runs.append(run_id,RunEvent(id=event_id,kind='coverage_batch',payload=payload))
        except DomainError as exc:
            if exc.code!='CONFLICT': raise
            winner=existing(self.runs.read(run_id))
            if winner is None: raise
            return winner
        return parsed

    def latest(self, run_id: str) -> list[CoverageDecision]:
        decisions = {}
        fields = set(CoverageDecision.model_fields)
        for event in self.runs.read(run_id).events:
            payloads=event.payload.get('decisions',[]) if event.kind=='coverage_batch' else [event.payload] if event.kind=='coverage_decision' else []
            for payload in payloads:
                decision = CoverageDecision.model_validate({key: value for key, value in payload.items() if key in fields})
                decisions[decision.concept_id] = decision
        return list(decisions.values())
