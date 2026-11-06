"""AP free-response tests.  Run:  python -m unittest tests.test_frq"""
import json, math, sqlite3, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import frq, web  # noqa: E402

Q = frq.load()


class Structure(unittest.TestCase):
    def test_bank(self):
        self.assertGreaterEqual(len(Q), 10)
        for q in Q.values():
            self.assertEqual(q["points"], sum(p["points"] for p in q["parts"]), q["id"])
            labels = [p["label"] for p in q["parts"]]
            self.assertEqual(len(labels), len(set(labels)), q["id"])
            self.assertTrue(q["stem"].strip() and q["title"].strip())
            for p in q["parts"]:
                self.assertEqual(p["points"], sum(r["pts"] for r in p["rubric"]), f"{q['id']}{p['label']}")
                self.assertTrue(p["rubric"] and all(r["text"].strip() for r in p["rubric"]))
                if p["type"] == "numeric":
                    self.assertTrue(math.isfinite(p["answer"]) and p["solution"] and p["answer_text"])
                    self.assertTrue(any(r.get("auto") for r in p["rubric"]), f"{q['id']}{p['label']} has no auto item")
                else:
                    self.assertEqual(p["type"], "written")
                    self.assertTrue(p["model_answer"].strip())

    def test_ids_do_not_clash_with_practice_problems(self):
        self.assertTrue(set(Q).isdisjoint(web.load_problems()))


class Grading(unittest.TestCase):
    def test_every_numeric_answer_grades_correct_and_wrong_is_rejected(self):
        for q in Q.values():
            ans = {p["label"]: p["answer_text"] for p in q["parts"] if p["type"] == "numeric"}
            rev = frq.reveal(q, ans, web.check_answer)
            for part in rev["parts"]:
                if part["type"] == "numeric":
                    self.assertTrue(part["auto_correct"], f"{q['id']}{part['label']} rejects its own answer {part['your_answer']!r}")
                    self.assertTrue(any(r["preset"] for r in part["rubric"]))
            wrong = {p["label"]: f"{p['answer'] * 1.5 + 1:.6g}" for p in q["parts"] if p["type"] == "numeric"}
            for part in frq.reveal(q, wrong, web.check_answer)["parts"]:
                if part["type"] == "numeric":
                    self.assertFalse(part["auto_correct"], f"{q['id']}{part['label']} accepts a wrong answer")
                    self.assertFalse(any(r["preset"] for r in part["rubric"]))

    def test_blank_and_written_never_preset(self):
        q = Q["frq-01"]
        rev = frq.reveal(q, {}, web.check_answer)
        for part in rev["parts"]:
            self.assertFalse(part.get("auto_correct", False))
            self.assertFalse(any(r["preset"] for r in part["rubric"]))

    def test_score_counts_only_ticked_items_and_ignores_extras(self):
        q = Q["frq-01"]  # a:1  b:2  c:2  d:2  e:1
        self.assertEqual(frq.score(q, {})[0], 0)
        full = {p["label"]: [1] * len(p["rubric"]) for p in q["parts"]}
        self.assertEqual(frq.score(q, full)[:2], (q["points"], q["points"]))
        half = {"(b)": [1, 0], "(d)": [0, 1], "(c)": [1, 1, 1, 1, 1]}  # extra marks beyond the rubric are ignored
        self.assertEqual(frq.score(q, half)[0], 1 + 1 + 2)


