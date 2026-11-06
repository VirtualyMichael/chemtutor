"""End-to-end tests against a real server on a free port, with a throwaway database and no AI model.
Run:  python -m unittest tests.test_server
"""
import json, sys, tempfile, threading, unittest, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import library, web  # noqa: E402


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.old = (library.DB, web.LLM_URL)
        library.DB = Path(cls.tmp.name) / "test.sqlite3"           # never touch the real progress database
        web.LLM_URL = "http://127.0.0.1:9/v1"                        # nothing listens here: the AI model is "offline"
        web._llm_cache.update(t=0.0)
        cls.srv = web.make_server(0)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        library.DB, web.LLM_URL = cls.old
        web._llm_cache.update(t=0.0)
        cls.tmp.cleanup()

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)


class Basics(ServerTest):
    def test_health_config_and_data(self):
        s, h = self.call("/api/health")
        self.assertEqual((s, h["app"]), (200, "chemtutor"))
        s, c = self.call("/api/config")
        self.assertEqual(s, 200)
        self.assertFalse(c["llm_ok"])                       # offline model is reported, not a crash
        self.assertGreater(len(self.call("/api/problems")[1]), 300)
        self.assertEqual(len(self.call("/api/frq")[1]), 10)
        ref = self.call("/api/reference")[1]
        self.assertGreater(len(ref["sections"]), 10)
        self.assertEqual(len(ref["elements"]), 64)

    def test_index_page_is_served(self):
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn(b"ChemTutor", r.read())

    def test_check_progress_and_review(self):
        s, r = self.call("/api/check", {"id": "found-003", "answer": "2.7 g/cm^3"})
        self.assertTrue(r["correct"])
        self.assertEqual(r["srs"]["next_in"], "1 day")
        self.assertTrue(self.call("/api/status")[1]["found-003"]["solved"])
        self.assertFalse(self.call("/api/check", {"id": "found-003", "answer": "99"})[1]["correct"])
        self.assertIn("found-003", [h for h in [k for k in self.call("/api/status")[1]]])

    def test_tutor_reports_offline_model_cleanly(self):
        s, r = self.call("/api/tutor", {"id": "found-003", "mode": "solution"})
        self.assertEqual(s, 502)
        self.assertIn("unreachable", r["error"])

    def test_unknown_problem_and_path(self):
        self.assertEqual(self.call("/api/check", {"id": "nope", "answer": "1"})[0], 404)
        self.assertEqual(self.call("/api/nothing")[0], 404)


class FreeResponse(ServerTest):
    def test_flow_and_no_leaks_before_reveal(self):
        s, q = self.call("/api/frq/item?id=frq-01")
        self.assertEqual(s, 200)
        text = json.dumps(q)
        for secret in ("rubric", "model_answer", "answer_text"):
            self.assertNotIn(secret, text)
        s, rev = self.call("/api/frq/reveal", {"id": "frq-01", "answers": {"(a)": "0.200 mol", "(b)": "0.368 mol", "(d)": "26.7 g"}})
        by = {p["label"]: p for p in rev["parts"]}
        self.assertTrue(by["(a)"]["auto_correct"] and by["(b)"]["auto_correct"] and by["(d)"]["auto_correct"])
        self.assertFalse(by["(e)"]["auto_correct"])                     # blank
        self.assertIn("model_answer", by["(c)"])                         # written part shows its model answer
        s, saved = self.call("/api/frq/save", {"id": "frq-01", "scores": {"(a)": [1], "(b)": [1, 1], "(c)": [1, 1]}, "answers": {}})
        self.assertEqual((saved["score"], saved["max"]), (5, 8))
        self.assertEqual(self.call("/api/frq")[1][0]["best"], {"score": 5, "max": 8})
        self.assertEqual(self.call("/api/frq/history")[1][0]["score"], 5)

    def test_feedback_with_model_offline_is_a_clean_error(self):
        s, r = self.call("/api/frq/feedback", {"id": "frq-03", "label": "(e)", "answers": {"(e)": "shifts left"}})
        self.assertEqual(s, 502)


class ExamLocking(ServerTest):
    def test_closed_book_while_exam_runs(self):
        s, r = self.call("/api/exam/start", {"n": 3, "minutes": 5, "sheet": False})
        ex = r["exam"]
        self.assertEqual((s, len(ex["problems"]), ex["sheet"]), (200, 3, False))
        pid = ex["problems"][0]["id"]
        self.assertEqual(self.call("/api/tutor", {"id": pid, "mode": "hint", "level": 1})[0], 423)
        self.assertEqual(self.call("/api/check", {"id": pid, "answer": "1"})[0], 423)
        self.assertEqual(self.call("/api/frq/reveal", {"id": "frq-01", "answers": {}})[0], 423)
        self.assertEqual(self.call("/api/exam/start", {"n": 3})[0], 409)          # one exam at a time
        self.call("/api/exam/save", {"id": ex["id"], "answers": {pid: "42"}})
        self.assertEqual(self.call("/api/exam/active")[1]["exam"]["answers"], {pid: "42"})   # survives a reload
        s, done = self.call("/api/exam/submit", {"id": ex["id"], "answers": {pid: "42"}})
        self.assertEqual(done["result"]["total"], 3)
        self.assertEqual(self.call("/api/frq/reveal", {"id": "frq-01", "answers": {}})[0], 200)   # unlocked again
        self.assertEqual(self.call("/api/check", {"id": pid, "answer": "1"})[0], 200)


if __name__ == "__main__":
    unittest.main()
