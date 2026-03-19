from ristiseiska.ranks import below_from_7, above_from_7
from ristiseiska.cards import standard_deck

def test_down_chain():
    assert below_from_7(7) == 6
    assert below_from_7(6) == 5
    assert below_from_7(2) == 14   # A
    assert below_from_7(14) is None

def test_up_chain():
    assert above_from_7(7) == 8
    assert above_from_7(12) == 13  # Q -> K
    assert above_from_7(13) is None
