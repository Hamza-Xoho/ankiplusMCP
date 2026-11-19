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
