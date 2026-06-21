import unittest

from Server.bots import BotDecision, LlamaBot, StrategicBot


class BotTests(unittest.TestCase):
    def test_strategic_bot_draws_without_legal_card(self):
        decision = StrategicBot().decide(
            {"hand": ["Blue 1"], "legal_cards": [], "top_card": "Red 8"}
        )
        self.assertEqual(decision, BotDecision("draw"))

    def test_strategic_bot_returns_a_legal_card(self):
        view = {
            "hand": ["Red 2", "Red Draw", "Blue 8"],
            "legal_cards": ["Red 2", "Red Draw"],
            "top_card": "Red 8",
        }
        decision = StrategicBot().decide(view)
        self.assertEqual(decision.card, "Red Draw")

    def test_llama_validation_rejects_invented_card(self):
        view = {"legal_cards": ["Red 2"]}
        self.assertFalse(LlamaBot._is_legal(BotDecision("play", "Blue 9"), view))

    def test_llama_validation_requires_wild_color(self):
        view = {"legal_cards": ["Wild"]}
        self.assertFalse(LlamaBot._is_legal(BotDecision("play", "Wild"), view))
        self.assertTrue(LlamaBot._is_legal(BotDecision("play", "Wild", "Blue"), view))

    def test_llama_validation_ignores_extra_color_for_regular_card(self):
        view = {"legal_cards": ["Red 2"]}
        self.assertTrue(LlamaBot._is_legal(BotDecision("play", "Red 2", "Red"), view))


if __name__ == "__main__":
    unittest.main()
