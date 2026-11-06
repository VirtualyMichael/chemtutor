"""Closed-book mock exams: selection, storage, grading. The server enforces the time limit and locks the tutor
while an exam is running; answers are autosaved so an expired exam is still graded from what was saved.
"""
from __future__ import annotations
import json, random
from datetime import datetime, timedelta

from .srs import utcnow

GRACE_S = 30  # slack after the deadline before the server treats the exam as over


def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS exams(
        id INTEGER PRIMARY KEY, started TEXT, limit_s INTEGER, status TEXT, ids TEXT, answers TEXT DEFAULT '{}',
        topics TEXT DEFAULT '[]', finished TEXT, score INTEGER, total INTEGER, elapsed_s INTEGER)""")
    con.execute("""CREATE TABLE IF NOT EXISTS exam_items(
        exam_id INTEGER, problem_id TEXT, answer TEXT, correct INTEGER, PRIMARY KEY(exam_id, problem_id))""")
    if "sheet" not in {r[1] for r in con.execute("PRAGMA table_info(exams)")}:  # migrate older databases
        con.execute("ALTER TABLE exams ADD COLUMN sheet INTEGER DEFAULT 1")


def pick(problems: dict, solved: set, missed: set, topics: list, n: int, pool: str, rng=random) -> list:
    """Choose up to n problem ids, spread across topics, ordered easy -> hard."""
    cand = [p for p in problems.values()
            if (not topics or p["topic"] in topics)
            and (pool != "unsolved" or p["id"] not in solved)
            and (pool != "missed" or p["id"] in missed)]
    by_topic = {}
    for p in cand:
        by_topic.setdefault(p["topic"], []).append(p)
    for lst in by_topic.values():
        rng.shuffle(lst)
    order = list(by_topic)
    rng.shuffle(order)
    chosen = []
    while len(chosen) < n and any(by_topic.values()):
        for t in order:
            if by_topic[t] and len(chosen) < n:
                chosen.append(by_topic[t].pop())
    chosen.sort(key=lambda p: (p["level"], p["topic"]))
    return [p["id"] for p in chosen]


def start(con, ids: list, limit_s: int, topics: list, sheet: bool = True) -> int:
    cur = con.execute("INSERT INTO exams(started,limit_s,status,ids,topics,sheet) VALUES(?,?,?,?,?,?)",
                      (utcnow().isoformat(), limit_s, "active", json.dumps(ids), json.dumps(topics), int(sheet)))
    con.commit()
    return cur.lastrowid


def get(con, exam_id: int):
    r = con.execute("""SELECT id,started,limit_s,status,ids,answers,topics,finished,score,total,elapsed_s,sheet
                       FROM exams WHERE id=?""", (exam_id,)).fetchone()
    if not r:
        return None
    return {"id": r[0], "started": datetime.fromisoformat(r[1]), "limit_s": r[2], "status": r[3],
            "ids": json.loads(r[4]), "answers": json.loads(r[5] or "{}"), "topics": json.loads(r[6] or "[]"),
            "finished": r[7], "score": r[8], "total": r[9], "elapsed_s": r[10], "sheet": bool(r[11] is None or r[11])}


def remaining_s(ex: dict, now=None) -> int:
    now = now or utcnow()
    return int((ex["started"] + timedelta(seconds=ex["limit_s"]) - now).total_seconds())


def current(con):
    """The unfinished exam (status 'active') or None. Adds 'expired': True once past deadline + grace."""
    r = con.execute("SELECT id FROM exams WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
    if not r:
        return None
    ex = get(con, r[0])
    ex["expired"] = remaining_s(ex) < -GRACE_S
    return ex


def save_answers(con, exam_id: int, answers: dict):
    con.execute("UPDATE exams SET answers=? WHERE id=? AND status='active'", (json.dumps(answers), exam_id))
    con.commit()


def grade(problems: dict, ids: list, answers: dict, check) -> dict:
    """check(problem, text) -> {'correct': bool, ...}. Blank answers count as wrong."""
    items = []
    for pid in ids:
        p, a = problems[pid], str(answers.get(pid, "")).strip()
        ok = bool(a) and check(p, a)["correct"]
        items.append({"id": pid, "answer": a, "correct": ok})
    return {"items": items, "score": sum(i["correct"] for i in items), "total": len(items)}


def finish(con, exam_id: int, graded: dict, elapsed_s: int, status: str):
    for i in graded["items"]:
        con.execute("INSERT OR REPLACE INTO exam_items VALUES(?,?,?,?)",
                    (exam_id, i["id"], i["answer"], int(i["correct"])))
    con.execute("""UPDATE exams SET status=?, finished=?, score=?, total=?, elapsed_s=? WHERE id=?""",
                (status, utcnow().isoformat(), graded["score"], graded["total"], elapsed_s, exam_id))
    con.commit()


def abandon(con, exam_id: int):
    con.execute("UPDATE exams SET status='abandoned', finished=? WHERE id=? AND status='active'",
                (utcnow().isoformat(), exam_id))
    con.commit()


def history(con, limit=20):
    rows = con.execute("""SELECT id,started,status,score,total,elapsed_s,limit_s,topics FROM exams
                          WHERE status IN ('done','expired') ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
    return [{"id": r[0], "date": r[1], "status": r[2], "score": r[3], "total": r[4], "elapsed_s": r[5],
             "limit_s": r[6], "topics": json.loads(r[7] or "[]")} for r in rows]


def items(con, exam_id: int):
    return [{"id": r[0], "answer": r[1], "correct": bool(r[2])} for r in
            con.execute("SELECT problem_id,answer,correct FROM exam_items WHERE exam_id=? ORDER BY rowid", (exam_id,))]
