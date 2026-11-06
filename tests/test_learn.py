"""Learn mode tests (synthetic transcripts only; no network, no real AI).  Run:  python -m unittest tests.test_learn"""
import json, random, sqlite3, sys, time, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import learn, web  # noqa: E402
from tests.test_server import ServerTest  # noqa: E402

VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.100 --> 00:00:02.980
Today we study the <c.colorE5E5E5>atom</c> &amp; its parts.

00:00:02.980 --> 00:00:06.000
Protons have a positive charge.

1
00:01:05.500 --> 00:01:08.000
Neutrons have no charge at all.
Isotopes differ in neutrons.

01:02:03.250 --> 01:02:05.000
An hour in.
"""
ROLLING = """WEBVTT

00:00:00.000 --> 00:00:02.000
the mole is a counting unit

00:00:02.000 --> 00:00:04.000
the mole is a counting unit
it equals avogadro's number

00:00:04.000 --> 00:00:06.000
it equals avogadro's number
of particles
"""
SRT = """1
00:00:01,000 --> 00:00:03,500
Gases expand to fill their container.

2
00:00:03,500 --> 00:00:06,000
Pressure comes from collisions.
"""


def fake_llm(messages, max_tokens=None, temperature=0.3):
    sysmsg, user = messages[0]["content"], messages[-1]["content"]
    if sysmsg == learn.NOTES_SYS:
        return json.dumps({"summary": "The speaker explains protons and neutrons.",
                           "terms": [{"term": "proton", "definition": "a positive particle"}, {"term": "quasar flux", "definition": "invented, never said"}]})
    if sysmsg == learn.Q_SYS:
        return '```json\n{"questions": ["What charge does a proton have?", "What is an isotope?", "Q3?"]}\n```'
    if sysmsg == learn.CHECK_SYS:
        return json.dumps({"question": "What charge do protons have?", "answer": "Protons are positively charged."})
    if sysmsg == learn.GRADE_SYS:
        return json.dumps({"verdict": "correct" if "positive" in user.split("Student answer:")[1].lower() else "incorrect", "feedback": "Checked."})
    if sysmsg == learn.ASK_SYS:
        return "Protons are positive. [Ep 1 @ 0:02] Does that make sense?"
    return "?"


def mem():
    con = sqlite3.connect(":memory:")
    learn.init(con)
    return con


class Parsing(unittest.TestCase):
    def test_vtt(self):
        cues = learn.parse_captions(VTT)
        self.assertEqual(cues[0], (0.1, "Today we study the atom & its parts."))     # tags stripped, entity decoded
        self.assertEqual(cues[2][0], 65.5)
        self.assertEqual(cues[2][1], "Neutrons have no charge at all. Isotopes differ in neutrons.")  # numeric cue id ignored
        self.assertEqual(cues[3][0], 3723.25)                                          # hours supported

    def test_rolling_auto_captions_are_deduplicated(self):
        text = " ".join(t for _, t in learn.parse_captions(ROLLING))
        self.assertEqual(text, "the mole is a counting unit it equals avogadro's number of particles")

    def test_srt_and_plain(self):
        self.assertEqual(learn.parse_captions(SRT)[1], (3.5, "Pressure comes from collisions."))
        cues = learn.parse_plain("[0:05]\nFirst part.\n\n1:30 Second part.\nThird line.")
        self.assertEqual(cues, [(5.0, "First part."), (90.0, "Second part."), (90.0, "Third line.")])
        self.assertEqual(learn.parse_plain("just text with no times")[0][0], -1.0)
        self.assertEqual(learn.to_cues(SRT), learn.parse_captions(SRT))

    def test_chunking_and_clock(self):
        cues = [(i * 3.0, "word " * 10) for i in range(40)]
        ch = learn.chunk_cues(cues, target_words=55)
        self.assertTrue(all(len(t.split()) >= 50 for _, t in ch[:-1]))
        self.assertEqual(sum(len(t.split()) for _, t in ch), 400)
        self.assertEqual([learn.clock(x) for x in (0, 65, 3723, -1, None)], ["0:00", "1:05", "62:03", "", ""])


class Topics(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(learn.lesson_topics("The Ideal Gas Law", "pressure volume temperature the ideal gas law pv nrt pressure"), ["Gases"])
        self.assertIn("Moles & Stoichiometry", learn.lesson_topics("Stoichiometry", "the mole and molar mass, avogadro, limiting reagent, mole ratio"))
        self.assertIn("Acids & Bases", learn.lesson_topics("pH and pOH", "an acid donates, a base accepts; ph and poh; buffer"))
        self.assertEqual(learn.lesson_topics("Hello", "nothing relevant here at all"), [])
        self.assertLessEqual(len(learn.lesson_topics("Mixed", "acid base mole gas pressure enthalpy redox kinetics rate law " * 5)), 3)

    def test_title_outweighs_passing_mentions(self):
        t = learn.lesson_topics("Entropy", "a gas is mentioned once. entropy entropy gibbs free energy spontaneous")
        self.assertEqual(t[0], "Thermodynamics")

    def test_aliases_cover_every_problem_topic(self):
        known = {p["topic"] for p in web.load_problems().values()}
        covered = set(learn.expand_topics(learn.ALIASES))
        self.assertEqual(known - covered, set(), "a practice topic can never unlock")
        self.assertEqual(set(learn.KEYWORDS), set(learn.ALIASES))


class StoreAndSearch(unittest.TestCase):
    def setUp(self):
        self.con = mem()
        filler = " ".join(["word"] * 60)
        atoms = [(0.0, "Protons are positive. " + filler), (65.5, "Neutrons have no charge at all. Isotopes differ in neutrons. " + filler)]
        learn.store_video(self.con, "aaaaaaaaaaa", "Atoms: Crash Course Chemistry #1", atoms, ord_=1)
        learn.store_video(self.con, "bbbbbbbbbbb", "Gases: Crash Course Chemistry #2", learn.parse_captions(SRT), ord_=2)

    def test_search_and_stemming_and_citation(self):
        hits = learn.search(self.con, "What is a neutron?")
        self.assertEqual(hits[0]["video_id"], "aaaaaaaaaaa")
        self.assertEqual(learn.cite(hits[0]), "[Ep 1 @ 1:05]")                       # 'Neutrons' matches 'neutron'
        self.assertEqual(learn.search(self.con, "pressure collisions")[0]["video_id"], "bbbbbbbbbbb")
        self.assertEqual(learn.search(self.con, "the is of a"), [])                  # only stopwords
        self.assertEqual(learn.search(self.con, 'quote " and ) symbols'), [])         # never crashes on odd input

    def test_current_video_is_preferred(self):
        h = learn.search(self.con, "charge pressure", limit=4, video_id="bbbbbbbbbbb")
        self.assertEqual(h[0]["video_id"], "bbbbbbbbbbb")
        self.assertIn("aaaaaaaaaaa", [x["video_id"] for x in h])

    def test_restore_replaces_instead_of_duplicating(self):
        learn.store_video(self.con, "aaaaaaaaaaa", "Atoms #1", [(0.0, "Protons are positive. " + " ".join(["word"] * 60))], ord_=1)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM chunks WHERE video_id='aaaaaaaaaaa'").fetchone()[0],
                         self.con.execute("SELECT COUNT(*) FROM chunks_fts WHERE video_id='aaaaaaaaaaa'").fetchone()[0])

    def test_progress_and_unlocking(self):
        self.assertEqual(learn.covered_topics(self.con), [])
        learn.set_status(self.con, "bbbbbbbbbbb", "watched")
        self.assertEqual(learn.covered_topics(self.con), ["Gases"])
        learn.set_status(self.con, "bbbbbbbbbbb", "new")
        self.assertEqual(learn.covered_topics(self.con), [])
        with self.assertRaises(ValueError):
            learn.set_status(self.con, "bbbbbbbbbbb", "mastered")
        ov = learn.course_overview(self.con)
        self.assertEqual([v["ep"] for v in ov["videos"]], [1, 2])
        self.assertTrue(all(v["has_transcript"] for v in ov["videos"]))


class AiHelpers(unittest.TestCase):
    def test_extract_json_and_grounding(self):
        self.assertEqual(learn.extract_json('Sure! ```json\n{"a": [1, 2,],}\n``` thanks'), {"a": [1, 2]})
        self.assertIsNone(learn.extract_json("no json here"))
        self.assertTrue(learn.grounded("protons", "the proton has a charge"))
        self.assertFalse(learn.grounded("quasar flux", "the proton has a charge"))
        self.assertTrue(learn.grounded("pH", "the ph scale"))                       # short terms: plain substring

    def test_notes_drop_invented_terms_and_report_progress(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms", learn.parse_captions(VTT))
        seen = []
        n = learn.make_notes(con, "aaaaaaaaaaa", fake_llm, "fake", progress=lambda d, t, m: seen.append((d, t)))
        self.assertEqual([t["term"] for t in n["terms"]], ["proton"])                # 'quasar flux' was not in the transcript
        self.assertEqual(n["questions"][:2], ["What charge does a proton have?", "What is an isotope?"])
        self.assertTrue(n["timeline"] and n["timeline"][0]["text"].startswith("The speaker"))
        self.assertEqual(seen[-1][0], seen[-1][1] - 1)
        self.assertEqual(learn.video_detail(con, "aaaaaaaaaaa")["notes"]["terms"][0]["term"], "proton")   # saved

    def test_notes_survive_a_model_that_ignores_json(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms", learn.parse_captions(VTT))
        n = learn.make_notes(con, "aaaaaaaaaaa", lambda m, t, temp: "Plain prose, not JSON, about atoms.", "x")
        self.assertIn("Plain prose", n["timeline"][0]["text"])
        self.assertEqual((n["terms"], n["questions"]), ([], []))

    def test_notes_need_a_transcript(self):
        with self.assertRaises(ValueError):
            learn.make_notes(mem(), "nope", fake_llm)

    def test_check_and_grade_flow(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms", learn.parse_captions(VTT))
        c = learn.new_check(con, "aaaaaaaaaaa", fake_llm, random.Random(1))
        self.assertEqual(c["question"], "What charge do protons have?")
        self.assertNotIn("reference", c)                                              # the answer is not sent with the question
        good = learn.grade_check(con, c["check_id"], "They are positive", fake_llm)
        self.assertEqual(good["verdict"], "correct")
        self.assertIn("positively", good["reference"])
        c2 = learn.new_check(con, "aaaaaaaaaaa", fake_llm, random.Random(2))
        self.assertEqual(learn.grade_check(con, c2["check_id"], "no idea", fake_llm)["verdict"], "incorrect")
        self.assertEqual(len(learn.video_detail(con, "aaaaaaaaaaa")["checks"]), 2)
        with self.assertRaises(KeyError):
            learn.grade_check(con, 999, "x", fake_llm)

    def test_bad_model_output_is_handled(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms", learn.parse_captions(VTT))
        with self.assertRaises(ValueError):
            learn.new_check(con, "aaaaaaaaaaa", lambda m, t, temp: "garbage")
        c = learn.new_check(con, "aaaaaaaaaaa", fake_llm)
        r = learn.grade_check(con, c["check_id"], "x", lambda m, t, temp: "not json")
        self.assertEqual(r["verdict"], "unknown")

    def test_ask_puts_video_excerpts_and_sheet_in_the_prompt(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms: Crash Course Chemistry #1", learn.parse_captions(VTT), ord_=1)
        learn.store_video(con, "bbbbbbbbbbb", "Gases: Crash Course Chemistry #2", learn.parse_captions(SRT), ord_=2)
        seen = {}

        def spy(messages, max_tokens=None, temperature=0.3):
            seen["user"], seen["sys"] = messages[1]["content"], messages[0]["content"]
            return "ok"
        r = learn.ask(con, "How does the ideal gas law relate pressure and volume?", spy)
        self.assertIn("[Ep 2", seen["user"])
        self.assertIn("Ideal gas law: PV = nRT", seen["user"])                         # cheat-sheet formula supplied, not invented
        self.assertIn("beyond the videos", seen["sys"])
        self.assertEqual(r["sources"][0]["video_id"], "bbbbbbbbbbb")

    def test_off_topic_questions_are_declined_without_calling_the_model(self):
        con = mem()
        learn.store_video(con, "aaaaaaaaaaa", "Atoms: Crash Course Chemistry #1", learn.parse_captions(VTT), ord_=1)
        calls = []
        r = learn.ask(con, "How do I make a perfect souffle?", lambda m, t, temp: calls.append(1) or "x")
        self.assertEqual((r["reply"], r["sources"], calls), (learn.OFF_TOPIC, [], []))
        self.assertTrue(learn.on_topic("what is an isotope", []))
        self.assertTrue(learn.on_topic("why does ice float on water", []))              # chemistry words count even if no video covers them
        self.assertFalse(learn.on_topic("who won the football game", []))
        r = learn.ask(con, "what is an isotope", lambda m, t, temp: "An isotope has extra neutrons.")
        self.assertIn("isotope", r["reply"])

    def test_leading_citations_move_to_the_end_of_the_paragraph(self):
        out = learn.tidy_citations("[Ep 6 @ 5:00] A mole counts atoms.\n\nPlain paragraph.\n\n[Ep 6 @ 7:44]  Another point.")
        self.assertEqual(out, "A mole counts atoms. [Ep 6 @ 5:00]\n\nPlain paragraph.\n\nAnother point. [Ep 6 @ 7:44]")
        self.assertEqual(learn.tidy_citations("No citations here."), "No citations here.")


class ImportText(unittest.TestCase):
    def test_pasted_transcript(self):
        con = mem()
        r = learn.import_text(con, "My Lesson!", "[0:10]\nAcids donate protons.\n[0:30]\nBases accept protons. That is a base.")
        self.assertEqual(r["id"], "txt-my-lesson")
        self.assertIn("Acids & Bases", r["topics"])
        self.assertEqual(learn.search(con, "donate protons")[0]["t"], "0:10")
        with self.assertRaises(ValueError):
            learn.import_text(con, "x", "   ")


class YtDlpDetection(unittest.TestCase):
    def setUp(self):
        self.old = (learn._probe_ytdlp, dict(learn._yt_state))
        learn._yt_state.update(ok=False, t=0.0)

    def tearDown(self):
        learn._probe_ytdlp = self.old[0]
        learn._yt_state.update(self.old[1])

    def test_installed_while_the_app_is_running_is_noticed(self):
        answers, calls = [False, True], []
        learn._probe_ytdlp = lambda: calls.append(1) or answers[len(calls) - 1]
        self.assertFalse(learn.have_ytdlp())
        self.assertFalse(learn.have_ytdlp())
        self.assertEqual(len(calls), 1)                       # a "no" is only re-checked every few seconds
        learn._yt_state["t"] -= 10                            # a little time passes (the user clicked Install)
        self.assertTrue(learn.have_ytdlp())
        self.assertTrue(learn.have_ytdlp())
        self.assertEqual(len(calls), 2)                       # and a "yes" is remembered

    def test_probe_uses_a_fresh_interpreter_when_the_import_fails_here(self):
        import subprocess
        real_run = subprocess.run
        seen = {}

        def fake_run(cmd, *a, **k):
            seen["cmd"] = cmd
            return type("R", (), {"returncode": 0})()
        learn.importlib.util.find_spec, orig = (lambda name: None), learn.importlib.util.find_spec
        subprocess.run = fake_run
        try:
            self.assertTrue(learn._probe_ytdlp())
        finally:
            subprocess.run = real_run
            learn.importlib.util.find_spec = orig
        self.assertEqual(seen["cmd"][1:], ["-c", "import yt_dlp"])


class LearnServer(ServerTest):
    def setUp(self):
        self.real_llm = web.llm
        web.llm = fake_llm

    def tearDown(self):
        web.llm = self.real_llm

    def test_end_to_end_with_a_fake_model(self):
        s, r = self.call("/api/learn/import", {"title": "Atoms: Crash Course Chemistry #1", "text": VTT})
        self.assertEqual(s, 200)
        vid = r["id"]
        ov = self.call("/api/learn")[1]
        mine = [v for v in ov["videos"] if v["id"] == vid]
        self.assertEqual(len(mine), 1)
        self.assertEqual(ov["covered"], [])
        self.assertIn("Atoms, Molecules & Ions", ov["aliases"])
        # notes run as a background job the page polls
        s, j = self.call("/api/learn/notes", {"id": vid})
        for _ in range(100):
            job = self.call("/api/learn/job?id=" + j["job"])[1]
            if job["state"] != "running":
                break
            time.sleep(0.05)
        self.assertEqual(job["state"], "done", job)
        d = self.call("/api/learn/video?id=" + vid)[1]
        self.assertEqual(d["notes"]["terms"][0]["term"], "proton")
        self.assertGreaterEqual(len(d["transcript"]), 2)
        # check yourself, ask, unlock
        q = self.call("/api/learn/check", {"id": vid})[1]
        g = self.call("/api/learn/grade", {"check_id": q["check_id"], "answer": "positive"})[1]
        self.assertEqual(g["verdict"], "correct")
        a = self.call("/api/learn/ask", {"question": "what is a proton", "id": vid})[1]
        self.assertIn("Protons are positive", a["reply"])
        self.assertEqual(a["sources"][0]["video_id"], vid)
        st = self.call("/api/learn/status", {"id": vid, "status": "watched"})[1]
        self.assertIn("Atoms, Molecules & Ions", st["covered"])
        self.assertEqual(self.call("/api/learn/status", {"id": vid, "status": "bogus"})[0], 400)

    def test_add_requires_the_caption_tool_and_a_youtube_link(self):
        old = learn.have_ytdlp
        try:
            learn.have_ytdlp = lambda: False
            s, r = self.call("/api/learn/add", {"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"})
            self.assertEqual((s, r.get("need_ytdlp")), (424, True))
            learn.have_ytdlp = lambda: True
            self.assertEqual(self.call("/api/learn/add", {"url": "https://example.com/video"})[0], 400)
            self.assertEqual(self.call("/api/learn/ask", {"question": ""})[0], 400)
            self.assertEqual(self.call("/api/learn/notes", {"id": "missing"})[0], 404)
        finally:
            learn.have_ytdlp = old

    def test_ai_offline_is_a_clean_error(self):
        web.llm = self.real_llm                      # the real one cannot reach anything in tests
        vid = self.call("/api/learn/import", {"title": "Gases #2", "text": SRT})[1]["id"]
        s, r = self.call("/api/learn/ask", {"question": "what is pressure", "id": vid})
        self.assertEqual(s, 502)
        self.assertIn("unreachable", r["error"])

    def test_lessons_are_locked_during_a_mock_exam(self):
        vid = self.call("/api/learn/import", {"title": "Atoms #1", "text": VTT})[1]["id"]
        ex = self.call("/api/exam/start", {"n": 3, "minutes": 5})[1]["exam"]
        try:
            self.assertEqual(self.call("/api/learn/video?id=" + vid)[0], 423)
            self.assertEqual(self.call("/api/learn/ask", {"question": "proton", "id": vid})[0], 423)
            self.assertEqual(self.call("/api/learn/check", {"id": vid})[0], 423)
            self.assertEqual(self.call("/api/learn")[0], 200)                         # the course list itself is harmless
        finally:
            self.call("/api/exam/abandon", {"id": ex["id"]})
        self.assertEqual(self.call("/api/learn/video?id=" + vid)[0], 200)


if __name__ == "__main__":
    unittest.main()
