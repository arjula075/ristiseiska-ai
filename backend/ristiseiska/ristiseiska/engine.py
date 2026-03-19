from __future__ import annotations

from .state import GameState
from .moves import Action, legal_plays, is_end_rank


def _alive_players(state: GameState) -> list[int]:
    return [i for i, h in enumerate(state.hands) if len(h) > 0]


def _next_alive(state: GameState, after_player: int) -> int:
    alive = set(_alive_players(state))
    if not alive:
        raise RuntimeError("No alive players")
    p = after_player
    for _ in range(state.num_players):
        p = (p + 1) % state.num_players
        if p in alive:
            return p
    raise RuntimeError("Could not find next alive player")


def _prev_alive(state: GameState, before_player: int) -> int:
    alive = set(_alive_players(state))
    if not alive:
        raise RuntimeError("No alive players")
    p = before_player
    for _ in range(state.num_players):
        p = (p - 1) % state.num_players
        if p in alive:
            return p
    raise RuntimeError("Could not find prev alive player")


def _record_finish_if_needed(state: GameState, player: int) -> None:
    if len(state.hands[player]) == 0 and player not in state.placements:
        state.placements.append(player)


def _maybe_end_game(state: GameState) -> None:
    """
    If only one player still has cards, game ends:
      - that player is the loser
      - placements becomes complete ranking (winner first, loser last)
    """
    if state.done:
        return

    alive = _alive_players(state)
    if len(alive) == 1:
        loser = alive[0]
        if loser not in state.placements:
            state.placements.append(loser)
        state.loser = loser
        state.done = True


def _legal_give_cards(state: GameState, giver: int) -> list:
    """
    GIVE rule:
      - If giver has any non-playable cards, they must give one of those.
      - Only if all cards are currently playable may giver give any card.
    """
    hand = state.hands[giver]
    playable = legal_plays(hand, state.table)
    playable_set = set(playable)
    non_playable = [c for c in hand if c not in playable_set]
    return non_playable if non_playable else hand


def step(state: GameState, action: Action) -> GameState:
    """
    Mutates the given state.

    Turn rules:
      - PLAY consumes your turn -> next alive player,
        EXCEPT: if you play K/A and choose to continue (action.cont=True),
        you may keep the turn ONLY if you can immediately PLAY again
        (continuation cannot be used to REQUEST).
      - REQUEST triggers GIVE from previous alive.
      - GIVE transfers a chosen card, then turn advances to next alive after requester.

    Game ends when only one player has cards left.
    """
    if state.done:
        raise ValueError("Game is already done")

    player = state.turn

    # --- GIVE phase ---
    if state.pending_give_from is not None:
        if action.kind != "GIVE":
            raise ValueError("Must GIVE while pending_give_from is set")
        if player != state.pending_give_from:
            raise ValueError("Only pending_give_from player may GIVE now")
        if action.card is None:
            raise ValueError("GIVE requires a card")

        giver = state.pending_give_from
        receiver = state.pending_give_to
        if receiver is None:
            raise RuntimeError("pending_give_to missing")

        if action.card not in state.hands[giver]:
            raise ValueError("Given card not in giver's hand")

        legal_cards = _legal_give_cards(state, giver)
        if action.card not in legal_cards:
            raise ValueError(
                "Illegal GIVE: must give a non-playable card if any non-playable cards exist"
            )

        state.hands[giver].remove(action.card)
        state.hands[receiver].append(action.card)
        state.hands[receiver].sort()

        _record_finish_if_needed(state, giver)

        # clear pending
        state.pending_give_from = None
        state.pending_give_to = None

        _maybe_end_game(state)
        if state.done:
            return state

        state.turn = _next_alive(state, receiver)
        return state

    # --- Normal phase ---
    if action.kind == "PLAY":
        if action.card is None:
            raise ValueError("PLAY requires a card")

        if not state.table.can_play(action.card):
            raise ValueError(f"Illegal PLAY: {action.card}")
        if action.card not in state.hands[player]:
            raise ValueError("Card not in player's hand")

        state.hands[player].remove(action.card)
        state.table.add(action.card)

        _record_finish_if_needed(state, player)

        _maybe_end_game(state)
        if state.done:
            return state

        # Continuation rule (K/A): only if you can immediately PLAY again
        if action.cont and is_end_rank(action.card.rank):
            next_plays = legal_plays(state.hands[player], state.table)
            if not next_plays:
                raise ValueError("Cannot continue: no legal follow-up play available")
            return state  # keep same player's turn

        state.turn = _next_alive(state, player)
        return state

    if action.kind == "REQUEST":
        if legal_plays(state.hands[player], state.table):
            raise ValueError("Cannot REQUEST when legal plays exist")

        requester = player
        giver = _prev_alive(state, requester)
        state.pending_give_from = giver
        state.pending_give_to = requester
        state.turn = giver
        return state

    raise ValueError(f"Unknown action kind: {action.kind}")