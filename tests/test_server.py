import unittest
from unittest.mock import patch

from Server.bots import StrategicBot
from Server.Server import UnoServer


class FakeSocket:
    def __init__(self):
        self.messages = []

    def sendall(self, data):
        self.messages.append(data.decode("utf-8"))


class UnoServerTests(unittest.TestCase):
    def setUp(self):
        self.server = UnoServer()
        self.server.clients = {0: FakeSocket(), 1: FakeSocket()}

    def test_waits_for_every_human_before_starting(self):
        self.server._handle_message(0, "READY")
        self.assertFalse(self.server.game.started)
        self.server._handle_message(1, "READY")
        self.assertTrue(self.server.game.started)

    def test_state_message_hides_opponent_cards(self):
        self.server.game.start()
        self.server.game.hands = [
            ["Red 1", "Red 2"],
            ["Blue 3", "Blue 4"],
            ["Green 5"],
            ["Yellow 6"],
        ]
        self.server.game.discard_pile = ["Red 8"]
        self.server._broadcast_state()
        player_zero_state = self.server.clients[0].messages[-1]
        player_one_state = self.server.clients[1].messages[-1]
        self.assertIn("Red 1,Red 2 ; Uno Back,Uno Back", player_zero_state)
        self.assertIn("Uno Back,Uno Back ; Blue 3,Blue 4", player_one_state)

    def test_bot_worker_returns_turn_to_a_human(self):
        self.server.game.start()
        self.server.game.current_turn = 2
        self.server.bots = {2: StrategicBot(), 3: StrategicBot()}
        with patch("Server.Server.BOT_DELAY", 0):
            self.server.bot_worker_active = True
            self.server._run_bot_turns()
        self.assertIn(self.server.game.current_turn, (0, 1))


if __name__ == "__main__":
    unittest.main()
