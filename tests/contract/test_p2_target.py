import json
import pytest
from test_p2_source import cli, build_at

@pytest.fixture
def target(tmp_path):
    def make(title='Cell biology', name='MED241_L006_2026-09-13_cell-biology.md', decks=(), own=False, extra=()):
        p = tmp_path/name
        p.write_text('# '+title+'\nLecture material')
        b = build_at(tmp_path/'build',p)
        cli('extract','--build',b)
        state = json.loads((b/'build.json').read_text())
        state['facts'] = {'deck_has_source_tag':own}
        (b/'build.json').write_text(json.dumps(state))
        listing = b/'decks.json'
        listing.write_text(json.dumps(list(decks)))
        r = cli('target','--build',b,'--existing-decks',listing,*extra)
        data = json.loads((b/'target.json').read_text()) if (b/'target.json').exists() else {}
        return r,data
    return make

def test_fr1_deck_from_slide1_title(target):
    r,d = target(title='  Endoplasmic Reticulum, Mitochondria & Golgi Apparatus  ')
    assert r.returncode == 0
    assert d['deck'] == 'Endoplasmic Reticulum, Mitochondria & Golgi Apparatus'
    assert d['deck_source']=='slide1' and d['create_deck'] is True
    assert d['source_tag']=='#ColdRecall::#Source::MED241::L006_Cell_biology'

def test_fr1_deck_fallback_filename_topic(target):
    r,d = target(title='MED241')
    assert r.returncode==0 and d['deck']=='Cell biology' and d['deck_source']=='filename'

def test_fr1_deck_never_nested(target):
    r,d=target(title='Cells :: Organelles')
    assert r.returncode==0 and d['deck']=='Cells - Organelles'

def test_fr1_collision_suffix(target):
    r,d=target(decks=['Cell biology'])
    assert r.returncode==0 and d['deck']=='Cell biology (MED241 L006)' and d['create_deck']

def test_fr1_rerun_reuses_own_deck(target):
    r,d=target(decks=['Cell biology'],own=True)
    assert r.returncode==0 and d['deck']=='Cell biology' and not d['create_deck']

def test_fr1_unparseable_filename_asks(target):
    r,d=target(name='notes.md')
    assert r.returncode==1 and d['confident'] is False
    assert r.stdout.count('?')==1 and all(w in r.stdout.lower() for w in ('course','number','title'))
