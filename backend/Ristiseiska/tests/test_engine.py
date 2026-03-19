from ristiseiska.state import reset
from ristiseiska.moves import available_actions, Action
from ristiseiska.engine import step


def test_step_play_advances_turn_and_updates_hand_and_table():
    state = reset(seed=123)
    p = state.turn
    actions = available_actions(state, p)

    # Pick a non-continuation PLAY if possible
    play_actions = [a for a in actions if a.kind == "PLAY" and a.cont is False]
    if not play_actions:
        # could be REQUEST case, tested elsewhere
        return

    a = play_actions[0]
    prev_hand_size = len(state.hands[p])
    step(state, a)

    assert len(state.hands[p]) == prev_hand_size - 1
    assert state.table.has(a.card)
    assert state.turn != p


def test_request_then_give_transfers_card_and_advances():
    state = reset(seed=123)

    # Find a player who has no legal plays
    target = None
    for i in range(4):
        if available_actions(state, i) == [Action("REQUEST", None)]:
            target = i
            break
    if target is None:
        # If seed happens to give everyone a legal play, skip
        return

    state.turn = target
    step(state, Action("REQUEST", None))

    assert state.pending_give_from is not None
    assert state.pending_give_to == target
    giver = state.pending_give_from
    assert state.turn == giver

    # giver must be able to GIVE any card
    give_actions = available_actions(state, giver)
    assert give_actions and all(a.kind == "GIVE" for a in give_actions)

    chosen = give_actions[0]
    giver_prev = len(state.hands[giver])
    recv_prev = len(state.hands[target])

    step(state, chosen)

    assert state.pending_give_from is None
    assert len(state.hands[giver]) == giver_prev - 1
    assert len(state.hands[target]) == recv_prev + 1
