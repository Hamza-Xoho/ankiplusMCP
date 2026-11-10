import pytest
from cards.target import _space_amp


@pytest.mark.parametrize("raw,want", [
    ("Mitochondria& Golgi", "Mitochondria & Golgi"),
    ("Mitochondria &Golgi", "Mitochondria & Golgi"),
    ("Mitochondria&Golgi", "Mitochondria & Golgi"),
    ("Mitochondria & Golgi", "Mitochondria & Golgi"),
    ("Mitochondria  &  Golgi", "Mitochondria & Golgi"),
])
def test_ampersand_spacing(raw, want):
    assert _space_amp(raw) == want
