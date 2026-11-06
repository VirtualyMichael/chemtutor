# ChemTutor

A free, private chemistry study app that runs entirely on your own computer. Practice from basic units up to AP-level
problems, get hints and explanations from a **local AI model** (no accounts, nothing leaves your machine), take timed
mock exams, and look anything up on a built-in cheat sheet.

[![tests](https://github.com/VirtualyMichael/chemtutor/actions/workflows/tests.yml/badge.svg)](https://github.com/VirtualyMichael/chemtutor/actions/workflows/tests.yml)

## What you get

- **Learn mode (teach me, don't just test me)**: watch the free [Crash Course Chemistry](https://www.youtube.com/playlist?list=PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr) videos inside the app.
  ChemTutor reads their captions, so it knows what each episode taught, and builds study notes with timestamps, "watch for"
  questions, comprehension checks marked against the transcript, a tutor that answers from the videos (with citations),
  and practice problems that unlock for the topics you have covered.
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
- **On your Android phone**: an installable app that talks to your computer, so your progress is always the same on both and the tutor still runs on your own AI. See [Use it on your phone](#use-it-on-your-android-phone).
- **Progress dashboard** with topic mastery, review schedule, exam and free-response scores.

## Learn from the beginning (Crash Course Chemistry)

Open the **Learn** tab and click **Load Crash Course Chemistry**. (First time only, ChemTutor offers to install `yt-dlp`, a free
open-source tool that reads YouTube captions. Loading all 47 episodes takes about 3 minutes.) Then, for each episode:

1. **Watch** it in the app (the video is embedded; it needs an internet connection).
2. **Notes**: one click makes study notes from what the episode says: questions to watch for, key terms, and a timestamped
   outline. Click a timestamp to jump the video there.
3. **Check yourself**: the AI asks a question drawn from the transcript, marks your answer, and shows the video's own answer.
4. **Ask**: ask anything; answers come from the videos first, cite `[Ep 6 @ 5:00]`, and say when something is beyond the videos.
5. **Mark it watched** and the matching practice topics unlock (**Practice** and **Mock Exam** can show only what you have covered).

Command line: `python chemtutor.py course add [YouTube link]` loads any playlist or video, `python chemtutor.py course list` shows progress.
You can also paste a transcript yourself in the Learn tab.

**About the captions:** they belong to their creators. ChemTutor saves them only on your computer (in `library/`) for your own study; they are
never part of this repository or the release download. Notes, questions and answers are written by your local AI model from the
transcript: it can make mistakes, so every item shows a timestamp to check against the video.

## Install (Windows)

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/> (tick *Add python.exe to PATH*). No extra
   packages are needed.
2. Download the latest **ChemTutor zip** from the [Releases page](https://github.com/VirtualyMichael/chemtutor/releases/latest)
   and extract it anywhere.
3. Double-click **`Install ChemTutor.bat`**. It checks your setup, offers to set up the AI tutor, and puts a
   **ChemTutor shortcut on your Desktop** (and Start menu).
4. Double-click the shortcut. Your browser opens at <http://127.0.0.1:8765>. Close the small black window to stop the app.

### The AI tutor (optional but recommended)

Hints, explanations, "check my work", Learn-mode notes and free-response feedback use a model running on your computer.
**Ollama and LM Studio both work**, and ChemTutor finds whichever is running:

- **Ollama** (free, [download](https://ollama.com/download)): the installer offers the default model, `qwen2.5:7b`
  (about 4.7 GB, one time), or run `ollama pull qwen2.5:7b`.
- **LM Studio** ([download](https://lmstudio.ai)): download any chat model in its Discover tab, then open the **Developer**
  tab and turn on **Start server** (port 1234). You can load bigger and newer models there than most people run in Ollama.

Click the **model badge** (top right of the app) to see every model your servers offer and pick one. If you do not pick,
ChemTutor chooses a plain chat model of up to about 14B parameters (bigger ones are often too slow at home), and switches
by itself if the server you were using goes away. Your choice is remembered. A phone paired to your computer can see the
model but only the computer itself can change it.

Tips: **reasoning models** (those that "think" first) work, but ChemTutor asks LM Studio to skip the thinking because a
tutor hint does not need it (4 seconds instead of 2 minutes in our test). 7-14B models are a good balance; 30B+ models
explain better but answer slowly unless you have a strong GPU. Embedding and speech models are ignored.

Without an AI everything else still works: practice, grading, spaced repetition, mock exams, free-response checking
and the cheat sheet.

Force a server or model from the command line (this overrides the badge):

```bash
python chemtutor.py --llm-url lmstudio --model qwen2.5-7b-instruct
python chemtutor.py --llm-url ollama --model llama3.1:8b
python chemtutor.py --llm-url http://localhost:1234/v1      # any OpenAI-compatible server
```

Even good models can make arithmetic slips. That is why answers are checked in code and the solutions to generated
problems are computed rather than asked of the model.

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

## Use it on your Android phone

ChemTutor installs on your phone as an app (a PWA: it has its own icon and opens full screen). It does not copy your data:
the phone is a window onto ChemTutor running on your computer, so **progress, reviews and exams are the same on both with
no syncing to break**, and the AI tutor and Crash Course notes use your own local model.

1. Install the free [Tailscale](https://tailscale.com/download) app on your computer **and** your phone and sign in to both
   with the same account. (This is what lets the phone reach your computer from anywhere, privately. On the same Wi-Fi you can skip it.)
2. On your computer double-click **`Phone Setup.bat`** (or run `python chemtutor.py phone`). It prints a link.
3. Restart ChemTutor if it was already open, then open that link once in Chrome on your phone. The phone is now paired.
4. For the full app experience, run the `tailscale serve` command that step 2 prints (once), open the `https://` link on the
   phone and choose Chrome menu, **Install app**. Without it, **Add to Home screen** still gives you a shortcut.

Good to know:

- Your computer has to be on, with ChemTutor (and Ollama for the AI) running. If not, the phone shows "Can't reach your computer".
  The cheat sheet stays available offline.
- The link contains a secret key. Anyone who has it can use your ChemTutor, so do not share it. `python chemtutor.py phone reset`
  makes a new one (you pair again), and `python chemtutor.py phone off` turns phone access off.
- Phone access is off until you run the setup, and when it is off ChemTutor listens on your computer only. When it is on, every
  device except the computer itself must present the key. Windows may ask once whether Python may use the network: allow it for private networks.
- A mock exam started on the phone is also locked on the computer, because they share one set of progress.

## Your data

Progress, spaced-repetition schedule, exam and free-response history are stored in one SQLite file under the
`library/` folder next to the app (or in the folder named by the `CHEMTUTOR_HOME` environment variable). Back it up by
copying that folder; reset by deleting it. To update, extract a new release over the old folder: `library/` is not in the
zip, so your progress is kept.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Python was not found" | Install Python 3.10+ and tick *Add to PATH*, then run the installer again. |
| Badge says **AI offline** | Start Ollama, or in LM Studio turn on *Developer > Start server*, then reload the page. ChemTutor also finds LM Studio when its server is set to listen on your Wi-Fi or Tailscale address instead of localhost. Run `python chemtutor.py doctor`. |
| Badge says **Choose a model** | The server is running but the model you chose is gone. Click the badge and pick one (or `ollama pull qwen2.5:7b`). |
| "Port 8765 is in use" | `python chemtutor.py --port 8766` |
| Learn tab asks to install `yt-dlp` | Click Install, or `python -m pip install --user yt-dlp`. Captions are fetched only from YouTube, from your computer. |
| Learn tab says captions failed (HTTP 429) | YouTube rate-limited you. Wait a few minutes and run `python chemtutor.py course add` again; it skips videos it already has. |
| Phone says "not paired" or "Can't reach your computer" | Run `python chemtutor.py phone` again and open the new link; make sure ChemTutor is running on the computer and Tailscale is connected on both devices. |
| An old ChemTutor keeps opening after an update | Start ChemTutor again: it now replaces an older running copy by itself. `python chemtutor.py stop` (or `Stop ChemTutor.bat`) stops it; closing its window does too. |
| Shortcut missing | Run `python setup.py` again, or start with `Start ChemTutor.bat`. |

## Development

```bash
python -m unittest tests.test_learn tests.test_server tests.test_frq tests.test_generated tests.test_exams tests.test_hints tests.test_remote tests.test_aiconfig tests.test_launcher
python scripts/generate_problems.py     # regenerate data/problems/generated.json (deterministic)
python scripts/build_frq.py             # regenerate data/frq/ap_frq.json
python scripts/make_icon.py             # redraw assets/chemtutor.ico
python scripts/build_release.py         # build dist/ChemTutor-<version>.zip
```

- `app/` : server (`web.py`), spaced repetition (`srs.py`), exams (`exams.py`), hint rules (`hints.py`),
  free response (`frq.py`), Learn mode (`learn.py`: captions, notes, checks, video-grounded tutor), cheat sheet content (`reference.py`), shared periodic table + formula parser (`chem.py`).
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
- Video captions loaded by Learn mode belong to their creators and stay on your computer; this project does not include or redistribute them. Crash Course is a trademark of its owners, who are not affiliated with this project.
- Study aid only. The AI can be wrong; trust the answer keys and your teacher or textbook.
