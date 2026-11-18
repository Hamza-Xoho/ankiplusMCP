import pytest

from ankiplusmcp.configuration import ConfigStore
from ankiplusmcp.evidence import EvidenceRef, EvidenceResolver
from ankiplusmcp.runs import RunStore, SourceSelection
from ankiplusmcp.service import Service
from ankiplusmcp.store import DomainError
from test_sources import wait


def setup(tmp_path, preferences=None):
    from ankiplusmcp.coverage import CoverageStore, CollectionSnapshot, ExistingNote
    service = Service(tmp_path / 'data', [tmp_path])
    workspace = service.store.create('lecture', text='# Cells\nFibroblasts have basophilic cytoplasm.')['id']
    wait(service, workspace, service.extract_source(workspace))
    sha = service.store.get(workspace)['source']['sha256']
    config = ConfigStore(tmp_path / 'data')
    if preferences:
        config.confirm(config.propose(preferences, 1).id)
    runs = RunStore(tmp_path / 'data')
    run = runs.start(workspace, SourceSelection(source_hash=sha, pages=[1]), config.read().config_version)
    coverage = CoverageStore(runs, config, EvidenceResolver(service))
    snapshot = CollectionSnapshot(collection_id='test-collection', query='fibroblast', notes=[
        ExistingNote(note_id=101, card_ids=[201, 202], suspended_card_ids=[202], fields={'Text': 'Fibroblast'}),
        ExistingNote(note_id=102, card_ids=[203], fields={'Text': 'Cell'})])
    return service, coverage, run, snapshot, sha


def decision(sha, **changes):
    from ankiplusmcp.coverage import CoverageDecision
    return CoverageDecision(**{'concept_id': 'fibroblast', 'disposition': 'propose_unsuspend',
                               'candidate_note_ids': [101], 'chosen_note_ids': [101], 'card_ids': [202],
                               'source_refs': [EvidenceRef(source_hash=sha, page=1, quote='basophilic cytoplasm')], **changes})


def test_existing_coverage_and_suspension_are_logged_with_source(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        saved = coverage.record(run.id, snapshot, [decision(sha)])
        assert saved[0].disposition == 'propose_unsuspend'
        latest = coverage.latest(run.id)
        assert latest[0].card_ids == [202]
        events = coverage.runs.read(run.id).events
        assert events[-1].payload['evidence_origin'] == 'caller_supplied'
        assert events[-1].payload['source_evidence'][0]['quote'] == 'basophilic cytoplasm'
        assert events[-1].payload['independently_verified'] is False
    finally:
        s.close()


def test_uncertain_matches_wait_for_user_by_default(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        assert coverage.record(run.id, snapshot, [decision(sha, uncertain=True)])[0].disposition == 'pending'
    finally:
        s.close()


@pytest.mark.parametrize('policy,want', [('pending', 'pending'), ('reuse', 'propose_unsuspend'), ('create', 'propose_create')])
def test_automatic_uncertainty_follows_saved_preferences(tmp_path, policy, want):
    s, coverage, run, snapshot, sha = setup(tmp_path, {'review_mode': 'automatic', 'uncertain_match': policy})
    try:
        assert coverage.record(run.id, snapshot, [decision(sha, uncertain=True)])[0].disposition == want
    finally:
        s.close()


def test_source_disagreement_stays_pending_even_with_automatic_reuse(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path, {'review_mode': 'automatic', 'uncertain_match': 'reuse'})
    try:
        assert coverage.record(run.id, snapshot, [decision(sha, source_disagreement=True)])[0].disposition == 'pending'
    finally:
        s.close()


def test_unknown_notes_and_wrong_card_ownership_are_refused_atomically(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        for invalid in [decision(sha, chosen_note_ids=[999]), decision(sha, card_ids=[203])]:
            with pytest.raises(DomainError):
                coverage.record(run.id, snapshot, [decision(sha), invalid])
        assert coverage.latest(run.id) == []
    finally:
        s.close()


def test_decision_revisions_keep_history_without_changing_configuration(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        coverage.record(run.id, snapshot, [decision(sha)])
        coverage.record(run.id, snapshot, [decision(sha, disposition='already_covered', card_ids=[201])])
        assert coverage.latest(run.id)[0].disposition == 'already_covered'
        assert len(coverage.runs.read(run.id).events) == 3
        assert coverage.config.read().config_version == 1
    finally:
        s.close()


def test_saved_preference_change_affects_later_decisions_in_same_run(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        coverage.record(run.id, snapshot, [decision(sha, uncertain=True)])
        change = coverage.config.propose({'review_mode': 'automatic', 'uncertain_match': 'create'}, 1)
        coverage.config.confirm(change.id)
        result = coverage.record(run.id, snapshot, [decision(sha, uncertain=True)])
        assert result[0].disposition == 'propose_create'
        events = coverage.runs.read(run.id).events
        assert events[1].payload['config_version'] == 1
        assert events[2].payload['config_version'] == 2
        assert coverage.runs.read(run.id).config_version == 1
    finally:
        s.close()


def test_active_cards_are_left_unchanged_and_repeat_decisions_do_not_create_cards(tmp_path):
    s, coverage, run, snapshot, sha = setup(tmp_path)
    try:
        for _ in range(2):
            result = coverage.record(run.id, snapshot, [decision(sha, card_ids=[201])])
            assert result[0].disposition == 'already_covered'
            assert result[0].card_ids == [201]
        assert s.get_cards(run.workspace)['cards'] == []
    finally:
        s.close()


@pytest.mark.parametrize('automatic', [False, True])
def test_missing_selected_cards_never_implies_coverage_of_suspended_note(tmp_path, automatic):
    from ankiplusmcp.coverage import ExistingNote
    prefs = {'review_mode': 'automatic', 'uncertain_match': 'reuse'} if automatic else None
    s, coverage, run, snapshot, sha = setup(tmp_path, prefs)
    try:
        snapshot.notes = [ExistingNote(note_id=101, card_ids=[202], suspended_card_ids=[202])]
        result = coverage.record(run.id, snapshot, [decision(sha, card_ids=[], uncertain=automatic)])
        assert result[0].disposition == 'pending'
    finally:
        s.close()
