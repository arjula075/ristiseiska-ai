from ristiseiska.cards import deal, card_7_of_clubs
from ristiseiska.game import starting_player

def test_starting_player_has_7_of_clubs():
    hands = deal(seed=123)
    sp = starting_player(hands)
    assert card_7_of_clubs() in hands[sp]
