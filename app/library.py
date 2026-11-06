from __future__ import annotations
import hashlib, json, os, re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Progress database and the optional ingested textbook live here. Set CHEMTUTOR_HOME to keep them elsewhere.
HOME = Path(os.environ.get("CHEMTUTOR_HOME") or ROOT / "library")
DB = HOME / "index" / "science_teacher.sqlite3"
TEXT = HOME / "text"
META = HOME / "metadata"

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY, sha256 TEXT UNIQUE, title TEXT, path TEXT, pages INTEGER, license_note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS pages(source_id INTEGER, page INTEGER, text_path TEXT, text TEXT, PRIMARY KEY(source_id,page));
    CREATE TABLE IF NOT EXISTS study_progress(topic TEXT PRIMARY KEY, mastery REAL DEFAULT 0, notes TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(source_id UNINDEXED, page UNINDEXED, title, text);
    ''')
    return db

def search(query: str, limit=8):
    db = connect()
    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms: return []
    q = " OR ".join(terms)
    try:
        rows = db.execute("SELECT source_id,page,title,text FROM pages_fts WHERE pages_fts MATCH ? LIMIT ?", (q, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    return [dict(r) for r in rows]

def sources():
    return [dict(r) for r in connect().execute("SELECT * FROM sources ORDER BY title").fetchall()]

def excerpt(source_id: int, page: int, max_chars=3000):
    row = connect().execute("SELECT sources.title,sources.path,pages.page,pages.text FROM pages JOIN sources ON sources.id=pages.source_id WHERE source_id=? AND page=?", (source_id,page)).fetchone()
    if not row: return None
    text = row[3]
    return {"title": row[0], "path": row[1], "page": row[2], "text": text[:max_chars], "citation": f"{row[0]}, p. {row[2]}"}

def record_progress(topic, mastery=0, notes=""):
    db = connect()
    db.execute("INSERT INTO study_progress(topic,mastery,notes) VALUES(?,?,?) ON CONFLICT(topic) DO UPDATE SET mastery=excluded.mastery,notes=excluded.notes,updated_at=CURRENT_TIMESTAMP", (topic, mastery, notes))
    db.commit()
