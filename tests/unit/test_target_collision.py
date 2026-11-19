"""A second occupied collision name must not reuse somebody else's deck."""
import json
from types import SimpleNamespace
from cards.target import run
from test_build_command import fixture


def test_collision_suffix_itself_is_occupied(tmp_path):
    folder,source=fixture(tmp_path)
    (folder/'source').mkdir(exist_ok=True)
    (folder/'source/slides.json').write_text(json.dumps({'slides':[{'n':1,'title':'Cell biology','text':'Cells','figures':[]}]}))
    listing=folder/'existing-decks.json';listing.write_text(json.dumps(['Cell biology','Cell biology (MED241 L006)']))
    run(SimpleNamespace(build=str(folder),existing_decks=str(listing),course='MED241',number=6,title='Cell biology',subject=None,system=None))
    target=json.loads((folder/'target.json').read_text())
    assert target['deck']=='Cell biology (MED241 L006 2)' and target['create_deck'] is True


def test_p1_refreshes_target_when_actual_preflight_listing_arrives_later(tmp_path):
    from cards import build,state
    from cards.common.paths import Build
    from test_build_command import prepared
    folder=prepared(tmp_path,'P1','P0')
    target_path=folder/'target.json';target=json.loads(target_path.read_text())
    (folder/'existing-decks.json').write_text(json.dumps([target['deck']]))
    build.extract_and_target(Build(folder),state.load(Build(folder)),SimpleNamespace())
    updated=json.loads(target_path.read_text())
    assert updated['deck']!=target['deck'] and updated['create_deck'] is True
