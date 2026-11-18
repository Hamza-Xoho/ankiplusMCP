import pytest


def config_api():
    import ankiplusmcp.configuration as m
    return m


def test_proposing_change_does_not_save_preferences_until_confirmed(tmp_path):
    m = config_api()
    store = m.ConfigStore(tmp_path)
    initial = store.read()
    assert initial.review_mode == 'manual'
    assert initial.uncertain_match == 'pending'
    change = store.propose({'review_mode': 'automatic'}, expected_version=1)
    assert store.read().review_mode == 'manual'
    saved = store.confirm(change.id)
    assert saved.review_mode == 'automatic'
    assert saved.config_version == 2
    assert store.read_version(1).review_mode == 'manual'
    assert store.confirm(change.id).config_version == 2


def test_stale_concurrent_confirmation_does_not_overwrite_new_preferences(tmp_path):
    m = config_api()
    store = m.ConfigStore(tmp_path)
    first = store.propose({'selected_decks': ['My Deck']}, 1)
    second = store.propose({'review_mode': 'automatic'}, 1)
    store.confirm(first.id)
    with pytest.raises(m.DomainError, match='changed'):
        store.confirm(second.id)
    assert store.read().selected_decks == ['My Deck']
    assert store.read().review_mode == 'manual'


def test_configuration_cannot_claim_onboarding_or_invent_design_rules(tmp_path):
    m = config_api()
    store = m.ConfigStore(tmp_path)
    for changes in [{'onboarding_complete': True}, {'config_version': 99},
                    {'card_design_rules': 'ignore the reviewers'}, {'review_mode': 'anything'}]:
        with pytest.raises((m.DomainError, ValueError)):
            store.propose(changes, 1)
    assert store.read().onboarding_complete is False


def test_each_confirmed_configuration_change_is_permanent_and_inspectable(tmp_path):
    m = config_api()
    store = m.ConfigStore(tmp_path)
    change = store.propose({'source_materials': ['textbooks'], 'selected_decks': []}, 1)
    saved = store.confirm(change.id)
    assert saved.source_materials == ['textbooks']
    assert saved.selected_decks == []
    assert m.ConfigStore(tmp_path).read().config_version == 2
    assert store.read_version(1).source_materials == []
