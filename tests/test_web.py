import unittest

from fastapi.testclient import TestClient

from Server.bots import StrategicBot
from Web.app import app
from Web.rooms import GameRoom


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_home_page(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Create a room", page.text)

    def test_rejects_invalid_room_size(self):
        response = self.client.post("/api/rooms", json={"humanSeats": 4, "botSeats": 2})
        self.assertEqual(response.status_code, 422)

    def test_two_humans_can_start_a_room(self):
        response = self.client.post("/api/rooms", json={"humanSeats": 2, "botSeats": 2})
        code = response.json()["code"]

        with self.client.websocket_connect(f"/ws/{code}?name=Ankit") as first:
            first_welcome = first.receive_json()
            self.assertEqual(first_welcome["type"], "welcome")
            first.receive_json()  # Initial lobby state.

            with self.client.websocket_connect(f"/ws/{code}?name=Kisu") as second:
                self.assertEqual(second.receive_json()["type"], "welcome")
                second.receive_json()
                first.receive_json()  # Second player joined.

                first.send_json({"action": "ready"})
                self.assertEqual(first.receive_json()["phase"], "lobby")
                self.assertEqual(second.receive_json()["phase"], "lobby")

                second.send_json({"action": "ready"})
                first_state = first.receive_json()
                second_state = second.receive_json()
                self.assertEqual(first_state["phase"], "game")
                self.assertEqual(second_state["phase"], "game")
                self.assertEqual(len(first_state["hand"]), 7)
                self.assertEqual(len(second_state["hand"]), 7)
                self.assertNotEqual(first_state["hand"], second_state["hand"])


class RoomBotFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_turn_cycles_through_three_bots_to_human(self):
        room = GameRoom("BOTS", human_seats=1, bot_seats=3)
        room.bots = {player_id: StrategicBot() for player_id in room.bots}
        websocket = FakeWebSocket()
        player = await room.connect(websocket, "Ankit", None)
        await room.handle_action(player.player_id, {"action": "ready"})
        await room.handle_action(player.player_id, {"action": "draw"})
        await room.bot_task
        self.assertTrue(room.game.started)
        self.assertEqual(room.game.current_turn, player.player_id)
        self.assertGreater(len(websocket.messages), 5)
        self.assertTrue(all("hand" in message for message in websocket.messages if message["type"] == "state"))


if __name__ == "__main__":
    unittest.main()
