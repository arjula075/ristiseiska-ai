from ristiseiska.state import GameState, TableState
from ristiseiska.cards import Card, Suit
from ristiseiska.engine import step
from ristiseiska.moves import Action


def test_game_ends_when_only_one_player_has_cards_left():
    # Minimal table with just 7♣
    table = TableState()
    table.add(Card(Suit.CLUBS, 7))

    # Player 0 has one legal move: 6♣ (since after 7 must play 6)
    hands = [
        [Card(Suit.CLUBS, 6)],  # will play and become empty -> placement #1
        [],                     # already empty
        [],                     # already empty
        [Card(Suit.SPADES, 2)], # will be the loser (last with cards)
    ]

    state = GameState(
        hands=hands,
        table=table,
        turn=0,
        starter=0,
    )

    step(state, Action("PLAY", Card(Suit.CLUBS, 6), cont=False))

    assert state.done is True
    assert state.loser == 3
    assert state.placements == [0, 3]
