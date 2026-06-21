"""TCP server for human and Llama-powered UNO players."""

from __future__ import annotations

import logging
import os
import socket
import threading
import time

try:
    from .bots import LlamaBot
    from .game import COLORS, UnoGame
except ImportError:  # Support `python Server/Server.py`.
    from bots import LlamaBot
    from game import COLORS, UnoGame


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("uno.server")

HOST = os.getenv("UNO_HOST", "127.0.0.1")
PORT = int(os.getenv("UNO_PORT", "65432"))
HUMAN_PLAYERS = int(os.getenv("UNO_HUMANS", "2"))
BOT_PLAYERS = int(os.getenv("UNO_BOTS", "2"))
BOT_DELAY = float(os.getenv("UNO_BOT_DELAY", "0.8"))
PLAYER_COUNT = HUMAN_PLAYERS + BOT_PLAYERS

if not 2 <= PLAYER_COUNT <= 4:
    raise ValueError("UNO_HUMANS + UNO_BOTS must be between 2 and 4")
if HUMAN_PLAYERS < 1:
    raise ValueError("At least one human player is required")


class UnoServer:
    def __init__(self) -> None:
        self.game = UnoGame(PLAYER_COUNT)
        self.clients: dict[int, socket.socket] = {}
        self.ready_players: set[int] = set()
        self.bots = {
            player_id: LlamaBot()
            for player_id in range(HUMAN_PLAYERS, PLAYER_COUNT)
        }
        self.lock = threading.RLock()
        self.send_lock = threading.Lock()
        self.server_socket: socket.socket | None = None
        self.bot_worker_active = False
        self.generation = 0

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            self.server_socket = server_socket
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen()
            LOGGER.info(
                "UNO server listening on %s:%s (%s human seats, %s Llama seats)",
                HOST,
                PORT,
                HUMAN_PLAYERS,
                BOT_PLAYERS,
            )
            for player_id, bot in self.bots.items():
                LOGGER.info("Player %s: %s", player_id + 1, bot.name)

            try:
                while True:
                    connection, address = server_socket.accept()
                    self._accept_human(connection, address)
            except KeyboardInterrupt:
                LOGGER.info("Shutting down server")
            finally:
                with self.lock:
                    for connection in self.clients.values():
                        connection.close()

    def _accept_human(self, connection: socket.socket, address: tuple[str, int]) -> None:
        with self.lock:
            available = next(
                (player_id for player_id in range(HUMAN_PLAYERS) if player_id not in self.clients),
                None,
            )
            if available is None:
                connection.sendall(b"SERVER_FULL\n")
                connection.close()
                return
            self.clients[available] = connection
            LOGGER.info("Human player %s connected from %s:%s", available + 1, *address)
            self._send(available, f"ASSIGN_ID {available}\n")
            self._broadcast_connected()

        threading.Thread(
            target=self._handle_human,
            args=(available, connection),
            daemon=True,
            name=f"human-{available + 1}",
        ).start()

    def _handle_human(self, player_id: int, connection: socket.socket) -> None:
        buffer = ""
        try:
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    if message.strip():
                        self._handle_message(player_id, message.strip())
        except (ConnectionError, UnicodeDecodeError, OSError) as error:
            LOGGER.info("Player %s connection ended: %s", player_id + 1, error)
        finally:
            self._disconnect_human(player_id, connection)

    def _handle_message(self, player_id: int, message: str) -> None:
        with self.lock:
            if message == "READY":
                self.ready_players.add(player_id)
                LOGGER.info("Human player %s is ready", player_id + 1)
                self._start_if_ready()
                return
            if message == "UNO":
                result = self.game.call_uno(player_id)
                if not result.valid:
                    self._send(player_id, f"ERROR {result.message}\n")
                return
            if message == "DRAW":
                result = self.game.draw(player_id)
            elif message.startswith("PLAY "):
                result = self.game.play_card(player_id, message[5:].strip())
            elif message.startswith("CHOOSE_COLOR "):
                result = self.game.choose_color(player_id, message.split(maxsplit=1)[1].title())
            else:
                self._send(player_id, "ERROR Unknown command\n")
                return

            if not result.valid:
                self._send(player_id, f"INVALID PLAY\nERROR {result.message}\n")
                return
            self._after_action(player_id, result)

    def _start_if_ready(self) -> None:
        human_ids = set(range(HUMAN_PLAYERS))
        if self.game.started or set(self.clients) != human_ids or not human_ids <= self.ready_players:
            return
        self.generation += 1
        self.game.start()
        LOGGER.info("Starting a %s-player game", PLAYER_COUNT)
        self._broadcast("START\n")
        self._broadcast_state()
        self._notify_turn()

    def _after_action(self, player_id: int, result) -> None:
        self._broadcast_state()
        if result.winner is not None:
            LOGGER.info("Player %s wins", result.winner + 1)
            self._broadcast(f"WINNER {result.winner + 1}\n")
            self.ready_players.clear()
            return
        if result.needs_color:
            self._send(player_id, "CHOOSE_COLOR\n")
            return
        self._notify_turn()

    def _notify_turn(self) -> None:
        if not self.game.started:
            return
        player_id = self.game.current_turn
        if player_id in self.bots:
            self._start_bot_worker()
        else:
            self._send(player_id, "YOUR TURN\n")

    def _start_bot_worker(self) -> None:
        if self.bot_worker_active:
            return
        self.bot_worker_active = True
        threading.Thread(target=self._run_bot_turns, daemon=True, name="llama-players").start()

    def _run_bot_turns(self) -> None:
        try:
            while True:
                with self.lock:
                    if not self.game.started or self.game.current_turn not in self.bots:
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

                time.sleep(BOT_DELAY)
                decision = bot.decide(view)

                with self.lock:
                    if generation != self.generation or not self.game.started or self.game.current_turn != player_id:
                        continue
                    if decision.action == "play" and decision.card:
                        if len(self.game.hands[player_id]) == 2:
                            self.game.call_uno(player_id)
                        result = self.game.play_card(player_id, decision.card)
                        if result.valid and result.needs_color:
                            color = decision.color if decision.color in COLORS else COLORS[0]
                            result = self.game.choose_color(player_id, color)
                        LOGGER.info("Llama player %s played %s", player_id + 1, decision.card)
                    else:
                        result = self.game.draw(player_id)
                        LOGGER.info("Llama player %s drew a card", player_id + 1)
                    self._after_action(player_id, result)
        finally:
            with self.lock:
                self.bot_worker_active = False
                # A human action may have moved to a bot just as the worker exited.
                if self.game.started and self.game.current_turn in self.bots:
                    self._start_bot_worker()

    def _disconnect_human(self, player_id: int, connection: socket.socket) -> None:
        with self.lock:
            if self.clients.get(player_id) is not connection:
                return
            self.clients.pop(player_id, None)
            self.ready_players.discard(player_id)
            connection.close()
            self.generation += 1
            self.game.started = False
            self.game.pending_color_player = None
            LOGGER.info("Human player %s disconnected; returning to lobby", player_id + 1)
            self._broadcast("RESET\n")
            self._broadcast_connected()

    def _broadcast_connected(self) -> None:
        occupied_seats = len(self.clients) + BOT_PLAYERS
        self._broadcast(f"CONNECTED {occupied_seats}\n")

    def _broadcast_state(self) -> None:
        if not self.game.top_card:
            return
        for viewer_id in list(self.clients):
            hands = self.game.public_hands_for(viewer_id)
            serialized_hands = " ; ".join(",".join(hand) for hand in hands)
            self._send(viewer_id, f"STATE {self.game.top_card} {serialized_hands}\n")

    def _broadcast(self, message: str) -> None:
        for player_id in list(self.clients):
            self._send(player_id, message)

    def _send(self, player_id: int, message: str) -> None:
        connection = self.clients.get(player_id)
        if connection is None:
            return
        try:
            with self.send_lock:
                connection.sendall(message.encode("utf-8"))
        except OSError:
            pass


if __name__ == "__main__":
    UnoServer().serve_forever()
