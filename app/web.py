"""Chemistry study web app: problems, code-based answer checking, local-LLM tutor, progress.

Stdlib only. Run:  python -m app.web   then open http://127.0.0.1:8765
LLM: Ollama or LM Studio (any OpenAI-compatible endpoint); detected automatically, or choose from the model badge.
"""
from __future__ import annotations
import json, math, os, re, sqlite3, sys, threading, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import time

from . import __version__, aiconfig, exams, frq, hints, learn, library, reference, remote, srs

ROOT = Path(__file__).resolve().parents[1]
PROBLEMS_DIR = ROOT / "data" / "problems"
WEB_DIR = ROOT / "web"
LLM_URL = aiconfig.resolve_url(os.environ.get("LLM_URL", aiconfig.BACKENDS[0][1]))
LLM_MODEL = os.environ.get("LLM_MODEL", aiconfig.DEFAULT_MODEL)
PORT = int(os.environ.get("PORT", "8765"))
_auto = "off"  # "all": detect Ollama and LM Studio; "url": only the configured server; "off": settings are exact (see init_llm)


_llm_cache: dict = {"t": 0.0, "v": (False, False, [])}


def init_llm() -> None:
    """Pick the AI server and model at startup (called by the launcher, not by the tests)."""
    global LLM_URL, LLM_MODEL, _auto
    url_set, model_set = "LLM_URL" in os.environ, "LLM_MODEL" in os.environ
    saved = aiconfig.load()
    if not url_set and saved.get("url") and saved.get("model") and not model_set:
        LLM_URL, LLM_MODEL = saved["url"], saved["model"]
    _auto = "off" if model_set else ("url" if url_set else "all")
    _llm_cache["t"] = 0.0
    if _auto != "off":
        auto_select()


def auto_select() -> None:
    """If the configured model is not available, switch to one that is (default model first, else the largest chat model)."""
    global LLM_URL, LLM_MODEL
    found = aiconfig.detect(LLM_URL)
    if _auto == "url":
        found = [b for b in found if b["url"].rstrip("/") == LLM_URL.rstrip("/")]
    cur = next((b for b in found if b["url"].rstrip("/") == LLM_URL.rstrip("/")), None)
    if cur and cur["up"] and aiconfig.has_model(LLM_MODEL, cur["models"]):
        return
    pick = aiconfig.auto_pick(found, LLM_MODEL, LLM_URL)
    if pick:
        LLM_URL, LLM_MODEL = pick
        _llm_cache["t"] = 0.0


def llm_status(force: bool = False):
    """(reachable, configured model installed, model names). Cached for a few seconds."""
    now = time.time()
    if not force and now - _llm_cache["t"] < 5:
        return _llm_cache["v"]
    names = aiconfig.list_models(LLM_URL, 1.0)
    ok = (False, False, []) if names is None else (True, aiconfig.has_model(LLM_MODEL, names), names)
    _llm_cache.update(t=now, v=ok)
    if not ok[1] and _auto != "off":
        before = (LLM_URL, LLM_MODEL)
        auto_select()
        if (LLM_URL, LLM_MODEL) != before:
            return llm_status(True)
    return ok


def load_problems() -> dict[str, dict]:
    out = {}
    for f in sorted(PROBLEMS_DIR.glob("*.json")):
        for p in json.loads(f.read_text(encoding="utf-8")):
            out[p["id"]] = p
    return out


def db():
    con = library.connect()
    con.execute("""CREATE TABLE IF NOT EXISTS attempts(
        id INTEGER PRIMARY KEY, problem_id TEXT, topic TEXT, correct INTEGER,
        hints_used INTEGER, answer TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP)""")
    srs.init(con)
    exams.init(con)
    frq.init(con)
    learn.init(con)
    return con


# ---------- answer checking (code decides correctness, never the LLM) ----------
NUM = re.compile(r"[-+]?\d*\.?\d+(?:\s*(?:[eE]|x\s*10\^?|\*\s*10\^?)\s*[-+]?\d+)?")


