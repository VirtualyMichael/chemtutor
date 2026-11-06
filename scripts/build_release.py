"""Build dist/ChemTutor-<version>.zip (+ .sha256) from the files git tracks, so the release matches the repo.

Leaves out developer-only files (tests, CI config). Adds a plain-text START HERE.txt for non-technical users.
Run:  python scripts/build_release.py
"""
from __future__ import annotations
import hashlib, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import __version__  # noqa: E402

SKIP_PREFIX = (".github/", "tests/")
SKIP_NAMES = {".gitignore", ".gitattributes"}

START_HERE = """ChemTutor {v}  -  START HERE
================================

1. You need Python 3.10 or newer (free): https://www.python.org/downloads/
   During install, tick "Add python.exe to PATH".

2. Double-click:   Install ChemTutor.bat
   It checks everything, offers to set up the AI tutor, and puts a ChemTutor icon on your Desktop.

3. Double-click the ChemTutor icon. Your browser opens the app. Close the small black window to stop it.

The AI tutor (hints, explanations) uses Ollama, a free program: https://ollama.com/download
Everything else works without it. Full instructions: README.md

Not on Windows?  Run:  python3 chemtutor.py
Something wrong?  Run:  python chemtutor.py doctor
"""


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        print("warning: uncommitted changes are NOT included (the zip contains the working-tree copy of tracked files):\n" + dirty)
    files = [f for f in tracked if not f.startswith(SKIP_PREFIX) and f not in SKIP_NAMES and (ROOT / f).is_file()]
    top = f"ChemTutor-{__version__}"
    out = ROOT / "dist" / f"{top}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(f"{top}/START HERE.txt", START_HERE.format(v=__version__).replace("\n", "\r\n"))
        for f in files:
            z.write(ROOT / f, f"{top}/{f}")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (out.parent / (out.name + ".sha256")).write_text(f"{digest}  {out.name}\n", encoding="utf-8")
    print(f"built {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.0f} KB, {len(files) + 1} files)")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
