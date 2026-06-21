import random
import unittest

from Server.bots import StrategicBot
from Server.game import UnoGame


class CompleteGameTests(unittest.TestCase):
    def test_twenty_complete_four_player_games(self):
        bot = StrategicBot()
        for seed in range(20):
            game = UnoGame(player_count=4, rng=random.Random(seed))
            game.start()
            turns = 0
            while game.started and turns < 2500:
                player_id = game.current_turn
                view = {
                    "hand": list(game.hands[player_id]),
                    "legal_cards": game.legal_cards(player_id),
                    "top_card": game.top_card,
                }
                decision = bot.decide(view)
                if decision.action == "play":
                    if len(game.hands[player_id]) == 2:
                        game.call_uno(player_id)
                    result = game.play_card(player_id, decision.card)
                    self.assertTrue(result.valid)
                    if result.needs_color:
                        result = game.choose_color(player_id, decision.color)
                        self.assertTrue(result.valid)
                else:
                    self.assertTrue(game.draw(player_id).valid)
                turns += 1
            self.assertFalse(game.started, f"seed {seed} did not finish")
            self.assertIsNotNone(game.winner)
            self.assertLess(turns, 2500)


if __name__ == "__main__":
    unittest.main()