def parse_number(text: str):
    text = text.replace("×", "x").replace("−", "-").replace("–", "-")  # typed multiplication / minus signs
    m = NUM.search(text.replace(",", ""))
    if not m:
        return None, text
    raw = m.group(0)
    norm = re.sub(r"\s*(x|\*)\s*10\^?", "e", raw).replace(" ", "")
    try:
        val = float(norm)
    except ValueError:
        return None, text
    return val, (text[:m.start()] + text[m.end():]).strip()


def check_answer(problem: dict, text: str) -> dict:
    val, rest = parse_number(text)
    if val is None:
        return {"correct": False, "message": "I couldn't find a number in your answer."}
    key = problem["answer"]
    tol = max(problem.get("tolerance_abs", 0), abs(key) * problem.get("tolerance_rel", 0))
    if not math.isclose(val, key, abs_tol=tol, rel_tol=0):
        return {"correct": False, "message": "Not quite. Check your setup and arithmetic."}
    units = [u.lower().replace(" ", "") for u in problem.get("units", [])]
    given = rest.lower().replace(" ", "").replace("**", "^")
    if units and given and not any(u in given or given in u for u in units):
        return {"correct": False, "message": f"The number matches, but check your units (expected {problem['units'][0]})."}
    if units and not given:
        return {"correct": True, "message": f"Correct! (Remember to write units: {problem['units'][0]}.)"}
    return {"correct": True, "message": "Correct!"}


# ---------- tutor ----------
BASE = ("You are a patient chemistry tutor for a self-taught beginner. Be concise. Show units. "
        "Use plain text math only (no LaTeX, no \\( \\) or \\text). Never invent facts; if unsure, say so.")


