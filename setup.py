#!/usr/bin/env python3
"""ChemTutor setup: checks requirements, offers to prepare the local AI model, creates shortcuts, can launch the app.

    python setup.py                 interactive (asks before anything big)
    python setup.py --yes           accept every prompt (including the ~4.7 GB model download)
    python setup.py --no-model --no-shortcut --no-launch    only check things

Safe to run again. Nothing is installed without asking: it only opens download pages, runs `ollama pull`, and writes
shortcut files for ChemTutor itself.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, urllib.request, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
LLM_URL = os.environ.get("LLM_URL", "http://localhost:11434/v1")
ICON, PNG = ROOT / "assets" / "chemtutor.ico", ROOT / "assets" / "chemtutor.png"
IS_WIN, IS_MAC = sys.platform == "win32", sys.platform == "darwin"


def say(m: str = "") -> None:
    print(m, flush=True)


def step(title: str) -> None:
    say(f"\n== {title}")


class Ask:
    def __init__(self, yes: bool):
        self.yes = yes

    def __call__(self, question: str, default: bool = True, big: bool = False) -> bool:
        if self.yes:
            return True
        if not sys.stdin or not sys.stdin.isatty():
            return default and not big
        hint = "Y/n" if default else "y/N"
        try:
            a = input(f"{question} [{hint}] ").strip().lower()
        except EOFError:
            return default and not big
        return default if not a else a.startswith("y")


def find_ollama() -> str | None:
    p = shutil.which("ollama")
    if p:
        return p
    for c in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe", Path("/usr/local/bin/ollama"),
              Path("/opt/homebrew/bin/ollama"), Path("/Applications/Ollama.app/Contents/Resources/ollama")):
        if c.is_file():
            return str(c)
    return None


def llm_models() -> list[str] | None:
    try:
        with urllib.request.urlopen(LLM_URL.rstrip("/") + "/models", timeout=2) as r:
            return [m.get("id", "") for m in json.load(r).get("data", [])]
    except Exception:
        return None


def check_python() -> bool:
    step("Python")
    v = sys.version_info
    if (v.major, v.minor) < (3, 10):
        say(f"Python {v.major}.{v.minor} is too old. ChemTutor needs 3.10 or newer: https://www.python.org/downloads/")
        return False
    say(f"OK: Python {v.major}.{v.minor}.{v.micro} (no extra packages are needed)")
    return True


def check_app() -> bool:
    step("ChemTutor files")
    sys.path.insert(0, str(ROOT))
    try:
        from app import __version__, frq, web
        say(f"OK: ChemTutor {__version__}: {len(web.load_problems())} practice problems, {len(frq.load())} free-response questions")
        return True
    except Exception as e:  # noqa: BLE001
        say(f"Problem loading the app: {e}\nRe-download the release and extract the whole folder.")
        return False


def check_ai(ask: Ask, no_model: bool) -> None:
    step("Local AI tutor (Ollama or LM Studio)")
    sys.path.insert(0, str(ROOT))
    from app import aiconfig
    ready = [b for b in aiconfig.detect() if b["up"] and b["models"]]
    if ready:
        b = ready[0]
        say(f"OK: {b['name']} is running with {len(b['models'])} model(s). ChemTutor picks one automatically;")
        say("you can change it any time from the model badge (top right of the app).")
        return
    say("(No AI server with models found yet. Ollama or LM Studio both work.)")
    ollama = find_ollama()
    names = llm_models()
    if names is not None and any(n == MODEL for n in names):
        say(f"OK: the AI server is running and '{MODEL}' is installed.")
        return
    if not ollama and names is None:
        say("Ollama (the free program that runs the AI on your computer) was not found.")
        say("The app works without it (practice, exams, cheat sheet, free-response checking), but hints,")
        say("explanations and AI feedback need it.")
        if ask("Open the Ollama download page now?", default=True):
            webbrowser.open("https://ollama.com/download")
        say(f"After installing Ollama, run this setup again (or just run:  ollama pull {MODEL}).")
        return
    if names is None:
        say("Ollama is installed but not running. Start the Ollama app (Start menu on Windows), then run setup again.")
    if not ollama:
        say(f"The AI server is running but '{MODEL}' is not installed. Install it with:  ollama pull {MODEL}")
        return
    have = subprocess.run([ollama, "list"], capture_output=True, text=True).stdout
    if any(line.split()[:1] == [MODEL] for line in have.splitlines()):
        say(f"OK: '{MODEL}' is installed.")
        return
    say(f"The tutor model '{MODEL}' is not installed yet (about 4.7 GB, one-time download).")
    if no_model:
        say(f"Skipped. Install later with:  ollama pull {MODEL}")
    elif ask("Download it now?", default=True, big=True):
        say(f"Running: ollama pull {MODEL}  (this can take a while)")
        rc = subprocess.call([ollama, "pull", MODEL])
        say("OK: model ready." if rc == 0 else f"The download did not finish. Try again with:  ollama pull {MODEL}")
    else:
        say(f"Skipped. Install later with:  ollama pull {MODEL}")


def offer_course(ask: Ask, skip: bool) -> None:
    step("Learn mode: Crash Course Chemistry")
    sys.path.insert(0, str(ROOT))
    from app import learn, web
    have = len(learn.course_overview(web.db())["videos"])
    if have:
        say(f"OK: {have} videos are already loaded.")
        return
    say("ChemTutor can teach alongside the free Crash Course Chemistry videos: it reads their captions (saved only on this")
    say("computer) so it knows what each episode taught. Loading all 47 takes about 3 minutes and needs the free 'yt-dlp' tool.")
    if skip or not ask("Load the Crash Course Chemistry captions now?", default=True, big=True):
        say("Skipped. You can do it later from the Learn tab, or:  python chemtutor.py course add")
        return
    if not learn.have_ytdlp():
        ok, msg = learn.install_ytdlp()
        say("OK: installed yt-dlp." if ok else f"Could not install yt-dlp ({msg}). Try:  python -m pip install --user yt-dlp")
        if not ok:
            return
    last = [""]

    def progress(done, total, m):
        if m != last[0]:
            last[0] = m
            say(f"  [{done}/{total}] {m}")
    res = learn.import_source(web.db(), learn.PLAYLIST_URL, progress)
    say(f"OK: {res['fetched']} captions fetched ({res['no_captions']} unavailable).")


def ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def windows_dirs() -> tuple[Path | None, Path | None]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                         capture_output=True, text=True).stdout.strip()
    desktop = Path(out) if out else Path.home() / "Desktop"
    appdata = os.environ.get("APPDATA")
    start = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" if appdata else None
    return desktop, start


def windows_shortcut(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    lnk = folder / "ChemTutor.lnk"
    bat = ROOT / "Start ChemTutor.bat"
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({ps_quote(str(lnk))});"
          f"$s.TargetPath={ps_quote(str(bat))};$s.WorkingDirectory={ps_quote(str(ROOT))};"
          f"$s.IconLocation={ps_quote(str(ICON))};$s.Description='ChemTutor - local chemistry study app';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
    return lnk


def make_shortcuts(ask: Ask) -> Path | None:
    step("Shortcuts")
    try:
        if IS_WIN:
            desktop, start = windows_dirs()
            made = None
            if ask("Put a ChemTutor shortcut on your Desktop?", default=True):
                made = windows_shortcut(desktop)
                say(f"OK: Desktop shortcut: {made}")
            if start and ask("Add ChemTutor to the Start menu too?", default=True):
                say(f"OK: Start menu shortcut: {windows_shortcut(start)}")
            return made
        if IS_MAC:
            target = Path.home() / "Desktop" / "ChemTutor.command"
            target.write_text(f'#!/bin/bash\ncd "{ROOT}"\npython3 chemtutor.py\n', encoding="utf-8")
            target.chmod(0o755)
            say(f"OK: Desktop launcher: {target} (macOS support is untested)")
            return target
        desk = Path.home() / ".local" / "share" / "applications" / "chemtutor.desktop"
        desk.parent.mkdir(parents=True, exist_ok=True)
        desk.write_text("[Desktop Entry]\nType=Application\nName=ChemTutor\nComment=Local chemistry study app\n"
                        f'Exec=sh -c \'cd "{ROOT}" && python3 chemtutor.py\'\nIcon={PNG}\nTerminal=true\nCategories=Education;Science;\n', encoding="utf-8")
        say(f"OK: application launcher: {desk} (Linux support is untested)")
        return desk
    except Exception as e:  # noqa: BLE001
        say(f"Could not create the shortcut ({e}). You can always start ChemTutor with:  python chemtutor.py")
        return None


def launch() -> None:
    if IS_WIN:
        os.startfile(str(ROOT / "Start ChemTutor.bat"))  # type: ignore[attr-defined]
    else:
        subprocess.Popen([sys.executable, str(ROOT / "chemtutor.py")], cwd=ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description="ChemTutor setup")
    ap.add_argument("--yes", "-y", action="store_true", help="accept all prompts (including the model download)")
    ap.add_argument("--no-model", action="store_true", help="never download the AI model")
    ap.add_argument("--no-course", action="store_true", help="do not offer to load the Crash Course captions")
    ap.add_argument("--no-shortcut", action="store_true")
    ap.add_argument("--no-launch", action="store_true")
    args = ap.parse_args()
    ask = Ask(args.yes)
    say("ChemTutor setup")
    if not check_python() or not check_app():
        return 1
    check_ai(ask, args.no_model)
    offer_course(ask, args.no_course)
    if not args.no_shortcut:
        make_shortcuts(ask)
    step("Done")
    say("Start ChemTutor from the shortcut, or run:  python chemtutor.py")
    say("Check everything any time with:  python chemtutor.py doctor")
    if not args.no_launch and ask("Start ChemTutor now?", default=True):
        launch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
