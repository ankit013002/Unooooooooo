"""Room lifecycle and WebSocket-facing game orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import secrets
import string
from typing import Any

from fastapi import WebSocket

from Server.bots import LlamaBot
from Server.game import ActionResult, COLORS, UnoGame


LOGGER = logging.getLogger(__name__)
ROOM_ALPHABET = string.ascii_uppercase.replace("I", "").replace("O", "") + "23456789"


class RoomError(Exception):
    pass


@dataclass
class Player:
    player_id: int
    name: str
    token: str
    bot: bool = False
    connected: bool = False
    ready: bool = False
    websocket: WebSocket | None = None


class GameRoom:
    def __init__(self, code: str, human_seats: int = 2, bot_seats: int = 2):
        if human_seats < 1 or bot_seats < 0 or not 2 <= human_seats + bot_seats <= 4:
            raise ValueError("Rooms need two to four total seats and at least one human")
        self.code = code
        self.human_seats = human_seats
        self.bot_seats = bot_seats
        self.player_count = human_seats + bot_seats
        self.game = UnoGame(self.player_count)
        self.players: dict[int, Player] = {}
        self.bots: dict[int, LlamaBot] = {}
        self.lock = asyncio.Lock()
        self.bot_task: asyncio.Task | None = None
        self.bot_thinking: int | None = None
        self.generation = 0

        for player_id in range(human_seats, self.player_count):
            bot_number = player_id - human_seats + 1
            self.players[player_id] = Player(
                player_id=player_id,
                name=f"Llama {bot_number}",
                token=f"bot-{bot_number}",
                bot=True,
                connected=True,
                ready=True,
            )
            self.bots[player_id] = LlamaBot()

    async def connect(self, websocket: WebSocket, name: str, token: str | None) -> Player:
        async with self.lock:
            player = self._find_reconnecting_player(token)
            if player is None:
                player = self._create_human(name)
            player.websocket = websocket
            player.connected = True
            player.name = clean_player_name(name or player.name)
            await websocket.send_json(
                {
                    "type": "welcome",
                    "roomCode": self.code,
                    "playerId": player.player_id,
                    "token": player.token,
                }
            )
            await self._broadcast_state_locked()
            self._ensure_bot_task_locked()
            return player

    async def disconnect(self, player_id: int, websocket: WebSocket) -> None:
        async with self.lock:
            player = self.players.get(player_id)
            if not player or player.websocket is not websocket:
                return
            player.websocket = None
            player.connected = False
            player.ready = False
            self.generation += 1
            await self._broadcast_state_locked()

    async def handle_action(self, player_id: int, payload: dict[str, Any]) -> None:
        async with self.lock:
            player = self.players.get(player_id)
            if not player or player.bot:
                raise RoomError("Unknown human player")
            action = payload.get("action")

            if action in {"ready", "rematch"}:
                player.ready = True
                await self._start_if_ready_locked()
                await self._broadcast_state_locked()
                return

            if not self.game.started:
                raise RoomError("The game has not started")
            if not self._all_humans_connected():
                raise RoomError("The game is paused while a player reconnects")

            if action == "uno":
                result = self.game.call_uno(player_id)
            elif action == "draw":
                result = self.game.draw(player_id)
            elif action == "play":
                result = self.game.play_card(player_id, str(payload.get("card", "")))
            elif action == "color":
                result = self.game.choose_color(player_id, str(payload.get("color", "")).title())
            else:
                raise RoomError("Unknown action")

            if not result.valid:
                raise RoomError(result.message)
            await self._after_action_locked(result)

    def state_for(self, viewer_id: int) -> dict[str, Any]:
        viewer = self.players[viewer_id]
        humans = [self.players.get(player_id) for player_id in range(self.human_seats)]
        all_players = [self.players.get(player_id) for player_id in range(self.player_count)]
        phase = "game" if self.game.started else "finished" if self.game.winner is not None else "lobby"
        hand = list(self.game.hands[viewer_id]) if self.game.started or self.game.winner is not None else []
        legal_cards = []
        if (
            self.game.started
            and self.game.current_turn == viewer_id
            and self.game.pending_color_player is None
            and self._all_humans_connected()
        ):
            legal_cards = self.game.legal_cards(viewer_id)
        winner = self.players.get(self.game.winner) if self.game.winner is not None else None

        return {
            "type": "state",
            "roomCode": self.code,
            "phase": phase,
            "paused": self.game.started and not self._all_humans_connected(),
            "playerId": viewer_id,
            "players": [
                {
                    **self._player_json(player),
                    "cardCount": len(self.game.hands[player.player_id])
                    if self.game.started or self.game.winner is not None
                    else 0,
                }
                for player in all_players
                if player
            ],
            "humanSeats": self.human_seats,
            "connectedHumans": sum(bool(player and player.connected) for player in humans),
            "hand": hand,
            "legalCards": legal_cards,
            "topCard": self.game.top_card,
            "deckCount": len(self.game.deck),
            "currentTurn": self.game.current_turn if self.game.started else None,
            "direction": self.game.direction,
            "pendingColor": self.game.pending_color_player == viewer_id,
            "winnerId": self.game.winner,
            "winnerName": winner.name if winner else None,
            "botThinking": self.bot_thinking,
            "ready": viewer.ready,
        }

    def _find_reconnecting_player(self, token: str | None) -> Player | None:
        if not token:
            return None
        return next(
            (player for player in self.players.values() if not player.bot and player.token == token),
            None,
        )

    def _create_human(self, name: str) -> Player:
        player_id = next(
            (candidate for candidate in range(self.human_seats) if candidate not in self.players),
            None,
        )
        if player_id is None:
            raise RoomError("This room already has all of its human players")
        player = Player(
            player_id=player_id,
            name=clean_player_name(name),
            token=secrets.token_urlsafe(24),
            connected=True,
        )
        self.players[player_id] = player
        return player

    async def _start_if_ready_locked(self) -> None:
        humans = [self.players.get(player_id) for player_id in range(self.human_seats)]
        if not all(player and player.connected and player.ready for player in humans):
            return
        self.generation += 1
        self.game.start()
        self.bot_thinking = None
        for player in self.players.values():
            player.ready = player.bot
        LOGGER.info("Room %s started a %s-player game", self.code, self.player_count)
        self._ensure_bot_task_locked()

    async def _after_action_locked(self, result: ActionResult) -> None:
        if result.winner is not None:
            for player in self.players.values():
                player.ready = player.bot
        await self._broadcast_state_locked()
        self._ensure_bot_task_locked()

    def _ensure_bot_task_locked(self) -> None:
        if (
            not self.game.started
            or not self._all_humans_connected()
            or self.game.current_turn not in self.bots
            or (self.bot_task and not self.bot_task.done())
        ):
            return
        self.bot_task = asyncio.create_task(self._run_bot_turns(), name=f"room-{self.code}-bots")

    async def _run_bot_turns(self) -> None:
        try:
            while True:
                async with self.lock:
                    if (
                        not self.game.started
                        or not self._all_humans_connected()
                        or self.game.current_turn not in self.bots
                    ):
                        return
                    player_id = self.game.current_turn
                    generation = self.generation
                    hand = list(self.game.hands[player_id])
                    view = {
                        "hand": hand,
                        "legal_cards": self.game.legal_cards(player_id),
                        "top_card": self.game.top_card,
                        "hand_counts": [len(cards) for cards in self.game.hands],
                        "direction": "clockwise" if self.game.direction == 1 else "counterclockwise",
                    }
                    bot = self.bots[player_id]
                    self.bot_thinking = player_id
                    await self._broadcast_state_locked()

                decision = await asyncio.to_thread(bot.decide, view)
                await asyncio.sleep(0.45)

                async with self.lock:
                    if (
                        generation != self.generation
                        or not self.game.started
                        or self.game.current_turn != player_id
                    ):
                        continue
                    if decision.action == "play" and decision.card:
                        if len(self.game.hands[player_id]) == 2:
                            self.game.call_uno(player_id)
                        result = self.game.play_card(player_id, decision.card)
                        if result.valid and result.needs_color:
                            color = decision.color if decision.color in COLORS else COLORS[0]
                            result = self.game.choose_color(player_id, color)
                        LOGGER.info("Room %s: %s played %s", self.code, self.players[player_id].name, decision.card)
                    else:
                        result = self.game.draw(player_id)
                        LOGGER.info("Room %s: %s drew", self.code, self.players[player_id].name)
                    self.bot_thinking = None
                    await self._after_action_locked(result)
        finally:
            async with self.lock:
                self.bot_thinking = None

    async def _broadcast_state_locked(self) -> None:
        disconnected: list[int] = []
        for player_id, player in self.players.items():
            if player.bot or not player.connected or player.websocket is None:
                continue
            try:
                await player.websocket.send_json(self.state_for(player_id))
            except Exception:
                disconnected.append(player_id)
        for player_id in disconnected:
            player = self.players[player_id]
            player.connected = False
            player.websocket = None

    def _all_humans_connected(self) -> bool:
        return all(
            player_id in self.players and self.players[player_id].connected
            for player_id in range(self.human_seats)
        )

    @staticmethod
    def _player_json(player: Player) -> dict[str, Any]:
        return {
            "id": player.player_id,
            "name": player.name,
            "bot": player.bot,
            "connected": player.connected,
            "ready": player.ready,
        }


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}
        self.lock = asyncio.Lock()

    async def create(self, human_seats: int = 2, bot_seats: int = 2) -> GameRoom:
        async with self.lock:
            code = self._new_code()
            room = GameRoom(code, human_seats, bot_seats)
            self.rooms[code] = room
            return room

    def get(self, code: str) -> GameRoom | None:
        return self.rooms.get(normalize_room_code(code))

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(4))
            if code not in self.rooms:
                return code


def normalize_room_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())[:4]


def clean_player_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())[:20]
    return cleaned or "Player"
