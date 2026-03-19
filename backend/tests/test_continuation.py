import pytest
from ristiseiska.state import TableState, GameState
from ristiseiska.cards import Card, Suit
from ristiseiska.moves import Action
from ristiseiska.engine import step


def test_cannot_continue_if_no_follow_up_play():
    # Build a minimal state where player can play K, but then has no legal follow-up plays.
    # Suit started with 7->6->8 and currently high is Q (12), so K (13) is legal.
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))
    table.add(Card(Suit.CLUBS, 6))
    table.add(Card(Suit.CLUBS, 8))
    table.add(Card(Suit.CLUBS, 9))
    table.add(Card(Suit.CLUBS, 10))
    table.add(Card(Suit.CLUBS, 11))
    table.add(Card(Suit.CLUBS, 12))  # Q

    # Player 0 has only K♣ as legal play; after playing it, no follow-up exists from their hand.
    hands = [
        [Card(Suit.CLUBS, 13)],  # K♣
        [Card(Suit.SPADES, 2)],
        [Card(Suit.HEARTS, 3)],
        [Card(Suit.DIAMONDS, 4)],
    ]
    # sort hands (optional)
    for h in hands:
        h.sort()

    state = GameState(
        hands=hands,
        table=table,
        turn=0,
        starter=0,
        placements=[],
        pending_give_from=None,
        pending_give_to=None,
    )

    with pytest.raises(ValueError, match="Cannot continue"):
        step(state, Action("PLAY", Card(Suit.CLUBS, 13), cont=True))
