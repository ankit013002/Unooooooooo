"""Authoritative, transport-independent UNO game rules."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable


COLORS = ("Red", "Yellow", "Green", "Blue")
VALUES = tuple(str(value) for value in range(10)) + ("Skip", "Reverse", "Draw")
WILD_CARDS = ("Wild", "Draw 4")


@dataclass
class ActionResult:
    valid: bool
    message: str = ""
    needs_color: bool = False
    winner: int | None = None
    drawn_cards: dict[int, list[str]] = field(default_factory=dict)


def build_deck() -> list[str]:
    """Build a standard 108-card UNO deck using the project's card names."""
    cards: list[str] = []
    for color in COLORS:
        cards.append(f"{color} 0")
        for value in VALUES[1:]:
            cards.extend([f"{color} {value}"] * 2)
    cards.extend(["Wild"] * 4)
    cards.extend(["Draw 4"] * 4)
    return cards


class UnoGame:
    def __init__(self, player_count: int = 4, rng: random.Random | None = None):
        if player_count < 2:
            raise ValueError("UNO requires at least two players")
        self.player_count = player_count
        self.rng = rng or random.Random()
        self.deck: list[str] = []
        self.discard_pile: list[str] = []
        self.hands: list[list[str]] = [[] for _ in range(player_count)]
        self.current_turn = 0
        self.direction = 1
        self.uno_called = [False] * player_count
        self.pending_color_player: int | None = None
        self.pending_wild: str | None = None
        self.started = False
        self.winner: int | None = None

    @property
    def top_card(self) -> str | None:
        return self.discard_pile[-1] if self.discard_pile else None

    def start(self) -> None:
        self.deck = build_deck()
        self.rng.shuffle(self.deck)
        self.discard_pile = []
        self.hands = [[] for _ in range(self.player_count)]
        self.current_turn = 0
        self.direction = 1
        self.uno_called = [False] * self.player_count
        self.pending_color_player = None
        self.pending_wild = None
        self.winner = None

        for _ in range(7):
            for player_id in range(self.player_count):
                self.hands[player_id].append(self.deck.pop())

        first_card = self.deck.pop()
        while first_card in WILD_CARDS:
            self.deck.insert(0, first_card)
            first_card = self.deck.pop()
        self.discard_pile.append(first_card)
        self.started = True

    def legal_cards(self, player_id: int) -> list[str]:
        return [card for card in self.hands[player_id] if self.is_valid_play(card)]

    def is_valid_play(self, card: str) -> bool:
        if not self.top_card:
            return False
        if card in WILD_CARDS:
            return True
        card_color, card_value = card.split(maxsplit=1)
        top_color, top_value = self.top_card.split(maxsplit=1)
        return card_color == top_color or card_value == top_value

    def call_uno(self, player_id: int) -> ActionResult:
        if not self.started or len(self.hands[player_id]) != 2:
            return ActionResult(False, "UNO can only be called with two cards")
        self.uno_called[player_id] = True
        return ActionResult(True)

    def play_card(self, player_id: int, card: str) -> ActionResult:
        error = self._turn_error(player_id)
        if error:
            return ActionResult(False, error)
        if card not in self.hands[player_id] or not self.is_valid_play(card):
            return ActionResult(False, "That card cannot be played")

        self.hands[player_id].remove(card)
        self.discard_pile.append(card)

        if not self.hands[player_id]:
            self.winner = player_id
            self.started = False
            return ActionResult(True, winner=player_id)

        penalty: dict[int, list[str]] = {}
        if len(self.hands[player_id]) == 1 and not self.uno_called[player_id]:
            penalty[player_id] = self._draw_cards(player_id, 2)
        self.uno_called[player_id] = False

        if card in WILD_CARDS:
            self.pending_color_player = player_id
            self.pending_wild = card
            return ActionResult(True, needs_color=True, drawn_cards=penalty)

        _, value = card.split(maxsplit=1)
        if value == "Reverse":
            self.direction *= -1
            self._advance(2 if self.player_count == 2 else 1)
        elif value == "Skip":
            self._advance(2)
        elif value == "Draw":
            target = self._player_after(player_id)
            penalty[target] = self._draw_cards(target, 2)
            self._advance(2)
        else:
            self._advance()
        return ActionResult(True, drawn_cards=penalty)

    def choose_color(self, player_id: int, color: str) -> ActionResult:
        if player_id != self.pending_color_player or self.pending_wild is None:
            return ActionResult(False, "No color choice is pending for this player")
        if color not in COLORS:
            return ActionResult(False, "Invalid color")

        wild = self.pending_wild
        self.discard_pile[-1] = f"{color} {'Plus' if wild == 'Draw 4' else 'Wild'}"
        self.pending_color_player = None
        self.pending_wild = None

        drawn: dict[int, list[str]] = {}
        if wild == "Draw 4":
            target = self._player_after(player_id)
            drawn[target] = self._draw_cards(target, 4)
            self._advance(2)
        else:
            self._advance()
        return ActionResult(True, drawn_cards=drawn)

    def draw(self, player_id: int) -> ActionResult:
        error = self._turn_error(player_id)
        if error:
            return ActionResult(False, error)
        cards = self._draw_cards(player_id, 1)
        self.uno_called[player_id] = False
        self._advance()
        return ActionResult(True, drawn_cards={player_id: cards})

    def public_hands_for(self, viewer_id: int) -> list[list[str]]:
        return [
            list(hand) if player_id == viewer_id else ["Uno Back"] * len(hand)
            for player_id, hand in enumerate(self.hands)
        ]

    def _turn_error(self, player_id: int) -> str | None:
        if not self.started:
            return "The game has not started"
        if self.pending_color_player is not None:
            return "A wild color choice is pending"
        if player_id != self.current_turn:
            return "It is not your turn"
        return None

    def _advance(self, steps: int = 1) -> None:
        for _ in range(steps):
            self.current_turn = (self.current_turn + self.direction) % self.player_count

    def _player_after(self, player_id: int) -> int:
        return (player_id + self.direction) % self.player_count

    def _draw_cards(self, player_id: int, count: int) -> list[str]:
        cards: list[str] = []
        for _ in range(count):
            self._replenish_deck()
            if not self.deck:
                break
            card = self.deck.pop()
            self.hands[player_id].append(card)
            cards.append(card)
        return cards

    def _replenish_deck(self) -> None:
        if self.deck or len(self.discard_pile) <= 1:
            return
        top = self.discard_pile[-1]
        self.deck = [self._uncolor_wild(card) for card in self.discard_pile[:-1]]
        self.rng.shuffle(self.deck)
        self.discard_pile = [top]

    @staticmethod
    def _uncolor_wild(card: str) -> str:
        if card.endswith(" Wild"):
            return "Wild"
        if card.endswith(" Plus"):
            return "Draw 4"
        return card


def most_common_color(cards: Iterable[str]) -> str:
    counts = {color: 0 for color in COLORS}
    for card in cards:
        if card not in WILD_CARDS:
            counts[card.split(maxsplit=1)[0]] += 1
    return max(COLORS, key=lambda color: counts[color])
