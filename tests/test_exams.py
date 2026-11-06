"""Mock-exam logic tests (in-memory DB, no model).  Run:  python -m unittest tests.test_exams"""
import random, sqlite3, sys, unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import exams, srs, web  # noqa: E402

P = web.load_problems()


def mem():
    con = sqlite3.connect(":memory:")
    exams.init(con)
    return con


class Pick(unittest.TestCase):
    def test_count_topics_and_order(self):
        ids = exams.pick(P, set(), set(), ["Gases", "Moles & Stoichiometry"], 8, "all", random.Random(1))
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)
        self.assertTrue(all(P[i]["topic"] in ("Gases", "Moles & Stoichiometry") for i in ids))
        levels = [P[i]["level"] for i in ids]
        self.assertEqual(levels, sorted(levels))  # easy -> hard

    def test_spread_across_topics(self):
        ids = exams.pick(P, set(), set(), [], 6, "all", random.Random(2))
        self.assertGreaterEqual(len({P[i]["topic"] for i in ids}), 4)

    def test_pools(self):
        solved = set(list(P)[:30])
        ids = exams.pick(P, solved, set(), [], 30, "unsolved", random.Random(3))
        self.assertTrue(solved.isdisjoint(ids))
        missed = {"mole-004", "gas-001"}
        self.assertEqual(set(exams.pick(P, set(), missed, [], 10, "missed")), missed)
        self.assertEqual(exams.pick(P, set(), set(), ["No Such Topic"], 5, "all"), [])


class Grade(unittest.TestCase):
    def test_grading_blank_wrong_right(self):
        ids = ["mole-004", "found-002", "gas-001"]
        g = exams.grade(P, ids, {"mole-004": "35.7 g", "found-002": "99", "gas-001": "  "}, web.check_answer)
        self.assertEqual([i["correct"] for i in g["items"]], [True, False, False])
        self.assertEqual((g["score"], g["total"]), (1, 3))


class Lifecycle(unittest.TestCase):
    def test_active_expiry_and_history(self):
        con = mem()
        eid = exams.start(con, ["mole-004", "gas-001"], 600, ["Gases"])
        ex = exams.current(con)
        self.assertEqual(ex["id"], eid)
        self.assertFalse(ex["expired"])
        self.assertTrue(0 < exams.remaining_s(ex) <= 600)
        # autosave persists
        exams.save_answers(con, eid, {"mole-004": "35.7"})
        self.assertEqual(exams.current(con)["answers"], {"mole-004": "35.7"})
        # push the start time into the past beyond limit + grace -> expired
        con.execute("UPDATE exams SET started=? WHERE id=?",
                    ((srs.utcnow() - timedelta(seconds=600 + exams.GRACE_S + 5)).isoformat(), eid))
        self.assertTrue(exams.current(con)["expired"])
        # within grace is NOT yet expired
        con.execute("UPDATE exams SET started=? WHERE id=?",
                    ((srs.utcnow() - timedelta(seconds=600 + 5)).isoformat(), eid))
        self.assertFalse(exams.current(con)["expired"])
        g = exams.grade(P, ["mole-004", "gas-001"], {"mole-004": "35.7"}, web.check_answer)
        exams.finish(con, eid, g, 600, "expired")
        self.assertIsNone(exams.current(con))
        h = exams.history(con)
        self.assertEqual((h[0]["score"], h[0]["total"], h[0]["status"]), (1, 2, "expired"))
        self.assertEqual([i["correct"] for i in exams.items(con, eid)], [True, False])

    def test_abandoned_not_in_history_and_unlocks(self):
        con = mem()
        eid = exams.start(con, ["gas-001"], 60, [])
        exams.abandon(con, eid)
        self.assertIsNone(exams.current(con))
        self.assertEqual(exams.history(con), [])

    def test_save_ignored_after_finish(self):
        con = mem()
        eid = exams.start(con, ["gas-001"], 60, [])
        exams.finish(con, eid, exams.grade(P, ["gas-001"], {}, web.check_answer), 5, "done")
        exams.save_answers(con, eid, {"gas-001": "1"})
        self.assertEqual(exams.get(con, eid)["answers"], {})


if __name__ == "__main__":
    unittest.main()
