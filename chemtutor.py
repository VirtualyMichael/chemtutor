#!/usr/bin/env python3
"""ChemTutor launcher.

    python chemtutor.py             start the app and open it in your browser
    python chemtutor.py doctor      check that everything is set up (Python, data, AI model, port)
    python chemtutor.py ingest FILE.pdf   index a textbook PDF so the tutor can cite pages (optional)
    python chemtutor.py course add [URL]  fetch video captions for Learn mode (default: Crash Course Chemistry)
    python chemtutor.py course list       show the videos you have loaded and your progress
    python chemtutor.py phone             set up the phone app: prints the link to open on your Android phone
    python chemtutor.py phone off         turn phone access off again (phone reset: make old links stop working)

Options: --port 8765  --model qwen2.5:7b  --llm-url http://localhost:11434/v1  --no-browser
Any OpenAI-compatible local server works (Ollama by default; for LM Studio use --llm-url http://localhost:1234/v1).
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, threading, time, urllib.request, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_PY = (3, 10)
OLLAMA_URL = "https://ollama.com/download"


def say(msg: str = "") -> None:
    print(msg, flush=True)


def fetch_json(url: str, timeout: float = 1.5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def chemtutor_at(port: int):
    """Health dict if a ChemTutor server is already answering on this port, else None."""
    try:
        cfg = fetch_json(f"http://127.0.0.1:{port}/api/health", timeout=3)
        return cfg if isinstance(cfg, dict) and cfg.get("app") == "chemtutor" else None
    except Exception:
        return None


def port_busy(port: int) -> bool:
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ai_tips(web) -> list[str]:
    up, have, names = web.llm_status(force=True)
    if have:
        return [f"AI tutor ready: {web.LLM_MODEL}"]
    if up:
        return [f"The AI server is running but '{web.LLM_MODEL}' is not installed.",
                f"  Install it once with:  ollama pull {web.LLM_MODEL}",
                f"  (or choose an installed model with --model; installed: {', '.join(names) or 'none'})"]
    return [f"AI tutor not detected at {web.LLM_URL}.",
            f"  Hints, explanations and AI feedback need a local model. Install Ollama from {OLLAMA_URL}",
            f"  then run:  ollama pull {web.LLM_MODEL}",
            "  Practice problems, mock exams, the cheat sheet and free-response checking work without it."]


def cmd_run(args, web) -> int:
    port = web.PORT
    url = f"http://127.0.0.1:{port}"
    if chemtutor_at(port):
        say(f"ChemTutor is already running at {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0
    if port_busy(port):
        say(f"Port {port} is in use by another program. Try:  python chemtutor.py --port {port + 1}")
        return 1
    from app import remote
    phone = remote.enabled()
    server = web.make_server(remote_access=phone)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    for _ in range(40):
        if chemtutor_at(port):
            break
        time.sleep(0.1)
    from app import __version__
    say(f"ChemTutor {__version__} is running at {url}")
    for line in ai_tips(web):
        say(line)
    if phone:
        say("Phone access is ON. For the link to open on your phone run:  python chemtutor.py phone")
    say("Close this window (or press Ctrl+C) to stop ChemTutor.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        say("\nStopping ChemTutor. Your progress is saved.")
        server.shutdown()
    return 0


def cmd_doctor(args, web) -> int:
    from app import __version__, library
    problems_ok = True
    say(f"ChemTutor {__version__} doctor")
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PY
    say(f"[{'ok' if ok else '!!'}] Python {v.major}.{v.minor}.{v.micro} (needs {MIN_PY[0]}.{MIN_PY[1]}+)")
    problems_ok &= ok
    try:
        probs, frqs = web.load_problems(), web.frq.load()
        say(f"[ok] {len(probs)} practice problems, {len(frqs)} free-response questions loaded")
    except Exception as e:  # noqa: BLE001
        say(f"[!!] could not load the problem files: {e}")
        problems_ok = False
    try:
        library.DB.parent.mkdir(parents=True, exist_ok=True)
        say(f"[ok] progress is saved in {library.DB.parent}")
    except OSError as e:
        say(f"[!!] cannot write to {library.DB.parent}: {e}")
        problems_ok = False
    running = chemtutor_at(web.PORT)
    say(f"[ok] ChemTutor is running on port {web.PORT}" if running else
        f"[{'ok' if not port_busy(web.PORT) else '!!'}] port {web.PORT} is {'free' if not port_busy(web.PORT) else 'used by another program (use --port)'}")
    tips = ai_tips(web)
    say(("[ok] " if tips[0].startswith("AI tutor ready") else "[--] ") + tips[0])
    for line in tips[1:]:
        say("     " + line)
    try:
        from app import learn
        vids = learn.course_overview(web.db())["videos"]
        say(f"[--] Learn mode: {sum(v['has_transcript'] for v in vids)} of {len(vids)} videos have captions loaded"
            + ("" if vids else "  (open the Learn tab, or: python chemtutor.py course add)"))
        say(f"[{'ok' if learn.have_ytdlp() else '--'}] caption reader (yt-dlp): " + ("installed" if learn.have_ytdlp() else "not installed (the Learn tab offers to install it)"))
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.library import sources
        n = len(sources())
        say(f"[--] textbook citations: {n} source(s) indexed" + ("" if n else "  (optional: python chemtutor.py ingest <OpenStax Chemistry 2e PDF>)"))
    except Exception:  # noqa: BLE001
        pass
    return 0 if problems_ok else 1


def cmd_ingest(args, web) -> int:
    if not args.file:
        say("Usage: python chemtutor.py ingest path/to/textbook.pdf")
        return 1
    try:
        import pypdf  # noqa: F401
    except ImportError:
        say("Installing the 'pypdf' package (needed only to read PDFs)...")
        if subprocess.call([sys.executable, "-m", "pip", "install", "--user", "pypdf"]) != 0:
            say("Could not install pypdf. Run:  python -m pip install pypdf")
            return 1
    sys.path.insert(0, str(ROOT / "scripts"))
    import ingest_pdf
    ingest_pdf.main(args.file)
    return 0


def cmd_course(args, web) -> int:
    from app import learn
    con = web.db()
    action = args.file or "list"
    if action == "list":
        ov = learn.course_overview(con)
        if not ov["videos"]:
            say("No videos loaded yet. Run:  python chemtutor.py course add")
            return 0
        v = ov["videos"]
        say(f"{len(v)} videos, {sum(x['has_transcript'] for x in v)} with transcripts, "
            f"{sum(x['status'] != 'new' for x in v)} watched, {sum(x['has_notes'] for x in v)} with notes")
        say("Practice unlocked for: " + (", ".join(ov["covered"]) or "nothing yet (mark lessons watched in the Learn tab)"))
        return 0
    if action != "add":
        say("Usage: python chemtutor.py course add [YOUTUBE_URL]   |   python chemtutor.py course list")
        return 1
    url = args.extra or learn.PLAYLIST_URL
    if not learn.have_ytdlp():
        say("Reading captions needs 'yt-dlp', a free open-source tool.")
        if input("Install it now with pip (for your user only)? [Y/n] ").strip().lower() not in ("", "y", "yes"):
            return 1
        ok, msg = learn.install_ytdlp()
        if not ok:
            say("Install failed: " + msg)
            return 1
    last = [""]

    def progress(done, total, msg):
        if msg != last[0]:
            last[0] = msg
            say(f"[{done}/{total}] {msg}")

    res = learn.import_source(con, url, progress)
    say(f"Done: {res['fetched']} fetched, {res['already_had']} already had, {res['no_captions']} without captions "
        f"(of {res['videos']} videos). Captions are stored only on this computer.")
    return 0


def cmd_phone(args, web) -> int:
    from app import remote
    action = (args.file or "on").lower()
    port = web.PORT
    if action == "off":
        remote.set_enabled(False)
        say("Phone access is off. Restart ChemTutor for it to take effect (it then listens on this computer only).")
        return 0
    if action == "reset":
        remote.reset_token()
        say("New access key created. Every phone has to be paired again with the link below.")
    elif action not in ("on", "show", "reset"):
        say("Usage: python chemtutor.py phone [on|off|reset]")
        return 1
    was = remote.enabled()
    remote.set_enabled(True)
    running = chemtutor_at(port)
    links = remote.pairing_links(port)
    say("")
    say("ChemTutor on your phone")
    say("=======================")
    if not links:
        say("No network address found. Connect this computer to Wi-Fi (or install Tailscale) and run this again.")
        return 1
    ts = remote.tailscale_info()
    say("Open ONE of these links on your Android phone (in Chrome), once. The phone then stays paired:")
    say("")
    for l in links:
        say(f"  {l['label']}:")
        say(f"    {l['url']}")
    say("")
    if ts:
        host = ts.get("dns") or ts["ip"]
        say("Tailscale is connected here. For a real installable app with a home-screen icon, run this once")
        say(f"(it adds a secure https address, then open https://{host}/?key=... on the phone):")
        say(f"    tailscale serve --bg --https=443 http://127.0.0.1:{port}")
    else:
        say("To use it away from home (mobile data, school, work), install the free Tailscale app on this computer")
        say("and on your phone, sign in to both with the same account, then run this command again.")
        say("Tailscale: https://tailscale.com/download")
    say("")
    say("Notes: the computer must be on and running ChemTutor (and its AI) for the phone to work.")
    say("Treat the link like a password; anyone with it can use your ChemTutor. 'phone reset' replaces it.")
    if running and not was:
        say("")
        say("ChemTutor is already running. Close its window and start it again to switch phone access on.")
    elif not running:
        say("Now start ChemTutor (desktop shortcut) and the phone link will work.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ChemTutor launcher")
    ap.add_argument("command", nargs="?", default="run", choices=["run", "doctor", "ingest", "course", "phone"])
    ap.add_argument("file", nargs="?", help="PDF to index (ingest), or add/list (course)")
    ap.add_argument("extra", nargs="?", help="URL for: course add")
    ap.add_argument("--port", type=int)
    ap.add_argument("--model")
    ap.add_argument("--llm-url")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if sys.version_info < MIN_PY:
        say(f"ChemTutor needs Python {MIN_PY[0]}.{MIN_PY[1]} or newer (this is {sys.version.split()[0]}). Get it at https://www.python.org/downloads/")
        return 1
    # settings are read when app.web is imported, so set them first
    for key, val in (("PORT", args.port), ("LLM_MODEL", args.model), ("LLM_URL", args.llm_url)):
        if val:
            os.environ[key] = str(val)
    sys.path.insert(0, str(ROOT))
    from app import web
    return {"run": cmd_run, "doctor": cmd_doctor, "ingest": cmd_ingest, "course": cmd_course, "phone": cmd_phone}[args.command](args, web)


if __name__ == "__main__":
    sys.exit(main())
