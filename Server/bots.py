"""Server-side UNO players, including an Ollama-backed Llama bot."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .game import COLORS, most_common_color


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotDecision:
    action: str
    card: str | None = None
    color: str | None = None


class StrategicBot:
    """Fast local fallback that always returns a legal decision."""

    name = "Strategic bot"

    def decide(self, view: dict[str, Any]) -> BotDecision:
        legal_cards = view["legal_cards"]
        hand = view["hand"]
        if not legal_cards:
            return BotDecision("draw")

        def score(card: str) -> tuple[int, int]:
            if card == "Draw 4":
                action_score = 5
            elif card.endswith(" Draw"):
                action_score = 4
            elif card.endswith(" Skip") or card.endswith(" Reverse"):
                action_score = 3
            elif card == "Wild":
                action_score = 1
            else:
                action_score = 2
            color = card.split(maxsplit=1)[0] if card not in ("Wild", "Draw 4") else None
            color_count = sum(candidate.startswith(f"{color} ") for candidate in hand) if color else 0
            return action_score, color_count

        card = max(legal_cards, key=score)
        remaining = list(hand)
        remaining.remove(card)
        color = most_common_color(remaining) if card in ("Wild", "Draw 4") else None
        return BotDecision("play", card, color)


class LlamaBot:
    """Ask a local Ollama model to choose from server-provided legal actions."""

    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["play", "draw"]},
            "card": {"type": ["string", "null"]},
            "color": {"type": ["string", "null"], "enum": [*COLORS, None]},
        },
        "required": ["action", "card", "color"],
    }

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        fallback: StrategicBot | None = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.base_url = (base_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout or float(os.getenv("OLLAMA_TIMEOUT", "20"))
        self.fallback = fallback or StrategicBot()
        self.name = f"Llama bot ({self.model})"
        self._reported_failure = False

    def decide(self, view: dict[str, Any]) -> BotDecision:
        if not view["legal_cards"]:
            return BotDecision("draw")
        try:
            decision = self._request_decision(view)
            if self._is_legal(decision, view):
                self._reported_failure = False
                if decision.card not in ("Wild", "Draw 4"):
                    return BotDecision(decision.action, decision.card)
                return decision
            raise ValueError(f"model returned an illegal decision: {decision}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            if not self._reported_failure:
                LOGGER.warning("Llama decision unavailable (%s); using the strategic fallback", error)
                self._reported_failure = True
            return self.fallback.decide(view)

    def _request_decision(self, view: dict[str, Any]) -> BotDecision:
        prompt = (
            "You are playing UNO. Choose the strongest legal move. "
            "Return only JSON matching the supplied schema. Never invent a card.\n\n"
            f"Your hand: {json.dumps(view['hand'])}\n"
            f"Top discard: {view['top_card']}\n"
            f"Legal cards: {json.dumps(view['legal_cards'])}\n"
            f"Cards held by each player: {json.dumps(view['hand_counts'])}\n"
            f"Current direction: {view['direction']}\n"
            "Use action 'draw' only when there are no legal cards. For Wild or Draw 4, "
            "choose the color that best matches the rest of your hand."
        )
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": self.RESPONSE_SCHEMA,
                "options": {"temperature": 0},
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = json.loads(result["response"])
        return BotDecision(content["action"], content.get("card"), content.get("color"))

    @staticmethod
    def _is_legal(decision: BotDecision, view: dict[str, Any]) -> bool:
        if decision.action == "draw":
            return not view["legal_cards"]
        if decision.action != "play" or decision.card not in view["legal_cards"]:
            return False
        if decision.card in ("Wild", "Draw 4"):
            return decision.color in COLORS
        return True
