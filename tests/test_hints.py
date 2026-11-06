"""Leak-detector tests (no model needed).  Run:  python -m unittest tests.test_hints"""
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import hints, web  # noqa: E402

P = web.load_problems()


class LeakDetector(unittest.TestCase):
    def leaks(self, pid, level, reply):
        return hints.leak_reason(reply, P[pid], level) is not None

    def test_blocks_final_answer(self):
        self.assertTrue(self.leaks("mole-004", 4, "So you get 35.7 g of water."))
        self.assertTrue(self.leaks("mole-004", 3, "That comes to 35.74 g."))
        self.assertTrue(self.leaks("mole-004", 1, "The answer is about thirty-five grams."))
        self.assertTrue(self.leaks("found-002", 4, "That equals 20.0 m/s."))
        self.assertTrue(self.leaks("ox-10-079", 1, "Cobalt hcp has coordination number = 12."))

    def test_early_levels_block_new_numbers(self):
        self.assertTrue(self.leaks("mole-004", 1, "First find moles: 4.00/2.016 = 1.984 mol."))
        self.assertTrue(self.leaks("mole-004", 2, "Use ratio 0.5 to scale."))

    def test_allows_good_hints(self):
        self.assertFalse(self.leaks("mole-004", 3, "Use 1.984 mol as your starting amount."))
        self.assertFalse(self.leaks("mole-004", 1, "You are finding how much water forms. What are you given?"))
        self.assertFalse(self.leaks("mole-004", 2, "Think moles = mass / molar mass, using 4.00 g and 2.016 g/mol."))
        self.assertFalse(self.leaks("mole-004", 1, "Look at H2O and O2 in 2 H2 + O2 -> 2 H2O."))
        self.assertFalse(self.leaks("ox-10-079", 1, "How many neighbors touch one atom in a closest-packed layer?"))
        self.assertFalse(self.leaks("found-002", 3, "Convert 72.0 km/h using 1000 m per km."))

    def test_fallback_when_model_keeps_leaking(self):
        r = hints.generate(P["mole-004"], 2, lambda m, t, temp: "The answer is 35.7 g.")
        self.assertTrue(r["fallback"])
        self.assertEqual(r["reply"], hints.SAFE[2])
        self.assertEqual(len(r["rejected"]), 3)

    def test_retry_recovers(self):
        replies = iter(["It is 35.7 g.", "Think about moles = mass / molar mass."])
        r = hints.generate(P["mole-004"], 2, lambda m, t, temp: next(replies))
        self.assertFalse(r["fallback"])
        self.assertEqual(len(r["rejected"]), 1)


if __name__ == "__main__":
    unittest.main()
