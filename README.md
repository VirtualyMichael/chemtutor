# ChemTutor

A free, private chemistry study app that runs entirely on your own computer. Practice from basic units up to AP-level
problems, get hints and explanations from a **local AI model** (no accounts, nothing leaves your machine), take timed
mock exams, and look anything up on a built-in cheat sheet.

[![tests](https://github.com/VirtualyMichael/chemtutor/actions/workflows/tests.yml/badge.svg)](https://github.com/VirtualyMichael/chemtutor/actions/workflows/tests.yml)

## What you get

- **386 practice problems, levels 1-5**, from significant figures to ICE tables, Nernst and thermodynamics. Every answer
  is **graded by code against a computed or official answer key**, never by the AI. Generated problems come with worked steps.
- **Guided tutor**: a 4-level hint ladder (the server checks every hint and rejects any that give away the answer),
  "check my work", concept explanations, and full worked solutions.
- **Spaced repetition**: problems you miss come back at the right time; a "Review N due" queue and a schedule view.
- **Closed-book mock exams**: timed, autosaved, resumable after a refresh. The tutor is locked until you submit, then
  every question is reviewed. Optionally allow the formula sheet, like AP and ACS exams.
- **AP-style free response**: 10 original multi-part questions (79 points) with rubrics. Numeric parts are checked for
  you, you score the written parts against the rubric, and the AI can give feedback (you decide the score).
- **Cheat sheet** (press `?`): formulas, step-by-step algorithms (limiting reagent, ICE tables, Hess's law, ...),
  notation, constants, ion tables, solubility rules, VSEPR, reduction potentials, and a periodic table with atomic masses.
- **Progress dashboard** with topic mastery, review schedule, exam and free-response scores.

## Install (Windows)

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/> (tick *Add python.exe to PATH*). No extra
   packages are needed.
2. Download the latest **ChemTutor zip** from the [Releases page](https://github.com/VirtualyMichael/chemtutor/releases/latest)
   and extract it anywhere.
3. Double-click **`Install ChemTutor.bat`**. It checks your setup, offers to set up the AI tutor, and puts a
   **ChemTutor shortcut on your Desktop** (and Start menu).
4. Double-click the shortcut. Your browser opens at <http://127.0.0.1:8765>. Close the small black window to stop the app.

### The AI tutor (optional but recommended)

Hints, explanations, "check my work" and free-response feedback use a model running on your computer through
[Ollama](https://ollama.com/download) (free). The installer offers to download the default model, `qwen2.5:7b`
(about 4.7 GB, one time). Or do it yourself:

```bash
ollama pull qwen2.5:7b
```

Without Ollama everything else still works: practice, grading, spaced repetition, mock exams, free-response checking
and the cheat sheet. A small badge in the top bar shows whether the AI is ready.

Use a different model or server (for example LM Studio) with flags:

```bash
python chemtutor.py --model llama3.1:8b
python chemtutor.py --llm-url http://localhost:1234/v1 --model your-loaded-model
```

A 7B model is good for explanations but can make arithmetic slips. That is why answers are checked in code and the
solutions to generated problems are computed rather than asked of the model.

## Other systems / manual start

```bash
python chemtutor.py            # start and open the browser   (python3 on macOS/Linux)
python chemtutor.py doctor     # check Python, data, port and AI model
python setup.py                # same interactive setup the Windows installer runs
```

Options: `--port 8765`, `--model NAME`, `--llm-url URL`, `--no-browser`. Only Windows 11 + Python 3.12 has been tried by
hand; the automated tests also run on Linux and Python 3.10-3.12 (see the badge). macOS/Linux shortcut creation in
`setup.py` is untested.

### Optional: textbook citations

The "Explain the concept" button can cite pages from a textbook you index locally. For example, download the free
[OpenStax Chemistry 2e PDF](https://openstax.org/details/books/chemistry-2e) and run:

```bash
python chemtutor.py ingest path/to/chemistry-2e.pdf
```

(This installs the small `pypdf` package the first time.)

## Your data

Progress, spaced-repetition schedule, exam and free-response history are stored in one SQLite file under the
`library/` folder next to the app (or in the folder named by the `CHEMTUTOR_HOME` environment variable). Back it up by
copying that folder; reset by deleting it. To update, extract a new release over the old folder: `library/` is not in the
zip, so your progress is kept.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Python was not found" | Install Python 3.10+ and tick *Add to PATH*, then run the installer again. |
| Badge says **AI offline** | Start the Ollama app, then reload the page. Run `python chemtutor.py doctor`. |
| Badge says **model not installed** | `ollama pull qwen2.5:7b` (or pass `--model` for one you have). |
| "Port 8765 is in use" | `python chemtutor.py --port 8766` |
| Shortcut missing | Run `python setup.py` again, or start with `Start ChemTutor.bat`. |

## Development

```bash
python -m unittest tests.test_server tests.test_frq tests.test_generated tests.test_exams tests.test_hints
python scripts/generate_problems.py     # regenerate data/problems/generated.json (deterministic)
python scripts/build_frq.py             # regenerate data/frq/ap_frq.json
python scripts/make_icon.py             # redraw assets/chemtutor.ico
python scripts/build_release.py         # build dist/ChemTutor-<version>.zip
```

- `app/` : server (`web.py`), spaced repetition (`srs.py`), exams (`exams.py`), hint rules (`hints.py`),
  free response (`frq.py`), cheat sheet content (`reference.py`), shared periodic table + formula parser (`chem.py`).
- `web/index.html` : the whole front end (no build step, no dependencies).
- `data/problems/` : `starter.json` (hand-written), `openstax.json` (imported), `generated.json` (computed).
  `data/frq/ap_frq.json`: free-response questions.
- The server only listens on `127.0.0.1`; nothing is sent over the network except requests to your local AI server.

Adding problems: add a JSON file to `data/problems/` with `id, topic, level, question, answer, tolerance_rel|abs, steps`
(see any existing file); it is picked up on the next page load.

## Content and licenses

- Code: [MIT](LICENSE).
- Problems with ids starting `ox-` are adapted from **Chemistry 2e** by OpenStax, licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (<https://openstax.org/details/books/chemistry-2e>);
  see [NOTICE](NOTICE). The hand-written, generated and free-response content is original.
- The free-response questions imitate the *format* of AP Chemistry exams. They are not College Board questions. AP is a
  trademark of the College Board, which is not affiliated with this project.
- Study aid only. The AI can be wrong; trust the answer keys and your teacher or textbook.
