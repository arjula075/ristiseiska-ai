from ristiseiska.cards import deal, standard_deck

def test_deal_is_deterministic():
    hands1 = deal(seed=123)
    hands2 = deal(seed=123)
    assert hands1 == hands2

def test_deal_distributes_all_cards_once():
    hands = deal(seed=42)
    all_cards = [c for h in hands for c in h]
    assert len(all_cards) == 52
    assert len(set(all_cards)) == 52
    assert set(all_cards) == set(standard_deck())

def test_deal_hand_sizes():
    hands = deal(seed=1)
    assert len(hands) == 4
    assert all(len(h) == 13 for h in hands)
