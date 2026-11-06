from __future__ import annotations
import hashlib, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.library import connect, META, TEXT

def main(src_arg):
    src = Path(src_arg).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != '.pdf': raise SystemExit(f"PDF not found: {src}")
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("pypdf is required: python -m pip install pypdf") from e
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    db = connect()
    old = db.execute("SELECT id FROM sources WHERE sha256=?", (digest,)).fetchone()
    if old: print(json.dumps({"status":"already_indexed","source_id":old[0]})); return
    reader = PdfReader(str(src))
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else src.stem).strip()
    cur = db.execute("INSERT INTO sources(sha256,title,path,pages,license_note) VALUES(?,?,?,?,?)", (digest,title,str(src),len(reader.pages),"User-provided; verify usage rights"))
    sid = cur.lastrowid
    out = TEXT / digest[:16]; out.mkdir(parents=True, exist_ok=True)
    for n, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        path = out / f"page-{n:04d}.txt"; path.write_text(text, encoding='utf-8')
        db.execute("INSERT INTO pages VALUES(?,?,?,?)", (sid,n,str(path),text))
        db.execute("INSERT INTO pages_fts VALUES(?,?,?,?)", (sid,n,title,text))
    META.mkdir(parents=True, exist_ok=True)
    (META / f"{digest[:16]}.json").write_text(json.dumps({"sha256":digest,"title":title,"original_path":str(src),"pages":len(reader.pages)}, indent=2), encoding='utf-8')
    db.commit()
    print(json.dumps({"status":"indexed","source_id":sid,"title":title,"pages":len(reader.pages),"sha256":digest}))

if __name__ == '__main__': main(sys.argv[1])
