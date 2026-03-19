from ristiseiska.cards import Card, Suit
from ristiseiska.state import TableState
from ristiseiska.moves import legal_plays, Action, available_actions
from ristiseiska.state import reset


def test_table_start_requires_7():
    table = TableState()
    assert table.can_play(Card(Suit.CLUBS, 7)) is True
    assert table.can_play(Card(Suit.CLUBS, 6)) is False
    assert table.can_play(Card(Suit.HEARTS, 7)) is True


def test_after_7_only_6_allowed():
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))
    assert table.can_play(Card(Suit.CLUBS, 6)) is True
    assert table.can_play(Card(Suit.CLUBS, 8)) is False

def test_after_6_only_8_allowed():
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))
    table.add(Card(Suit.CLUBS, 6))
    assert table.can_play(Card(Suit.CLUBS, 8)) is True
    assert table.can_play(Card(Suit.CLUBS, 5)) is False

def test_after_6_and_8_both_sides_open():
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))
    table.add(Card(Suit.CLUBS, 6))
    table.add(Card(Suit.CLUBS, 8))

    assert table.can_play(Card(Suit.CLUBS, 5)) is True
    assert table.can_play(Card(Suit.CLUBS, 9)) is True

def test_chain_extends_correctly_down_and_up():
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))
    table.add(Card(Suit.CLUBS, 6))

    # House rule: must play 8 before any further down-cards (5,4,...)
    assert table.can_play(Card(Suit.CLUBS, 5)) is False
    assert table.can_play(Card(Suit.CLUBS, 8)) is True

    table.add(Card(Suit.CLUBS, 8))

    # Now both sides are open
    assert table.can_play(Card(Suit.CLUBS, 5)) is True
    assert table.can_play(Card(Suit.CLUBS, 9)) is True



def test_legal_plays_filters_hand():
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))

    hand = [
        Card(Suit.CLUBS, 6),
        Card(Suit.CLUBS, 9),
        Card(Suit.HEARTS, 7),
        Card(Suit.SPADES, 2),
    ]
    plays = legal_plays(hand, table)
    assert set(plays) == {Card(Suit.CLUBS, 6), Card(Suit.HEARTS, 7)}


def test_available_actions_forces_play_if_possible():
    state = reset(seed=123)
    player = state.turn
    actions = available_actions(state, player)

    # If any legal play exists, all actions must be PLAY
    if any(a.kind == "PLAY" for a in actions):
        assert all(a.kind == "PLAY" for a in actions)
    else:
        assert actions == [Action("REQUEST", None)]
