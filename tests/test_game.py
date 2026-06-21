import random
import unittest

from Server.game import COLORS, UnoGame, build_deck


class UnoGameTests(unittest.TestCase):
    def setUp(self):
        self.game = UnoGame(rng=random.Random(7))
        self.game.start()

    def test_standard_deck_and_deal(self):
        self.assertEqual(len(build_deck()), 108)
        self.assertEqual([len(hand) for hand in self.game.hands], [7, 7, 7, 7])
        self.assertNotIn(self.game.top_card, ("Wild", "Draw 4"))

    def test_rejects_out_of_turn_player(self):
        result = self.game.draw(1)
        self.assertFalse(result.valid)
        self.assertEqual(self.game.current_turn, 0)

    def test_normal_play_advances_turn(self):
        self.game.hands[0] = ["Red 3", "Blue 5"]
        self.game.discard_pile = ["Red 8"]
        result = self.game.play_card(0, "Red 3")
        self.assertTrue(result.valid)
        self.assertEqual(self.game.current_turn, 1)

    def test_missing_uno_call_draws_penalty(self):
        self.game.hands[0] = ["Red 3", "Blue 5"]
        self.game.discard_pile = ["Red 8"]
        result = self.game.play_card(0, "Red 3")
        self.assertEqual(len(result.drawn_cards[0]), 2)
        self.assertEqual(len(self.game.hands[0]), 3)

    def test_uno_call_avoids_penalty(self):
        self.game.hands[0] = ["Red 3", "Blue 5"]
        self.game.discard_pile = ["Red 8"]
        self.assertTrue(self.game.call_uno(0).valid)
        result = self.game.play_card(0, "Red 3")
        self.assertNotIn(0, result.drawn_cards)
        self.assertEqual(self.game.hands[0], ["Blue 5"])

    def test_draw_four_waits_for_color_then_skips_target(self):
        self.game.hands[0] = ["Draw 4", "Blue 5", "Green 2"]
        self.game.discard_pile = ["Red 8"]
        result = self.game.play_card(0, "Draw 4")
        self.assertTrue(result.needs_color)
        self.assertEqual(self.game.current_turn, 0)
        result = self.game.choose_color(0, "Blue")
        self.assertEqual(len(result.drawn_cards[1]), 4)
        self.assertEqual(self.game.top_card, "Blue Plus")
        self.assertEqual(self.game.current_turn, 2)

    def test_private_hands_are_hidden(self):
        hands = self.game.public_hands_for(0)
        self.assertEqual(hands[0], self.game.hands[0])
        self.assertEqual(hands[1], ["Uno Back"] * 7)

    def test_colors_are_stable(self):
        self.assertEqual(COLORS, ("Red", "Yellow", "Green", "Blue"))


if __name__ == "__main__":
    unittest.main()
