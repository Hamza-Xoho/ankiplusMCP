from pathlib import Path
import pytest

from ankiplusmcp.configuration import UserConfig
from ankiplusmcp.store import DomainError


def capabilities():
    from ankiplusmcp.guide import VerifiedCapabilities
    return VerifiedCapabilities(anki_connection=True, interactive_review=True, independent_quality_review=True,
                                source_evidence=True, history=True)


def test_guide_uses_saved_workflow_and_explains_why(tmp_path):
    from ankiplusmcp.guide import Guide
    lecture = UserConfig(data_root=str(tmp_path), source_materials=['lecture slides'], selected_decks=['My Deck'])
    textbook = UserConfig(data_root=str(tmp_path), source_materials=['textbooks'], review_mode='automatic')
    a = Guide.render(lecture, capabilities())
    b = Guide.render(textbook, capabilities())
    assert 'lecture PDF' in a and 'chapters 2 and 3' in b
    assert 'My Deck' in a
    assert 'review is on' in a and 'review is off' in b
    assert 'same idea twice' in a
    assert 'why' in a.lower()
    assert str(tmp_path) in a
    assert all(f'## {n}.' in a for n in range(1, 8))


def test_unverified_capabilities_are_not_presented_as_available(tmp_path):
    from ankiplusmcp.guide import Guide, VerifiedCapabilities
    text = Guide.render(UserConfig(data_root=str(tmp_path)), VerifiedCapabilities())
    assert 'Setup still needs verification' in text
    assert 'Finish setup before applying changes' in text
    assert 'interactive review is ready' not in text


def test_regeneration_preserves_notes_and_does_not_overwrite_other_edits(tmp_path):
    from ankiplusmcp.guide import Guide
    config = UserConfig(data_root=str(tmp_path), source_materials=['textbooks'])
    path = Guide.write(config, capabilities())
    assert path.parent == tmp_path
    assert path.name == 'Start here — AnkiPlus.md'
    body = path.read_text().replace('<!-- user-notes:start -->\n', '<!-- user-notes:start -->\nRemember the practical exam.\n')
    path.write_text(body)
    updated = config.model_copy(update={'config_version': 2, 'review_mode': 'automatic'})
    Guide.write(updated, capabilities())
    assert 'Remember the practical exam.' in path.read_text()
    assert 'review is off' in path.read_text()
    path.write_text(path.read_text().replace('## 1. Your AnkiPlus setup', '## 1. My custom heading'))
    before = path.read_bytes()
    with pytest.raises(DomainError, match='edited'):
        Guide.write(config, capabilities())
    assert path.read_bytes() == before


def test_existing_user_document_is_preserved(tmp_path):
    from ankiplusmcp.guide import Guide
    target = tmp_path / 'Start here — AnkiPlus.md'
    target.write_text('My own document')
    with pytest.raises(DomainError):
        Guide.write(UserConfig(data_root=str(tmp_path)), capabilities())
    assert target.read_text() == 'My own document'
