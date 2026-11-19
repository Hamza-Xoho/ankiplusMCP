from ankiplusmcp.service import Service
from ankiplusmcp.server import API
import pytest
from ankiplusmcp.store import DomainError


def test_explicit_preference_confirmation_updates_guide_and_survives_restart(tmp_path):
    s=Service(tmp_path/'work',[tmp_path]); api=API(s)
    try:
        initial=api.get_student_setup()
        assert initial['configuration']['review_mode']=='manual'
        assert not initial['configuration']['onboarding_complete']
        proposal=api.propose_preferences({'source_materials':['textbook chapters'],'selected_decks':[]},1)
        assert proposal['changed_keys']==['source_materials']
        assert api.get_student_setup()['configuration']['source_materials']==[]
        result=api.confirm_preferences(proposal['id'])
        assert result['configuration']['source_materials']==['textbook chapters']
        from pathlib import Path
        guide=Path(result['guide_path']); assert guide.is_file()
        assert 'chapters 2 and 3' in guide.read_text()
        assert 'Setup still needs verification' in guide.read_text()
        assert not result['configuration']['onboarding_complete']
        assert api.confirm_preferences(proposal['id'])['configuration']['config_version']==2
    finally:s.close()
    s=Service(tmp_path/'work',[tmp_path])
    try: assert API(s).get_student_setup()['configuration']['source_materials']==['textbook chapters']
    finally:s.close()


def test_onboarding_and_health_cannot_be_saved_as_user_preferences(tmp_path):
    s=Service(tmp_path/'work',[tmp_path])
    try:
        with pytest.raises(DomainError): API(s).propose_preferences({'onboarding_complete':True},1)
    finally:s.close()
