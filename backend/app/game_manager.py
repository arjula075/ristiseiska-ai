from __future__ import annotations

from collections import deque
from pathlib import Path
import os

from ristiseiska.state import reset
from ristiseiska.engine import step
from ristiseiska.moves import available_actions, Action

from .ai_player import choose_model_action
from .model_loader import load_policy_model


SUIT_ORDER = ["CLUBS", "DIAMONDS", "HEARTS", "SPADES"]
SUIT_SYMBOL = {
    "CLUBS": "♣",
    "DIAMONDS": "♦",
    "HEARTS": "♥",
    "SPADES": "♠",
}

# Tämä tiedosto on tyyliin backend/app/.../game_manager.py
# backend-kansion saa näin talteen varmasti.
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = BACKEND_DIR / "models" / "policy_rl_shaped_open7_500k_v2.pt"


class GameManager:
    def __init__(self):
        self.device = os.getenv("MODEL_DEVICE", "cpu")
        self.model = None

        env_model_path = os.getenv("MODEL_PATH")
        if env_model_path:
            self.model_path = Path(env_model_path)
        else:
            self.model_path = DEFAULT_MODEL_PATH

        self.state = None
        self.recent_events = deque(maxlen=20)
        self.pending_continuation = False
        self.pending_play_card_id = None
        self.error_message = None
        self.next_seed = 1000

    # =========================
    # GAME LIFECYCLE
    # =========================

    def new_game(self):
        self.state = reset(seed=self.next_seed)
        self.next_seed += 1

        self.recent_events.clear()
        self.pending_continuation = False
        self.pending_play_card_id = None
        self.error_message = None

        self.recent_events.append("New game started.")

        self._settle_state()
        return self.get_public_state()

    # =========================
    # PUBLIC STATE
    # =========================

    def get_public_state(self):
        if self.state is None:
            return {
                "game_status": "no_game",
                "ui_mode": "NO_GAME",
                "active_player": None,
                "human_player": 0,
                "human_hand": [],
                "opponents": [],
                "table": {"suits": []},
                "pending_continuation": False,
                "pending_play_card_id": None,
                "recent_events": list(self.recent_events),
                "error": self.error_message,
            }

        ui_mode = self._detect_mode()

        return {
            "game_status": "game_over" if self._is_game_over() else "active",
            "ui_mode": ui_mode,
            "active_player": self.state.turn,
            "human_player": 0,
            "human_hand": self._serialize_hand(self.state.hands[0]),
            "opponents": self._serialize_opponents(),
            "table": self._serialize_table(),
            "pending_continuation": self.pending_continuation,
            "pending_play_card_id": self.pending_play_card_id,
            "recent_events": list(self.recent_events),
            "error": self.error_message,
        }

    # =========================
    # PLAYER ACTIONS
    # =========================

    def play_card(self, card_id: str):
        self.error_message = None

        if self.state is None:
            self.error_message = "no game"
            return self.get_public_state()

        if self.pending_continuation:
            self.error_message = "choose continuation first"
            return self.get_public_state()

        if self.pending_play_card_id is not None:
            self.error_message = "choose continuation for the selected card first"
            return self.get_public_state()

        if self.state.turn != 0:
            self.error_message = "not your turn"
            return self.get_public_state()

        actions = available_actions(self.state, 0)
        play_actions = [
            a for a in actions
            if a.kind == "PLAY" and self._action_card_id(a) == card_id
        ]

        if not play_actions:
            self.error_message = "That card cannot be played now."
            return self.get_public_state()

        cont_values = {getattr(a, "cont", False) for a in play_actions}

        if cont_values == {False, True}:
            self.pending_play_card_id = card_id
            return self.get_public_state()

        action = play_actions[0]

        acting_player = self.state.turn
        acted_card_id = self._action_card_id(action)

        step(self.state, action)
        self.recent_events.append(f"Player {acting_player} played {acted_card_id}")

        if getattr(action, "cont", False):
            self.pending_continuation = True
        else:
            self._settle_state()

        return self.get_public_state()

    def give_card(self, card_id: str):
        self.error_message = None

        if self.state is None:
            self.error_message = "no game"
            return self.get_public_state()

        if self.pending_play_card_id is not None:
            self.error_message = "choose continuation for the selected card first"
            return self.get_public_state()

        if self.state.turn != 0:
            self.error_message = "not your turn"
            return self.get_public_state()

        actions = available_actions(self.state, 0)
        action = self._find_action_by_card_id(actions, card_id, expected_kind="GIVE")

        if action is None:
            self.error_message = "That card cannot be given now."
            return self.get_public_state()

        acting_player = self.state.turn
        acted_card_id = self._action_card_id(action)

        step(self.state, action)
        self.recent_events.append(f"Player {acting_player} gave {acted_card_id}")

        self._settle_state()
        return self.get_public_state()

    def choose_continuation(self, continue_choice: bool):
        self.error_message = None

        if self.state is None:
            self.error_message = "no game"
            return self.get_public_state()

        if self.pending_play_card_id is not None:
            if self.state.turn != 0:
                self.error_message = "not your turn"
                return self.get_public_state()

            actions = available_actions(self.state, 0)
            matching = [
                a for a in actions
                if a.kind == "PLAY"
                   and self._action_card_id(a) == self.pending_play_card_id
                   and getattr(a, "cont", False) == continue_choice
            ]

            if not matching:
                self.error_message = "continuation choice is no longer valid"
                self.pending_play_card_id = None
                return self.get_public_state()

            action = matching[0]
            acted_card_id = self._action_card_id(action)

            self.pending_play_card_id = None

            step(self.state, action)
            self.recent_events.append(f"Player 0 played {acted_card_id}")

            if getattr(action, "cont", False):
                self.pending_continuation = True
                self.recent_events.append("You chose to continue.")
            else:
                self.recent_events.append("You chose not to continue.")
                self._settle_state()

            return self.get_public_state()

        if not self.pending_continuation:
            self.error_message = "no continuation pending"
            return self.get_public_state()

        self.pending_continuation = False

        if continue_choice:
            self.recent_events.append("You chose to continue.")
        else:
            self.recent_events.append("You chose not to continue.")
            self._settle_state()

        return self.get_public_state()

    # =========================
    # AI LOOP
    # =========================

    def advance_ai(self):
        self.error_message = None

        if self.state is None:
            return {"error": "no game"}

        if self._is_game_over():
            return self.get_public_state()

        if self.pending_continuation:
            self.error_message = "waiting for continuation choice"
            return self.get_public_state()

        if self.pending_play_card_id is not None:
            self.error_message = "waiting for continuation choice"
            return self.get_public_state()

        if self.state.turn == 0:
            return self.get_public_state()

        self._ensure_model_loaded()

        p = self.state.turn
        action = choose_model_action(
            state=self.state,
            player=p,
            model=self.model,
            device=self.device,
        )

        acted_card_id = self._action_card_id(action)
        acted_kind = action.kind

        step(self.state, action)

        if acted_kind == "REQUEST":
            self.recent_events.append(f"Player {p} requested a card.")
        elif acted_card_id is not None:
            verb = "played" if acted_kind == "PLAY" else "gave"
            self.recent_events.append(f"Player {p} {verb} {acted_card_id}")
        else:
            self.recent_events.append(f"Player {p} did {acted_kind.lower()}")

        self._settle_state()
        return self.get_public_state()

    # =========================
    # INTERNAL FLOW
    # =========================

    def _settle_state(self):
        if self.state is None:
            return

        while True:
            if self._is_game_over():
                return

            if self.pending_continuation:
                return

            if self.pending_play_card_id is not None:
                return

            if self.state.turn != 0:
                return

            actions = available_actions(self.state, 0)

            if not actions:
                return

            if len(actions) == 1 and actions[0].kind == "REQUEST":
                step(self.state, actions[0])
                self.recent_events.append("You cannot play. Requesting a card...")
                continue

            return

    # =========================
    # INTERNAL HELPERS
    # =========================

    def _ensure_model_loaded(self):
        if self.model is not None:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}. "
                f"Put the model under backend/models or set MODEL_PATH."
            )

        self.model = load_policy_model(
            model_path=str(self.model_path),
            device=self.device,
        )

    def _normalize_rank(self, rank: int) -> int:
        rank = int(rank)
        return 1 if rank == 14 else rank

    def _is_game_over(self):
        if self.state is None:
            return False
        return self.state.done or len(self.state.hands[0]) == 0

    def _detect_mode(self):
        if self.state is None:
            return "NO_GAME"

        if self._is_game_over():
            return "GAME_OVER"

        if self.pending_play_card_id is not None:
            return "CONTINUE"

        if self.pending_continuation:
            return "CONTINUE"

        if self.state.turn != 0:
            return "AI_THINKING"

        actions = available_actions(self.state, 0)
        kinds = {a.kind for a in actions}

        if kinds == {"GIVE"}:
            return "GIVE"

        if kinds == {"REQUEST"}:
            return "AI_THINKING"

        return "PLAY"

    def _find_action_by_card_id(self, actions, card_id: str, expected_kind: str):
        for action in actions:
            if action.kind != expected_kind:
                continue

            action_card_id = self._action_card_id(action)
            if action_card_id == card_id:
                return action

        return None

    def _action_card_id(self, action: Action):
        card = getattr(action, "card", None)
        if card is None:
            return None
        return self._card_id(card)

    def _card_id(self, card):
        rank = self._normalize_rank(card.rank)
        return f"{card.suit.name}-{rank}"

    def _card_label(self, card):
        rank = self._normalize_rank(card.rank)
        rank_label = {
            1: "A",
            11: "J",
            12: "Q",
            13: "K",
        }.get(rank, str(rank))
        return f"{rank_label}{SUIT_SYMBOL[card.suit.name]}"

    def _serialize_hand(self, hand):
        cards = sorted(
            hand,
            key=lambda c: (SUIT_ORDER.index(c.suit.name), self._normalize_rank(c.rank)),
        )
        return [
            {
                "id": self._card_id(c),
                "suit": c.suit.name,
                "rank": self._normalize_rank(c.rank),
                "label": self._card_label(c),
            }
            for c in cards
        ]

    def _serialize_opponents(self):
        out = []
        for i in range(1, 4):
            out.append(
                {
                    "player": i,
                    "cards": len(self.state.hands[i]),
                    "is_active": self.state.turn == i,
                }
            )
        return out

    def _serialize_table(self):
        table = getattr(self.state, "table", None)
        played = getattr(table, "played", None)

        if played is None:
            return {"suits": []}

        suits = []

        for suit_name in SUIT_ORDER:
            suit_enum = next(
                (s for s in played.keys() if s.name == suit_name),
                None,
            )

            suit_cards = []
            if suit_enum is not None:
                normalized = {self._normalize_rank(rank) for rank in played[suit_enum]}
                suit_cards = sorted(normalized)

            suits.append(
                {
                    "suit": suit_name,
                    "cards": suit_cards,
                }
            )

        return {"suits": suits}