def llm(messages: list[dict], max_tokens: int | None = None, temperature: float = 0.3) -> str:
    budget = max_tokens
    # LM Studio: skip the long "thinking" phase of reasoning models. A tutor hint does not need it, and it can
    # turn a 4 second reply into 2 minutes. Servers/models that do not know the setting ignore it (or we retry without).
    quick = aiconfig.backend_name(LLM_URL) == "LM Studio"
    for attempt in (1, 2):
        payload = {"model": LLM_MODEL, "messages": messages, "temperature": temperature}
        if budget:
            payload["max_tokens"] = budget
        while True:
            if quick:
                payload["reasoning_effort"] = "none"
            req = urllib.request.Request(LLM_URL.rstrip("/") + "/chat/completions", json.dumps(payload).encode(),
                                         {"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    choice = json.load(r)["choices"][0]
                break
            except urllib.error.HTTPError as e:
                if quick and e.code in (400, 422):
                    quick = False
                    payload.pop("reasoning_effort", None)
                    continue
                raise
        text = choice["message"].get("content") or ""
        # reasoning models (DeepSeek-R1, Qwen3, Gemma...) think first; some servers inline it in <think> tags
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).replace("</think>", "").strip()
        if text or attempt == 2 or not budget or choice.get("finish_reason") != "length":
            return text
        budget = budget * 4 + 1500  # the thinking used up the whole budget: give the answer room and ask again
    return ""


def final_answer(p: dict) -> str:
    return p.get("answer_text") or f"{p['answer']} {', '.join(p.get('units', [])[:1])}".strip()


def build_tutor_messages(p: dict, mode: str, level: int, user_text: str, history: list[dict]):
    steps = p.get("steps", [])
    q = f"Problem: {p['question']}"
    # (hints are handled by app/hints.py, which enforces the no-leak rules in code)
    if not steps and mode in ("solution", "check"):
        # Imported problems have only a final answer: the model derives the steps, but must land on the key.
        if mode == "check":
            sys = (BASE + f" The official final answer is {final_answer(p)}. Compare it to the student's work, "
                   "identify the specific error or confirm the approach, and address THEIR work."
                   + " If the student gave only a final answer with no working, do NOT invent or guess what steps they took; say that you can't see their method, name the most common mistake only if the value makes it clear, then show the correct method briefly.")
            ctx = f"{q}\nStudent's work:\n{user_text}"
        else:
            sys = (BASE + f" The official final answer is {final_answer(p)}. Work the solution step by step, "
                   "explaining why each step is done, and make sure your calculation lands on that answer. "
                   "If it does not, say your steps disagree with the official answer instead of forcing it.")
            ctx = q
        return [{"role": "system", "content": sys}] + history[-6:] + [{"role": "user", "content": ctx}]
    if mode == "check":
        sys = (BASE + " The student's work may contain a mistake. Using the official solution, identify the "
               "specific error (or confirm the approach is right) and explain it. Do not just restate the "
               "solution; address THEIR work." + " If the student gave only a final answer with no working, do NOT invent or guess what steps they took; say that you can't see their method, name the most common mistake only if the value makes it clear, then show the correct method briefly.")
        ctx = (f"{q}\nOfficial final answer: {p['answer']} {', '.join(p.get('units', [])[:1])}\n"
               "Official steps:\n" + "\n".join(f"- {s}" for s in steps) + f"\nStudent's work:\n{user_text}")
    elif mode == "solution":
        sys = BASE + " Explain the official solution step by step so a beginner understands WHY each step is done."
        ctx = (f"{q}\nOfficial steps:\n" + "\n".join(f"- {s}" for s in steps) +
               f"\nFinal answer: {p['answer']} {', '.join(p.get('units', [])[:1])}")
    else:  # explain concept, grounded in the local textbook
        hits = library.search(f"{p['topic']} {p['question']}"[:200], limit=2)
        excerpts = "\n\n".join(f"[{h['title']}, p. {h['page']}]\n{h['text'][:1500]}" for h in hits)
        sys = (BASE + " Explain the underlying concept with a simple analogy, then a tiny example. "
               "If textbook excerpts are provided, cite them as (title, p. N).")
        ctx = f"{q}\nTextbook excerpts:\n{excerpts or '(none found)'}"
    msgs = [{"role": "system", "content": sys}] + history[-6:] + [{"role": "user", "content": ctx}]
    return msgs


# ---------- mock exams ----------
LOCKED = {"error": "Locked: a mock exam is in progress. Finish or abandon it first (closed-book).", "locked": True}

JOBS: dict = {}  # background work (fetching captions, writing notes) the page polls


def start_job(fn) -> str:
    jid = f"j{int(time.time() * 1000)}"
    job = JOBS[jid] = {"id": jid, "state": "running", "done": 0, "total": 1, "message": "Starting…", "result": None}
    for old in list(JOBS)[:-30]:
        JOBS.pop(old, None)

    def progress(done, total, message):
        job.update(done=done, total=max(total, 1), message=message)

    def run():
        try:
            job["result"] = fn(progress)
            job.update(state="done", done=job["total"], message="Done")
        except Exception as e:  # noqa: BLE001
            job.update(state="error", message=str(e)[:300])

    threading.Thread(target=run, daemon=True).start()
    return jid


def record_attempt(con, p: dict, correct: bool, hints_used: int, answer: str):
    con.execute("INSERT INTO attempts(problem_id,topic,correct,hints_used,answer) VALUES(?,?,?,?,?)",
                (p["id"], p["topic"], int(correct), hints_used, answer))
    con.commit()
    return srs.record(con, p["id"], correct, hints_used)


def exam_payload(ex: dict, problems: dict) -> dict:
    return {"id": ex["id"], "limit_s": ex["limit_s"], "remaining_s": max(0, exams.remaining_s(ex)),
            "answers": ex["answers"], "sheet": ex["sheet"],
            "problems": [{k: problems[i][k] for k in ("id", "topic", "level", "question")}
                         for i in ex["ids"] if i in problems]}


def exam_results(con, exam_id: int, problems: dict) -> dict | None:
    ex = exams.get(con, exam_id)
    if not ex or ex["status"] == "active":
        return None
    items, by_topic = [], {}
    for it in exams.items(con, exam_id):
        p = problems.get(it["id"])
        if not p:
            continue
        r = by_topic.setdefault(p["topic"], [0, 0])
        r[0] += it["correct"]
        r[1] += 1
        items.append({**it, "topic": p["topic"], "level": p["level"], "question": p["question"],
                      "key": final_answer(p), "steps": p.get("steps", []), "source": p.get("source", "")})
    return {"id": exam_id, "status": ex["status"], "score": ex["score"], "total": ex["total"],
            "elapsed_s": ex["elapsed_s"], "limit_s": ex["limit_s"], "date": ex["started"].isoformat(),
            "by_topic": by_topic, "items": items}


def finalize(con, ex: dict, answers: dict, problems: dict, status: str) -> dict:
    graded = exams.grade(problems, [i for i in ex["ids"] if i in problems], answers, check_answer)
    elapsed = int((srs.utcnow() - ex["started"]).total_seconds())
    exams.finish(con, ex["id"], graded, min(elapsed, ex["limit_s"]) if status == "expired" else elapsed, status)
    for it in graded["items"]:  # feed results into progress + spaced repetition (as unaided attempts)
        record_attempt(con, problems[it["id"]], it["correct"], 0, it["answer"])
    return exam_results(con, ex["id"], problems)


def active_exam(con, problems: dict):
    """The running exam, or None. An exam past its deadline is graded from its autosaved answers first."""
    ex = exams.current(con)
    if ex and ex["expired"]:
        finalize(con, ex, ex["answers"], problems, "expired")
        return None
    return ex


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def _is_local(self) -> bool:
        """Browser on this computer (not a paired phone): only it may change which AI server is used."""
        return (not getattr(self.server, "remote", False)) or remote.is_local_request(self.client_address[0], self.headers)

    def _ai_select(self, body):
        global LLM_URL, LLM_MODEL, _auto
        if not self._is_local():
            return self._json({"error": "Choose the AI model on the computer running ChemTutor."}, 403)
        if body.get("auto"):
            aiconfig.forget()
            _auto = "all"
            auto_select()
            return self._json({"url": LLM_URL, "model": LLM_MODEL})
        url, model = aiconfig.resolve_url(str(body.get("url", ""))), str(body.get("model", "")).strip()
        known = [b["url"].rstrip("/") for b in aiconfig.detect(LLM_URL)]
        if url.rstrip("/") not in known or not model:
            return self._json({"error": "Pick one of the detected servers and a model."}, 400)
        names = aiconfig.list_models(url, 2.0)
        if names is None or model not in names:
            return self._json({"error": "That model is not offered by that server right now."}, 400)
        LLM_URL, LLM_MODEL, _auto = url, model, "off"
        aiconfig.save(url, model)
        _llm_cache["t"] = 0.0
        return self._json({"url": LLM_URL, "model": LLM_MODEL})

    def _gate(self, query_key: str = "") -> bool:
        """Phone access. True means the request was answered (blocked or redirected) and must stop here."""
        if not getattr(self.server, "remote", False):
            return False
        path = self.path.split("?")[0]
        if remote.is_public(path) or remote.is_local_request(self.client_address[0], self.headers):
            return False
        if query_key and self.command == "GET" and remote.has_key(self.headers, query_key):
            self.send_response(302)  # pairing link: remember this phone, then drop the key from the address bar
            secure = "; Secure" if (self.headers.get("X-Forwarded-Proto") or "").lower() == "https" else ""
            self.send_header("Set-Cookie", f"{remote.COOKIE}={remote.token()}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax{secure}")
            self.send_header("Location", path or "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True
        if remote.has_key(self.headers, ""):
            return False
        if path.startswith("/api/"):
            self._json({"error": "This device is not paired. Open the pairing link from ChemTutor on your computer."}, 401)
        else:
            page = (b"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>ChemTutor</title>"
                    b"<body style='font:16px system-ui;max-width:30em;margin:12vh auto;padding:0 20px'>"
                    b"<h2>This phone is not paired yet</h2><p>On your computer run <code>python chemtutor.py phone</code> "
                    b"and open the link it prints on this phone.</p>")
            self.send_response(401)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        return True

    def do_GET(self):
        path = self.path.split("?")[0]
        if self._gate((parse_qs(urlparse(self.path).query).get("key") or [""])[0]):
            return
        problems = load_problems()
        if path == "/api/problems":
            return self._json([{k: p[k] for k in ("id", "topic", "level", "question", "source")}
                               for p in problems.values()])
        if path == "/api/progress":
            rows = db().execute("""SELECT topic, COUNT(*) n, SUM(correct) right_n
                                   FROM attempts GROUP BY topic""").fetchall()
            return self._json([{"topic": r[0], "attempts": r[1], "correct": r[2] or 0} for r in rows])
        if path == "/api/status":
            rows = db().execute("""SELECT problem_id, MAX(correct), COUNT(*)
                                   FROM attempts GROUP BY problem_id""").fetchall()
            return self._json({r[0]: {"solved": bool(r[1]), "attempts": r[2]} for r in rows})
        if path == "/api/review":
            ov = srs.overview(db())
            ov["due"] = [i for i in ov["due"] if i in problems]
            return self._json(ov)
        if path == "/api/exam/active":
            ex = active_exam(db(), problems)
            return self._json({"exam": exam_payload(ex, problems) if ex else None})
        if path == "/api/exams":
            con = db()
            active_exam(con, problems)  # settle an expired exam so it shows in history
            return self._json(exams.history(con))
        if path == "/api/exam/result":
            q = parse_qs(urlparse(self.path).query)
            res = exam_results(db(), int((q.get("id") or ["0"])[0]), problems)
            return self._json(res) if res else self._json({"error": "no such finished exam"}, 404)
        if path == "/api/reference":
            return self._json(reference.payload())
        if path == "/api/frq":
            best = frq.best_scores(db())
            return self._json([frq.summary(q, best.get(q["id"])) for q in frq.load().values()])
        if path == "/api/frq/item":
            q = frq.load().get((parse_qs(urlparse(self.path).query).get("id") or [""])[0])
            return self._json(frq.public(q)) if q else self._json({"error": "no such question"}, 404)
        if path == "/api/learn":
            ov = learn.course_overview(db())
            ov.update(ytdlp=learn.have_ytdlp(), playlist=learn.PLAYLIST_URL, course_id=learn.COURSE_ID, aliases=learn.ALIASES)
            return self._json(ov)
        if path in ("/api/learn/video", "/api/learn/job"):
            if active_exam(db(), problems):
                return self._json(LOCKED, 423)
            key = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            if path.endswith("/job"):
                return self._json(JOBS[key]) if key in JOBS else self._json({"error": "no such job"}, 404)
            d = learn.video_detail(db(), key)
            return self._json(d) if d else self._json({"error": "no such video"}, 404)
        if path == "/api/frq/history":
            return self._json(frq.history(db()))
        if path == "/api/health":  # instant, never touches the AI server (used by the launcher)
            return self._json({"app": "chemtutor", "version": __version__, "pid": os.getpid()})
        if path == "/api/ai":
            found = aiconfig.detect(LLM_URL)
            return self._json({"url": LLM_URL, "model": LLM_MODEL, "backends": found, "auto": _auto != "off",
                               "can_change": self._is_local()})
        if path == "/api/config":
            up, have, names = llm_status()
            return self._json({"model": LLM_MODEL, "llm_url": LLM_URL, "backend": aiconfig.backend_name(LLM_URL), "version": __version__,
                               "llm_ok": up and have, "llm_reachable": up, "models": names[:20]})
        f = WEB_DIR / ("index.html" if path in ("/", "") else path.lstrip("/"))
        if f.is_file() and WEB_DIR in f.resolve().parents:
            ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
                     ".webmanifest": "application/manifest+json", ".png": "image/png", ".svg": "image/svg+xml"}.get(f.suffix, "text/plain")
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype if ctype.startswith("image/") else ctype + "; charset=utf-8")
            if f.name in ("sw.js", "index.html"):
                self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._json({"error": "not found"}, 404)

    def _learn_post(self, con, problems, body):
        if active_exam(con, problems):  # closed-book: lessons, notes and the video tutor stay locked during a mock exam
            return self._json(LOCKED, 423)
        action = self.path.rsplit("/", 1)[-1]
        vid = str(body.get("id", ""))
        try:
            if action == "add":
                if not learn.have_ytdlp():
                    return self._json({"error": "The caption reader (yt-dlp) is not installed yet.", "need_ytdlp": True}, 424)
                url = str(body.get("url", "")).strip()
                if not re.match(r"https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/", url):
                    return self._json({"error": "Paste a YouTube video or playlist link."}, 400)
                return self._json({"job": start_job(lambda progress: learn.import_source(db(), url, progress))})
            if action == "install":
                def work(progress):
                    progress(0, 1, "Installing yt-dlp (a free caption reader)…")
                    ok, msg = learn.install_ytdlp()
                    if not ok:
                        raise RuntimeError("Install failed: " + msg)
                    return {"installed": True}
                return self._json({"job": start_job(work)})
            if action == "import":
                return self._json(learn.import_text(con, str(body.get("title", "")).strip() or "My video", str(body.get("text", ""))))
            if action == "status":
                learn.set_status(con, vid, str(body.get("status", "")))
                return self._json({"ok": True, "covered": learn.covered_topics(con)})
            if action == "grade":
                return self._json(learn.grade_check(con, int(body.get("check_id", 0)), str(body.get("answer", "")), llm))
            if not learn.video_detail(con, vid) and action != "ask":
                return self._json({"error": "no such video"}, 404)
            if action == "notes":
                return self._json({"job": start_job(lambda progress: learn.make_notes(db(), vid, llm, LLM_MODEL, progress))})
            if action == "check":
                return self._json(learn.new_check(con, vid, llm))
            if action == "ask":
                q = str(body.get("question", "")).strip()
                if not q:
                    return self._json({"error": "Type a question first."}, 400)
                return self._json(learn.ask(con, q, llm, vid or None))
        except (ValueError, KeyError) as e:
            return self._json({"error": str(e).strip("'\"")}, 400)
        except Exception as e:  # the AI server being offline, etc.
            return self._json({"error": f"Tutor model unreachable ({LLM_URL}, {LLM_MODEL}): {e}"}, 502)
        self._json({"error": "not found"}, 404)

    def _frq_post(self, con, problems, body):
        if active_exam(con, problems):  # closed-book: rubrics and AI feedback stay locked during a mock exam
            return self._json(LOCKED, 423)
        action = self.path.rsplit("/", 1)[-1]
        q = frq.load().get(body.get("id", ""))
        if not q:
            return self._json({"error": "no such question"}, 404)
        answers = {str(k): str(v) for k, v in (body.get("answers") or {}).items()}
        if action == "reveal":
            return self._json(frq.reveal(q, answers, check_answer))
        if action == "save":
            raw = body.get("scores") or {}
            scores = {str(k): [bool(m) for m in v][:12] for k, v in raw.items() if isinstance(v, list)}
            return self._json(frq.save(con, q, scores, answers))
        if action == "feedback":
            part = next((p for p in q["parts"] if p["label"] == body.get("label")), None)
            if not part:
                return self._json({"error": "no such part"}, 404)
            try:
                return self._json({"reply": llm(frq.feedback_messages(q, part, answers.get(part["label"], "")), 350, 0.2)})
            except Exception as e:
                return self._json({"error": f"Tutor model unreachable ({LLM_URL}, {LLM_MODEL}): {e}"}, 502)
        self._json({"error": "not found"}, 404)

    def _exam_post(self, con, problems, body):
        action = self.path.rsplit("/", 1)[-1]
        ex = active_exam(con, problems)
        if action == "start":
            if ex:
                return self._json({"error": "An exam is already in progress.", "exam": exam_payload(ex, problems)}, 409)
            n = max(3, min(int(body.get("n", 10)), 30))
            limit_s = max(1, min(int(body.get("minutes", 30)), 180)) * 60
            pool = body.get("pool", "all") if body.get("pool") in ("all", "unsolved", "missed") else "all"
            topics = [t for t in body.get("topics", []) if isinstance(t, str)]
            solved = {r[0] for r in con.execute("SELECT DISTINCT problem_id FROM attempts WHERE correct=1")}
            missed = {r[0] for r in con.execute("SELECT DISTINCT problem_id FROM attempts WHERE correct=0")}
            ids = exams.pick(problems, solved, missed, topics, n, pool)
            if not ids:
                return self._json({"error": "No problems match those settings."}, 400)
            ex = exams.get(con, exams.start(con, ids, limit_s, topics, bool(body.get("sheet", True))))
            return self._json({"exam": exam_payload(ex, problems)})
        if action in ("save", "submit", "abandon"):
            if not ex or ex["id"] != body.get("id"):
                done = exam_results(con, int(body.get("id") or 0), problems)  # already finished (e.g. expired)
                return self._json({"result": done} if done else {"error": "no active exam"}, 200 if done else 404)
            answers = {k: str(v) for k, v in (body.get("answers") or {}).items() if k in ex["ids"]}
            if action == "save":
                exams.save_answers(con, ex["id"], answers)
                return self._json({"ok": True, "remaining_s": exams.remaining_s(ex)})
            if action == "abandon":
                exams.abandon(con, ex["id"])
                return self._json({"ok": True})
            return self._json({"result": finalize(con, ex, answers or ex["answers"], problems, "done")})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self._gate():
            return
        problems = load_problems()
        body = self._body()
        con = db()
        if self.path.startswith("/api/exam/"):
            return self._exam_post(con, problems, body)
        if self.path.startswith("/api/frq/"):
            return self._frq_post(con, problems, body)
        if self.path.startswith("/api/learn/"):
            return self._learn_post(con, problems, body)
        if self.path == "/api/ai":
            return self._ai_select(body)
        if self.path == "/api/shutdown":  # `chemtutor.py stop`, or a newer launcher replacing this version
            if not self._is_local():
                return self._json({"error": "Stop ChemTutor on the computer that runs it."}, 403)
            self._json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        p = problems.get(body.get("id", ""))
        if not p:
            return self._json({"error": "unknown problem"}, 404)
        if active_exam(con, problems):  # closed-book: no checking answers or tutor help mid-exam
            return self._json(LOCKED, 423)
        if self.path == "/api/check":
            res = check_answer(p, str(body.get("answer", "")))
            con = db()
            con.execute("INSERT INTO attempts(problem_id,topic,correct,hints_used,answer) VALUES(?,?,?,?,?)",
                        (p["id"], p["topic"], int(res["correct"]), int(body.get("hints_used", 0)), str(body.get("answer", ""))))
            con.commit()
            res["srs"] = srs.record(con, p["id"], res["correct"], int(body.get("hints_used", 0)))
            return self._json(res)
        if self.path == "/api/tutor":
            try:
                if body.get("mode") == "hint":
                    return self._json(hints.generate(p, int(body.get("level", 1)), llm))
                msgs = build_tutor_messages(p, body.get("mode", "hint"), int(body.get("level", 1)),
                                            str(body.get("text", "")), body.get("history", []))
                return self._json({"reply": llm(msgs)})
            except Exception as e:  # LLM offline etc.
                return self._json({"error": f"Tutor model unreachable ({LLM_URL}, {LLM_MODEL}): {e}"}, 502)
        self._json({"error": "not found"}, 404)


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # a browser tab closing mid-response is normal, not worth a traceback
        if isinstance(sys.exc_info()[1], (ConnectionError, BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def make_server(port: int | None = None, remote_access: bool = False, host: str | None = None) -> ThreadingHTTPServer:
    """Local-only server (127.0.0.1) unless remote_access=True, which listens on the network and requires the
    access key from every device but this computer. port=0 picks a free port (used by the tests)."""
    bind = host or ("0.0.0.0" if remote_access else "127.0.0.1")
    srv = QuietServer((bind, PORT if port is None else port), Handler)
    srv.remote = remote_access
    return srv


def main():
    print(f"Chemistry tutor on http://127.0.0.1:{PORT}  (model {LLM_MODEL} @ {LLM_URL})")
    make_server().serve_forever()


if __name__ == "__main__":
    main()
