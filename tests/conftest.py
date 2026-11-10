from pathlib import Path
import os
import pytest

@pytest.fixture
def private_fixture():
    def locate(name):
        path = Path(__file__).parent / 'fixtures' / 'private' / name
        if not path.exists():
            if os.environ.get('CARDS_PUBLIC_CI') == '1':
                pytest.skip(f'private fixture {name} is not published')
            pytest.fail(f'missing fixture {name}: see HANDOVER §Setup')
        return path
    return locate
