"""Spaced repetition (SM-2 variant) for problems. Pure functions + tiny SQLite helpers.

Grade from an attempt: wrong = 1, right with 2+ hints = 3, right with 1 hint = 4, right unaided = 5.
Wrong answers reset the card (relearn in 10 minutes). Right answers go 1 day -> 3 days -> interval * ease.
A correct answer only reschedules a card that is new or due, so re-checking the same problem can't
inflate its interval; a wrong answer always counts.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

MIN_EASE = 1.3
RELEARN = timedelta(minutes=10)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def grade(correct: bool, hints: int) -> int:
    if not correct:
        return 1
    return 5 if hints <= 0 else 4 if hints == 1 else 3


def next_state(state: dict | None, correct: bool, hints: int, now: datetime | None = None):
    """Return (new_state, changed). state = {ease, interval, reps, lapses, due(datetime)} or None for a new card."""
    now = now or utcnow()
    s = dict(state) if state else {"ease": 2.5, "interval": 0.0, "reps": 0, "lapses": 0, "due": now}
    is_due = state is None or s["due"] <= now
    if correct and not is_due:
        return s, False
    q = grade(correct, hints)
    if q < 3:
        s["reps"], s["interval"] = 0, RELEARN.total_seconds() / 86400
        s["lapses"] += 1
        s["ease"] = max(MIN_EASE, s["ease"] - 0.2)
    else:
        s["reps"] += 1
        s["interval"] = 1.0 if s["reps"] == 1 else 3.0 if s["reps"] == 2 else round(s["interval"] * s["ease"], 2)
        s["ease"] = max(MIN_EASE, s["ease"] + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    s["due"] = now + timedelta(days=s["interval"])
    return s, True


def label(days: float) -> str:
    mins = days * 1440
    if mins < 90:
        return f"{max(1, round(mins))} minutes"
    if mins < 1440 * 1.5:
        return f"{round(mins / 60)} hours" if mins < 1320 else "1 day"
    return f"{round(days)} days"


# ---- storage ----
def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS srs(problem_id TEXT PRIMARY KEY, ease REAL, interval REAL,
                   reps INTEGER, lapses INTEGER, due TEXT)""")


def load(con, pid: str):
    r = con.execute("SELECT ease,interval,reps,lapses,due FROM srs WHERE problem_id=?", (pid,)).fetchone()
    return None if not r else {"ease": r[0], "interval": r[1], "reps": r[2], "lapses": r[3],
                               "due": datetime.fromisoformat(r[4])}


def save(con, pid: str, s: dict):
    con.execute("""INSERT INTO srs(problem_id,ease,interval,reps,lapses,due) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(problem_id) DO UPDATE SET ease=excluded.ease, interval=excluded.interval,
                   reps=excluded.reps, lapses=excluded.lapses, due=excluded.due""",
                (pid, s["ease"], s["interval"], s["reps"], s["lapses"], s["due"].isoformat()))


def record(con, pid: str, correct: bool, hints: int):
    """Update the card after an attempt; returns {'next_in': label, 'due': iso} describing its schedule."""
    cur = load(con, pid)
    new, changed = next_state(cur, correct, hints)
    if changed:
        save(con, pid, new)
        con.commit()
    return {"next_in": label((new["due"] - utcnow()).total_seconds() / 86400), "due": new["due"].isoformat(),
            "rescheduled": changed}


def overview(con):
    """Due ids (oldest first) plus summary counts for the dashboard."""
    now = utcnow()
    rows = con.execute("SELECT problem_id,interval,due,lapses FROM srs ORDER BY due").fetchall()
    due = [r[0] for r in rows if datetime.fromisoformat(r[2]) <= now]
    nxt = next((datetime.fromisoformat(r[2]) for r in rows if datetime.fromisoformat(r[2]) > now), None)
    return {"due": due, "total": len(rows), "mature": sum(1 for r in rows if r[1] >= 21),
            "lapsed": sum(1 for r in rows if r[3] > 0),
            "today": sum(1 for r in rows if now < datetime.fromisoformat(r[2]) <= now + timedelta(days=1)),
            "week": sum(1 for r in rows if now + timedelta(days=1) < datetime.fromisoformat(r[2]) <= now + timedelta(days=7)),
            "next_in": label((nxt - now).total_seconds() / 86400) if nxt else None}
