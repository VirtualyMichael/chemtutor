"""Learn mode: video transcripts -> notes, comprehension checks, a video-grounded tutor, and unlocking of practice.

Transcripts are fetched to YOUR computer only (yt-dlp, English captions) and live in the local database under
library/. They are the video makers' content: they are never part of the repository or the release zip.
The AI only ever works from text the transcript really contains; everything is shown with timestamps so you can check.
"""
from __future__ import annotations
import html, importlib.util, json, math, random, re, subprocess, sys, tempfile, time
from pathlib import Path

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr"   # CrashCourse "Chemistry"
COURSE_ID = "crashcourse-chemistry"

TOPICS_VERSION = "4"


def retopic(con) -> int:
    """Recompute which practice topics each stored video covers (run automatically when TOPICS_VERSION changes)."""
    n = 0
    for vid, title in con.execute("SELECT id,title FROM videos").fetchall():
        text = " ".join(r[0] for r in con.execute("SELECT text FROM chunks WHERE video_id=? ORDER BY idx", (vid,)))
        con.execute("UPDATE videos SET topics=? WHERE id=?", (json.dumps(lesson_topics(title, text)), vid))
        n += 1
    con.commit()
    return n


# ------------------------------------------------------------------ storage
def init(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS videos(id TEXT PRIMARY KEY, course TEXT, ord INTEGER, ep INTEGER, title TEXT, duration INTEGER, topics TEXT DEFAULT '[]');
    CREATE TABLE IF NOT EXISTS chunks(video_id TEXT, idx INTEGER, start REAL, text TEXT, PRIMARY KEY(video_id, idx));
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(video_id UNINDEXED, start UNINDEXED, text, tokenize='porter');
    CREATE TABLE IF NOT EXISTS lesson_notes(video_id TEXT PRIMARY KEY, notes TEXT, made TEXT DEFAULT CURRENT_TIMESTAMP, model TEXT);
    CREATE TABLE IF NOT EXISTS lesson_progress(video_id TEXT PRIMARY KEY, status TEXT DEFAULT 'new', updated TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS lesson_checks(id INTEGER PRIMARY KEY, video_id TEXT, question TEXT, reference TEXT, excerpt TEXT, start REAL,
        answer TEXT, verdict TEXT, feedback TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS learn_meta(k TEXT PRIMARY KEY, v TEXT);
    """)
    row = con.execute("SELECT v FROM learn_meta WHERE k='topics_version'").fetchone()
    if not row or row[0] != TOPICS_VERSION:
        retopic(con)
        con.execute("INSERT OR REPLACE INTO learn_meta VALUES('topics_version', ?)", (TOPICS_VERSION,))
        con.commit()


# ------------------------------------------------------------------ caption parsing
_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->")


def _secs(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_captions(text: str) -> list[tuple[float, str]]:
    """WebVTT or SRT -> [(start_seconds, text)]. Strips markup and the repeated lines auto-captions roll through."""
    cues, lines, i = [], text.replace("\r", "").split("\n"), 0
    last_line = ""
    while i < len(lines):
        m = _TS.search(lines[i])
        if not m:
            i += 1
            continue
        start = _secs(*m.groups())
        i += 1
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i])
            i += 1
        clean = [html.unescape(re.sub(r"<[^>]+>", "", b)).strip() for b in body]
        clean = [c for c in clean if c and not c.isdigit()]
        if clean and clean[0] == last_line:          # rolling auto-caption repeats the previous line
            clean = clean[1:]
        if not clean:
            continue
        last_line = clean[-1]
        cues.append((start, " ".join(clean)))
    return cues


def parse_plain(text: str) -> list[tuple[float, str]]:
    """Pasted transcript without timestamps (or with [m:ss] / m:ss markers on their own). Unknown times are -1."""
    cues, t = [], -1.0
    for para in re.split(r"\n\s*\n|\n", text.strip()):
        para = para.strip()
        if not para:
            continue
        m = re.fullmatch(r"\[?(?:(\d+):)?(\d{1,2}):(\d{2})\]?", para)
        if m:
            t = _secs(m.group(1), m.group(2), m.group(3), "0")
            continue
        m = re.match(r"^\[?(?:(\d+):)?(\d{1,2}):(\d{2})\]?\s+(.*)$", para)
        if m:
            t, para = _secs(m.group(1), m.group(2), m.group(3), "0"), m.group(4)
        cues.append((t, para))
    return cues


def to_cues(text: str) -> list[tuple[float, str]]:
    return parse_captions(text) if "-->" in text else parse_plain(text)


def chunk_cues(cues, target_words: int = 55, max_seconds: float = 45) -> list[tuple[float, str]]:
    out, cur, start, words = [], [], None, 0
    for t, s in cues:
        if start is None:
            start = t
        cur.append(s)
        words += len(s.split())
        if words >= target_words or (t >= 0 and start >= 0 and t - start >= max_seconds):
            out.append((start, " ".join(cur)))
            cur, start, words = [], None, 0
    if cur:
        out.append((start if start is not None else 0, " ".join(cur)))
    return out


def clock(sec: float) -> str:
    if sec is None or sec < 0:
        return ""
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


# ------------------------------------------------------------------ topics (which practice topics a lesson covers)
ALIASES = {
    "Foundations": ["Foundations", "Essential Ideas"],
    "Atoms, Molecules & Ions": ["Atoms, Molecules & Ions"],
    "Moles & Stoichiometry": ["Moles & Stoichiometry"],
    "Solutions": ["Solutions", "Composition of Substances & Solutions", "Solutions & Colloids"],
    "Gases": ["Gases"],
    "Thermochemistry": ["Thermochemistry"],
    "Thermodynamics": ["Thermodynamics"],
    "Electronic Structure & Periodicity": ["Electronic Structure & Periodicity"],
    "Bonding & Geometry": ["Bonding & Geometry", "Advanced Covalent Bonding"],
    "Liquids & Solids": ["Liquids & Solids"],
    "Kinetics": ["Kinetics"],
    "Equilibrium": ["Equilibrium", "Other Equilibria"],
    "Acids & Bases": ["Acids & Bases"],
    "Electrochemistry": ["Electrochemistry"],
    "Nuclear": ["Nuclear"],
}
KEYWORDS = {
    "Foundations": ["significant figure", "unit conversion", "conversion factor", "scientific notation", "dimensional analysis", "density", "kelvin"],
    "Atoms, Molecules & Ions": ["proton", "neutron", "isotope", "atomic number", "mass number", "nucleus", "ion", "ionic compound", "periodic table", "atomic mass"],
    "Moles & Stoichiometry": ["mole", "molar mass", "avogadro", "stoichiometry", "limiting reagent", "limiting reactant", "percent yield", "empirical formula", "balanced equation"],
    "Solutions": ["solution", "solute", "solvent", "molarity", "concentration", "dilution", "dissolve", "solubility"],
    "Gases": ["gas", "ideal gas", "pressure", "partial pressure", "boyle", "charles", "gas law", "effusion", "diffusion", "kinetic molecular"],
    "Thermochemistry": ["enthalpy", "calorimetry", "specific heat", "exothermic", "endothermic", "hess", "heat capacity"],
    "Thermodynamics": ["entropy", "gibbs", "free energy", "spontaneous", "second law"],
    "Electronic Structure & Periodicity": ["electron configuration", "orbital", "quantum", "valence electron", "ionization energy", "electronegativity", "atomic radius", "photon", "wavelength"],
    "Bonding & Geometry": ["covalent", "lewis structure", "polar", "molecular geometry", "vsepr", "bond angle", "hybridization", "resonance", "bond"],
    "Liquids & Solids": ["intermolecular", "hydrogen bond", "vapor pressure", "surface tension", "crystal", "unit cell", "solid"],
    "Kinetics": ["reaction rate", "rate law", "activation energy", "catalyst", "kinetics", "rate constant", "collision"],
    "Equilibrium": ["equilibrium", "le chatelier", "equilibrium constant", "reaction quotient"],
    "Acids & Bases": ["acid", "base", "ph", "poh", "buffer", "titration", "hydronium", "hydroxide", "conjugate"],
    "Electrochemistry": ["redox", "oxidation", "reduction", "electrochemical", "galvanic", "electrolysis", "cell potential", "anode", "cathode"],
    "Nuclear": ["radioactive", "half-life", "fission", "fusion", "nuclear", "decay", "alpha particle", "beta"],
}


# words that only count when they are in the video TITLE ("energy" in a body would pollute every topic)
TITLE_KEYWORDS = {
    "Foundations": ["unit", "conversion", "significant"], "Atoms, Molecules & Ions": ["atom", "nucleus", "atomic", "periodic table", "element"],
    "Thermochemistry": ["energy", "heat", "calorimetry", "enthalpy"], "Liquids & Solids": ["liquid", "solid"], "Solutions": ["solution", "water"],
    "Nuclear": ["nuclear"], "Electrochemistry": ["redox", "electrochemistry"], "Kinetics": ["kinetics"], "Equilibrium": ["equilibrium"],
}


def _count(text: str, kw: str) -> int:
    """Whole-word (plural-tolerant) occurrences, so 'ion' does not match 'solution' and 'mole' not 'molecule'."""
    return len(re.findall(rf"\b{re.escape(kw.strip())}(?:s|es)?\b", text))


def lesson_topics(title: str, text: str, limit: int = 3) -> list[str]:
    """Canonical practice topics a lesson covers: keyword counts in the transcript, title matches weigh 6x."""
    body, ttl = text.lower(), title.lower()
    score = {}
    for topic, kws in KEYWORDS.items():
        s = sum(_count(body, k) for k in kws) + 6 * sum(_count(ttl, k) for k in kws + TITLE_KEYWORDS.get(topic, []))
        if s:
            score[topic] = s
    if not score:
        return []
    ranked = sorted(score.items(), key=lambda kv: -kv[1])
    top = ranked[0][1]
    if top < 2:
        return []
    # the best match always counts; others must be at least half as strong (and not just a passing mention)
    return [t for i, (t, s) in enumerate(ranked) if i == 0 or s >= max(5, 0.5 * top)][:limit]


def expand_topics(canonical) -> list[str]:
    out = []
    for t in canonical:
        out += ALIASES.get(t, [t])
    return sorted(set(out))


# ------------------------------------------------------------------ store / read
def store_video(con, vid: str, title: str, cues, course: str = COURSE_ID, ord_: int = 0, duration: int = 0) -> dict:
    chunks = chunk_cues(cues)
    full = " ".join(c[1] for c in chunks)
    ep = re.search(r"#\s*(\d+)", title)
    topics = lesson_topics(title, full)
    con.execute("INSERT OR REPLACE INTO videos(id,course,ord,ep,title,duration,topics) VALUES(?,?,?,?,?,?,?)",
                (vid, course, ord_, int(ep.group(1)) if ep else 0, title, duration, json.dumps(topics)))
    con.execute("DELETE FROM chunks WHERE video_id=?", (vid,))
    con.execute("DELETE FROM chunks_fts WHERE video_id=?", (vid,))
    for i, (start, text) in enumerate(chunks):
        con.execute("INSERT INTO chunks VALUES(?,?,?,?)", (vid, i, start, text))
        con.execute("INSERT INTO chunks_fts(video_id,start,text) VALUES(?,?,?)", (vid, start, text))
    con.commit()
    return {"id": vid, "chunks": len(chunks), "words": len(full.split()), "topics": topics}


def add_listing(con, vid: str, title: str, ord_: int, duration: int, course: str = COURSE_ID):
    """Register a video from a playlist listing (no transcript yet)."""
    ep = re.search(r"#\s*(\d+)", title)
    con.execute("INSERT OR IGNORE INTO videos(id,course,ord,ep,title,duration,topics) VALUES(?,?,?,?,?,?,'[]')",
                (vid, course, ord_, int(ep.group(1)) if ep else 0, title, duration))
    con.execute("INSERT OR IGNORE INTO lesson_progress(video_id) VALUES(?)", (vid,))
    con.commit()


def set_status(con, vid: str, status: str):
    if status not in ("new", "watched", "understood"):
        raise ValueError("bad status")
    con.execute("INSERT INTO lesson_progress(video_id,status) VALUES(?,?) ON CONFLICT(video_id) DO UPDATE SET status=excluded.status, updated=CURRENT_TIMESTAMP", (vid, status))
    con.commit()


def course_overview(con) -> dict:
    rows = con.execute("""SELECT v.id,v.course,v.ord,v.ep,v.title,v.duration,v.topics, COALESCE(p.status,'new'),
        (SELECT COUNT(*) FROM chunks c WHERE c.video_id=v.id), (SELECT 1 FROM lesson_notes n WHERE n.video_id=v.id)
        FROM videos v LEFT JOIN lesson_progress p ON p.video_id=v.id ORDER BY v.course, v.ord, v.id""").fetchall()
    vids = [{"id": r[0], "course": r[1], "ord": r[2], "ep": r[3], "title": r[4], "duration": r[5], "topics": json.loads(r[6] or "[]"),
             "status": r[7], "has_transcript": r[8] > 0, "has_notes": bool(r[9])} for r in rows]
    return {"videos": vids, "covered": covered_topics(con)}


def covered_topics(con) -> list[str]:
    canon = set()
    for (t,) in con.execute("""SELECT v.topics FROM videos v JOIN lesson_progress p ON p.video_id=v.id WHERE p.status IN ('watched','understood')"""):
        canon.update(json.loads(t or "[]"))
    return expand_topics(canon)


def video_detail(con, vid: str):
    r = con.execute("SELECT id,course,ord,ep,title,duration,topics FROM videos WHERE id=?", (vid,)).fetchone()
    if not r:
        return None
    st = con.execute("SELECT status FROM lesson_progress WHERE video_id=?", (vid,)).fetchone()
    n = con.execute("SELECT notes, model FROM lesson_notes WHERE video_id=?", (vid,)).fetchone()
    chunks = [{"start": s, "t": clock(s), "text": t} for s, t in con.execute("SELECT start,text FROM chunks WHERE video_id=? ORDER BY idx", (vid,))]
    checks = [{"question": q, "verdict": v, "feedback": f} for q, v, f in con.execute(
        "SELECT question,verdict,feedback FROM lesson_checks WHERE video_id=? AND verdict IS NOT NULL ORDER BY id DESC LIMIT 12", (vid,))]
    return {"id": r[0], "course": r[1], "ord": r[2], "ep": r[3], "title": r[4], "duration": r[5], "topics": json.loads(r[6] or "[]"),
            "status": st[0] if st else "new", "transcript": chunks, "notes": json.loads(n[0]) if n else None, "checks": checks}


# ------------------------------------------------------------------ retrieval
STOP = set("the a an and or of to in is are was were be been it that this what how why when which who do does did for on with as at by from "
           "about can could would should i you we they he she my your me tell explain mean means please just like".split())


def _terms(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if len(t) > 2 and t not in STOP]


def search(con, query: str, limit: int = 5, video_id: str | None = None) -> list[dict]:
    terms = _terms(query)
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    sql = """SELECT f.video_id, f.start, f.text, v.title, v.ep FROM chunks_fts f JOIN videos v ON v.id=f.video_id
             WHERE chunks_fts MATCH ? {} ORDER BY rank LIMIT ?"""
    try:
        if video_id:
            rows = con.execute(sql.format("AND f.video_id = ?"), (match, video_id, limit)).fetchall()
            if len(rows) >= limit:
                return [_hit(r) for r in rows]
            extra = con.execute(sql.format("AND f.video_id != ?"), (match, video_id, limit - len(rows))).fetchall()
            return [_hit(r) for r in rows + extra]
        return [_hit(r) for r in con.execute(sql.format(""), (match, limit)).fetchall()]
    except Exception:
        return []


def _hit(r) -> dict:
    return {"video_id": r[0], "start": r[1], "t": clock(r[1]), "text": r[2], "title": r[3], "ep": r[4]}


def cite(h: dict) -> str:
    label = f"Ep {h['ep']}" if h.get("ep") else h["title"][:24]
    return f"[{label}{' @ ' + h['t'] if h['t'] else ''}]"


# ------------------------------------------------------------------ AI helpers (llm(messages, max_tokens, temperature) -> str)
def extract_json(text: str):
    """First JSON object in a model reply, tolerating code fences and chatter; None if there isn't one."""
    s = re.sub(r"```(?:json)?", "", text or "")
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        return json.loads(s[a:b + 1])
    except ValueError:
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", s[a:b + 1]))
        except ValueError:
            return None


def grounded(term: str, text: str) -> bool:
    low = text.lower()
    toks = [t.rstrip("s") for t in re.findall(r"[a-z]{4,}", term.lower())]
    return all(t in low for t in toks) if toks else term.lower() in low


def sections(chunks, words: int = 520):
    out, cur, n, start = [], [], 0, None
    for s, t in chunks:
        start = s if start is None else start
        cur.append(t)
        n += len(t.split())
        if n >= words:
            out.append((start, " ".join(cur)))
            cur, n, start = [], 0, None
    if cur:
        out.append((start if start is not None else 0, " ".join(cur)))
    return out


NOTES_SYS = ("You write study notes for a complete beginner from ONE section of a chemistry video transcript. Use ONLY what the speaker says in the "
             "section. Reply with JSON only: {\"summary\": \"two plain sentences\", \"terms\": [{\"term\": \"...\", \"definition\": \"one plain sentence\"}]}. "
             "At most 4 terms, only terms the speaker actually explains. No LaTeX.")
Q_SYS = ("From these notes about a chemistry lesson, write 3 short questions a beginner should be able to answer after watching. "
         "Reply with JSON only: {\"questions\": [\"...\", \"...\", \"...\"]}.")


def make_notes(con, vid: str, llm, model: str = "", progress=None) -> dict:
    chunks = [(s, t) for s, t in con.execute("SELECT start,text FROM chunks WHERE video_id=? ORDER BY idx", (vid,))]
    if not chunks:
        raise ValueError("this video has no transcript yet")
    secs = sections(chunks)
    timeline, terms, seen = [], [], set()
    for i, (start, text) in enumerate(secs):
        if progress:
            progress(i, len(secs) + 1, f"Reading part {i + 1} of {len(secs)}…")
        reply = llm([{"role": "system", "content": NOTES_SYS}, {"role": "user", "content": text}], 450, 0.2)
        data = extract_json(reply) or {}
        summary = str(data.get("summary") or "").strip() or re.sub(r"\s+", " ", reply).strip()[:280]
        timeline.append({"start": start, "t": clock(start), "text": summary})
        for t in data.get("terms") or []:
            term, d = str(t.get("term", "")).strip(), str(t.get("definition", "")).strip()
            key = re.sub(r"(es|s)$", "", term.lower())          # "mole"/"moles" count as the same term
            if term and d and key not in seen and grounded(term, text):
                seen.add(key)
                terms.append({"term": term, "definition": d, "start": start, "t": clock(start)})
    if progress:
        progress(len(secs), len(secs) + 1, "Writing questions to watch for…")
    qd = extract_json(llm([{"role": "system", "content": Q_SYS}, {"role": "user", "content": "\n".join(x["text"] for x in timeline)}], 300, 0.3)) or {}
    notes = {"timeline": timeline, "terms": terms, "questions": [str(q) for q in (qd.get("questions") or [])][:3]}
    con.execute("INSERT OR REPLACE INTO lesson_notes(video_id,notes,model) VALUES(?,?,?)", (vid, json.dumps(notes), model))
    con.commit()
    return notes


CHECK_SYS = ("You write ONE comprehension question for a beginner, answerable only from the excerpt of a chemistry lesson. "
             "Reply with JSON only: {\"question\": \"...\", \"answer\": \"1-2 sentences using the excerpt's ideas\"}.")
GRADE_SYS = ("You are a kind, strict tutor marking a beginner's short answer using the excerpt and reference answer. Reply with JSON only: "
             "{\"verdict\": \"correct\" or \"partly\" or \"incorrect\", \"feedback\": \"one or two sentences saying what is right and what is missing\"}. "
             "Do not invent facts that are not in the excerpt.")


def new_check(con, vid: str, llm, rng=random) -> dict:
    rows = [(s, t) for s, t in con.execute("SELECT start,text FROM chunks WHERE video_id=? ORDER BY idx", (vid,))]
    if not rows:
        raise ValueError("this video has no transcript yet")
    used = {r[0] for r in con.execute("SELECT start FROM lesson_checks WHERE video_id=?", (vid,))}
    win = [(rows[i][0], " ".join(r[1] for r in rows[i:i + 3])) for i in range(0, max(1, len(rows) - 2), 2)]
    fresh = [w for w in win if w[0] not in used] or win
    start, excerpt = rng.choice(fresh)
    data = extract_json(llm([{"role": "system", "content": CHECK_SYS}, {"role": "user", "content": excerpt}], 250, 0.4)) or {}
    q, a = str(data.get("question") or "").strip(), str(data.get("answer") or "").strip()
    if not q or not a:
        raise ValueError("the model did not produce a usable question; try again")
    cur = con.execute("INSERT INTO lesson_checks(video_id,question,reference,excerpt,start) VALUES(?,?,?,?,?)", (vid, q, a, excerpt, start))
    con.commit()
    return {"check_id": cur.lastrowid, "question": q}


def grade_check(con, check_id: int, answer: str, llm) -> dict:
    r = con.execute("SELECT video_id,question,reference,excerpt,start FROM lesson_checks WHERE id=?", (check_id,)).fetchone()
    if not r:
        raise KeyError("no such check")
    user = f"Excerpt:\n{r[3]}\n\nQuestion: {r[1]}\nReference answer: {r[2]}\n\nStudent answer: {answer or '(blank)'}"
    data = extract_json(llm([{"role": "system", "content": GRADE_SYS}, {"role": "user", "content": user}], 200, 0.1)) or {}
    verdict = str(data.get("verdict", "")).lower()
    verdict = verdict if verdict in ("correct", "partly", "incorrect") else "unknown"
    feedback = str(data.get("feedback") or "I could not judge this one: compare with the reference answer below.").strip()
    con.execute("UPDATE lesson_checks SET answer=?, verdict=?, feedback=? WHERE id=?", (answer, verdict, feedback, check_id))
    con.commit()
    return {"verdict": verdict, "feedback": feedback, "reference": r[2], "excerpt": r[3], "start": r[4], "t": clock(r[4]), "video_id": r[0]}


ASK_SYS = ("You are a patient tutor teaching a complete beginner chemistry, alongside a video course. If the question is not about chemistry "
           "(or the basic maths/physics it needs), politely say you can only help with chemistry and stop. Otherwise first use the VIDEO EXCERPTS below. "
           "Cite a source at the END of the sentence it supports, using its exact bracket label like [Ep 6 @ 5:00]; never start a paragraph with a "
           "citation. Use CHEAT SHEET lines for formulas. If the excerpts do not cover the question, say so plainly, then give a short standard "
           "explanation and label it '(beyond the videos)'. Be simple and concrete, define any term you use, and end by asking one short question "
           "to check understanding. Plain text, no LaTeX, under 180 words.")


def sheet_hits(question: str, limit: int = 2) -> list[str]:
    from . import reference
    terms = _terms(question)
    scored = []
    for sec in reference.SECTIONS:
        for e in sec["entries"]:
            if e["t"] != "eq":
                continue
            low = (e["name"] + " " + e["eq"] + " " + e.get("note", "")).lower()
            s = sum(2 if t in e["name"].lower() else 1 for t in terms if t in low)
            if s >= 2:
                scored.append((s, f"{e['name']}: {e['eq']}"))
    return [x[1] for x in sorted(scored, key=lambda x: -x[0])[:limit]]


CHEM_WORDS = ({w.rstrip("s") for kws in KEYWORDS.values() for k in kws for w in re.findall(r"[a-z]{3,}", k)} |
              set("atom molecule element compound mixture reaction chemical chemistry electron matter mass energy temperature solid liquid gas ion bond "
                  "acid base mole periodic equation formula concentration solution volume pressure heat metal salt water carbon hydrogen oxygen "
                  "isotope charge particle orbital nucleus conversion measure unit significant density".split()))
OFF_TOPIC = "I can only help with chemistry, so that one is outside what I can teach. Try asking about something from the lessons."


def on_topic(question: str, hits: list[dict]) -> bool:
    """Chemistry vocabulary in the question, or at least two of its words matching one transcript passage."""
    terms = {t.rstrip("s") for t in _terms(question)}
    if terms & CHEM_WORDS:
        return True
    best = max((sum(1 for t in terms if t in h["text"].lower()) for h in hits), default=0)
    return best >= 2


def tidy_citations(reply: str) -> str:
    """Small models like to open a paragraph with [Ep 6 @ 5:00]; move it to the end of the paragraph."""
    out = []
    for para in re.split(r"\n\s*\n", reply.strip()):
        m = re.match(r"^(\[[^\]]*@[^\]]*\])\s*(.+)$", para, re.S)
        out.append(f"{m.group(2).strip()} {m.group(1)}" if m else para)
    return "\n\n".join(out)


def ask(con, question: str, llm, video_id: str | None = None) -> dict:
    hits = search(con, question, limit=4, video_id=video_id)
    if not on_topic(question, hits):
        return {"reply": OFF_TOPIC, "sources": []}
    ex = "\n".join(f"{cite(h)} {h['text']}" for h in hits) or "(no matching passage in the loaded videos)"
    sheet = "\n".join(sheet_hits(question)) or "(none)"
    reply = llm([{"role": "system", "content": ASK_SYS},
                 {"role": "user", "content": f"VIDEO EXCERPTS:\n{ex}\n\nCHEAT SHEET:\n{sheet}\n\nStudent question: {question}"}], 420, 0.3)
    return {"reply": tidy_citations(reply), "sources": [{k: h[k] for k in ("video_id", "start", "t", "title", "ep")} for h in hits]}


# ------------------------------------------------------------------ fetching (yt-dlp, run as a subprocess; English captions only)
def have_ytdlp() -> bool:
    return importlib.util.find_spec("yt_dlp") is not None


def _yt(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "yt_dlp", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def install_ytdlp() -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "yt-dlp"], capture_output=True, text=True, timeout=300)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def list_source(url: str) -> tuple[str, list[dict]]:
    """(title, [{id, ord, duration, title}]) for a playlist or a single video URL."""
    r = _yt(["--flat-playlist", "--print", "%(playlist_title)s\t%(playlist_index)s\t%(id)s\t%(duration)s\t%(title)s", url], 120)
    items, ptitle = [], ""
    for line in r.stdout.splitlines():
        parts = line.split("\t", 4)
        if len(parts) < 5 or not re.fullmatch(r"[\w-]{11}", parts[2]):
            continue
        ptitle = ptitle or parts[0]
        items.append({"id": parts[2], "ord": int(parts[1]) if parts[1].isdigit() else len(items) + 1,
                      "duration": int(float(parts[3])) if parts[3].replace(".", "").isdigit() else 0, "title": parts[4]})
    if not items:
        raise ValueError("Could not read that link. Use a YouTube video or playlist URL. " + (r.stderr.strip().splitlines() or [""])[-1][:160])
    return (ptitle if ptitle and ptitle != "NA" else "My videos"), items


def fetch_captions(vid: str, retries: int = 3) -> str | None:
    with tempfile.TemporaryDirectory() as d:
        for attempt in range(retries):
            r = _yt(["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en", "--sub-format", "vtt", "--no-playlist",
                     "-o", f"{d}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={vid}"], 120)
            files = sorted(Path(d).glob("*.vtt"))
            if files:
                return files[0].read_text(encoding="utf-8", errors="replace")
            if "429" in r.stderr and attempt < retries - 1:
                time.sleep(15 * (attempt + 1))
                continue
            return None
    return None


def import_source(con, url: str, progress=None, pause: float = 1.2, course: str | None = None) -> dict:
    """Register every video at the URL, then fetch each transcript. Returns counts. Safe to run again (skips done videos)."""
    title, items = list_source(url)
    cid = course or (COURSE_ID if "PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr" in url else re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "my-videos")
    for it in items:
        add_listing(con, it["id"], it["title"], it["ord"], it["duration"], cid)
    got = skipped = failed = 0
    for i, it in enumerate(items):
        if progress:
            progress(i, len(items), f"Fetching captions {i + 1} of {len(items)}: {it['title'][:50]}")
        if con.execute("SELECT 1 FROM chunks WHERE video_id=? LIMIT 1", (it["id"],)).fetchone():
            skipped += 1
            continue
        text = fetch_captions(it["id"])
        cues = to_cues(text) if text else []
        if cues:
            store_video(con, it["id"], it["title"], cues, cid, it["ord"], it["duration"])
            got += 1
        else:
            failed += 1
        time.sleep(pause)
    if progress:
        progress(len(items), len(items), "Done")
    return {"course": cid, "title": title, "videos": len(items), "fetched": got, "already_had": skipped, "no_captions": failed}


def import_text(con, title: str, text: str, vid: str | None = None, course: str = "my-videos") -> dict:
    cues = to_cues(text)
    if not cues:
        raise ValueError("no transcript text found")
    vid = vid or "txt-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    n = con.execute("SELECT COALESCE(MAX(ord),0) FROM videos WHERE course=?", (course,)).fetchone()[0]
    res = store_video(con, vid, title, cues, course, n + 1, 0)
    con.execute("INSERT OR IGNORE INTO lesson_progress(video_id) VALUES(?)", (vid,))
    con.commit()
    return res