class NoLeaks(unittest.TestCase):
    FORBIDDEN = {"rubric", "model_answer", "solution", "answer_text", "answer", "tolerance_rel", "tolerance_abs", "auto", "preset"}

    def keys(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from self.keys(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from self.keys(v)

    def test_public_view_has_no_answers(self):
        for q in Q.values():
            self.assertTrue(self.FORBIDDEN.isdisjoint(self.keys(frq.public(q))), f"{q['id']} leaks answer keys")

    def test_summary_has_no_answers(self):
        for q in Q.values():
            self.assertTrue(self.FORBIDDEN.isdisjoint(self.keys(frq.summary(q))))


class Storage(unittest.TestCase):
    def test_save_best_and_history(self):
        con = sqlite3.connect(":memory:")
        frq.init(con)
        q = Q["frq-02"]
        full = {p["label"]: [1] * len(p["rubric"]) for p in q["parts"]}
        r1 = frq.save(con, q, {"(a)": [1]}, {})
        r2 = frq.save(con, q, full, {"(a)": "2"})
        self.assertEqual((r1["score"], r2["score"], r2["max"]), (1, q["points"], q["points"]))
        self.assertEqual(frq.best_scores(con)["frq-02"], {"score": q["points"], "max": q["points"]})
        self.assertEqual([h["score"] for h in frq.history(con)], [q["points"], 1])

    def test_feedback_prompt_contains_rubric_and_student_text(self):
        q = Q["frq-03"]
        part = q["parts"][-1]
        msgs = frq.feedback_messages(q, part, "It shifts left because fewer moles of gas.")
        text = msgs[1]["content"]
        self.assertIn("It shifts left", text)
        self.assertIn(part["rubric"][0]["text"][:30], text)
        self.assertIn("Never invent", msgs[0]["content"])


class PlugBack(unittest.TestCase):
    def part(self, qid, label):
        return next(p for p in Q[qid]["parts"] if p["label"] == label)

    def test_kc_kp_ice(self):
        Kc = self.part("frq-03", "(b)")["answer"]
        self.assertAlmostEqual(Kc, 0.0140 ** 2 / 0.0420, delta=1e-5)
        self.assertAlmostEqual(self.part("frq-03", "(c)")["answer"], Kc * 0.08206 * 298.15, delta=2e-4)
        y = self.part("frq-03", "(d)")["answer"]  # [NO2] eq; plug into Kc = y^2/(0.200 - y/2)
        self.assertAlmostEqual(y * y / (0.200 - y / 2) / Kc, 1, delta=0.01)

    def test_weak_acid(self):
        Ka = self.part("frq-04", "(a)")["answer"]
        x = 10 ** -2.88
        self.assertAlmostEqual(Ka, x * x / (0.100 - x), delta=Ka * 0.001)
        pH = self.part("frq-04", "(c)")["answer"]  # buffer: 1.00 mmol HA, 1.50 mmol A-
        self.assertAlmostEqual(pH, -math.log10(Ka) + math.log10(1.5 / 1.0), delta=0.005)
        self.assertAlmostEqual(self.part("frq-04", "(f)")["answer"] * Ka, 1e-14, delta=1e-16)

    def test_thermo_and_electro(self):
        dG = self.part("frq-05", "(a)")["answer"]
        self.assertAlmostEqual(dG, -92.2 - 298 * (-0.1987), delta=0.01)
        K = self.part("frq-05", "(d)")["answer"]
        self.assertAlmostEqual(-8.314 * 298 * math.log(K) / 1000, dG, delta=0.05)
        self.assertAlmostEqual(self.part("frq-06", "(b)")["answer"], -2 * 96485 * 1.10 / 1000, delta=0.05)
        self.assertAlmostEqual(self.part("frq-06", "(d)")["answer"], 2.50 * 1800 / (2 * 96485) * 63.546, delta=0.005)

    def test_limiting_reagent_chain(self):
        nAl = self.part("frq-01", "(a)")["answer"]
        nCl = self.part("frq-01", "(b)")["answer"]
        self.assertLess(nAl * 1.5, nCl)  # Al really is limiting, as the rubric says
        mass = self.part("frq-01", "(d)")["answer"]
        self.assertAlmostEqual(mass, nAl * 133.332, delta=0.02)
        self.assertAlmostEqual(self.part("frq-01", "(e)")["answer"], 22.1 / mass * 100, delta=0.05)


if __name__ == "__main__":
    unittest.main()
