"""AP-style free-response practice: load questions, reveal rubric/answers, store self-scored attempts.

Numeric parts are checked in code; written parts are scored by the student against the rubric (the local model
can offer feedback, but it only suggests - the student decides). Public payloads never contain answers.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRQ_DIR = ROOT / "data" / "frq"


def load() -> dict[str, dict]:
    out = {}
    for f in sorted(FRQ_DIR.glob("*.json")):
        for q in json.loads(f.read_text(encoding="utf-8")):
            out[q["id"]] = q
    return out


def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS frq_attempts(
        id INTEGER PRIMARY KEY, frq_id TEXT, score INTEGER, max_score INTEGER, detail TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP)""")


def summary(q: dict, best: dict | None = None) -> dict:
    return {"id": q["id"], "title": q["title"], "kind": q.get("kind", "long"), "minutes": q.get("minutes"),
            "topics": q.get("topics", []), "points": q["points"], "parts": len(q["parts"]), "best": best}


def public(q: dict) -> dict:
    """Question as shown while answering: stem and part prompts only."""
    return {"id": q["id"], "title": q["title"], "minutes": q.get("minutes"), "points": q["points"], "stem": q["stem"],
            "parts": [{"label": p["label"], "type": p["type"], "prompt": p["prompt"], "points": p["points"]} for p in q["parts"]]}


def reveal(q: dict, answers: dict, check) -> dict:
    """Everything shown after the student commits: keys, solutions, rubric, and the code check of numeric parts."""
    parts = []
    for p in q["parts"]:
        mine = str(answers.get(p["label"], "")).strip()
        item = {"label": p["label"], "type": p["type"], "points": p["points"], "your_answer": mine, "rubric": [dict(r) for r in p["rubric"]]}
        if p["type"] == "numeric":
            res = check({"answer": p["answer"], "tolerance_rel": p.get("tolerance_rel", 0.01), "tolerance_abs": p.get("tolerance_abs", 0), "units": []}, mine) if mine else {"correct": False}
            item.update(answer_text=p["answer_text"], solution=p.get("solution", []), auto_correct=bool(res["correct"]))
            for r in item["rubric"]:
                r["preset"] = bool(r.get("auto") and res["correct"])
        else:
            item.update(model_answer=p["model_answer"])
            for r in item["rubric"]:
                r["preset"] = False
        parts.append(item)
    return {"id": q["id"], "title": q["title"], "points": q["points"], "parts": parts}


def score(q: dict, scores: dict) -> tuple[int, int, dict]:
    """scores: {label: [0/1 per rubric item]}. Returns (earned, max, per-part earned). Unknown/short input counts as 0."""
    earned, detail = 0, {}
    for p in q["parts"]:
        marks = scores.get(p["label"], [])
        e = sum(r["pts"] for r, m in zip(p["rubric"], marks) if m)
        detail[p["label"]] = e
        earned += e
    return earned, q["points"], detail


def save(con, q: dict, scores: dict, answers: dict) -> dict:
    earned, mx, detail = score(q, scores)
    con.execute("INSERT INTO frq_attempts(frq_id,score,max_score,detail) VALUES(?,?,?,?)",
                (q["id"], earned, mx, json.dumps({"parts": detail, "answers": answers})))
    con.commit()
    return {"score": earned, "max": mx, "parts": detail}


def best_scores(con) -> dict:
    return {r[0]: {"score": r[1], "max": r[2]} for r in con.execute(
        "SELECT frq_id, MAX(score), max_score FROM frq_attempts GROUP BY frq_id")}


def history(con, limit=15) -> list:
    return [{"id": r[0], "frq_id": r[1], "score": r[2], "max": r[3], "ts": r[4]} for r in con.execute(
        "SELECT id,frq_id,score,max_score,ts FROM frq_attempts ORDER BY id DESC LIMIT ?", (limit,))]


def feedback_messages(q: dict, part: dict, answer: str) -> list[dict]:
    rubric = "\n".join(f"{i + 1}. ({r['pts']} pt) {r['text']}" for i, r in enumerate(part["rubric"]))
    ref = part.get("model_answer") or " ".join(part.get("solution", []))
    sys = ("You are an AP Chemistry exam reader giving short feedback on one part of a free-response answer. "
           "Go through the rubric items one by one and write 'Earned' or 'Missing' for each with a one-sentence reason "
           "that points at the student's words. Be strict: mark Earned only if the response explicitly states the idea. "
           "Never invent things the student did not write. Plain text, under 120 words, no LaTeX.")
    user = (f"Question context: {q['stem']}\nPart {part['label']}: {part['prompt']}\n\nRubric:\n{rubric}\n\n"
            f"Reference answer (for grading only): {ref}\n\nStudent response:\n{answer or '(blank)'}")
    return [{"role": "system", "content": sys}, {"role": "user", "content": user}]
