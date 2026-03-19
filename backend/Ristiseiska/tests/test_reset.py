from ristiseiska.state import reset
from ristiseiska.cards import card_7_of_clubs

def test_reset_forces_7_of_clubs_on_table():
    state = reset(seed=123)
    assert state.table.has(card_7_of_clubs())

def test_reset_removes_7_of_clubs_from_some_hand():
    state = reset(seed=123)
    # Ensure no one still has 7♣ in hand
    all_cards = [c for h in state.hands for c in h]
    assert card_7_of_clubs() not in all_cards

def test_reset_turn_is_valid_player():
    state = reset(seed=123)
    assert 0 <= state.turn < 4

def test_reset_total_cards_accounting():
    state = reset(seed=123)
    # 52 total cards: 51 in hands + 1 on table
    hand_cards = sum(len(h) for h in state.hands)
    table_cards = sum(len(v) for v in state.table.played.values())
    assert hand_cards + table_cards == 52
