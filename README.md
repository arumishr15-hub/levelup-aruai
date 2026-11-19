# 🌸 LevelUp_AruAI

Learn Python by playing. Two AI agents work together:

- **Question Agent:** writes a fresh "What does this code print?" question for your level, your weakest topics and your recent mistakes, or any topic you type.
- **Teacher Agent:** gives a mini-lesson with every question, explains your answer, steps through the code line by line, and answers anything in the **Ask the Teacher** chat. It never gives the answer away before you've tried.

**Every answer is checked by real Python.** Each question runs in your browser (Pyodide) before you see it. If the AI got the answer wrong, the app fixes the answer key first.

You earn XP and climb from *Python Hatchling* to *Python Master*. Three right in a row levels you up; the Teacher steers the Question Agent toward what you find hardest.

It's free to use, with no sign-up and no API key. If the AI is busy, the app switches to 161 built-in questions that are already checked by Python.

## How it works

```
browser (GitHub Pages)  ──►  relay (Cloudflare Worker, holds the key)  ──►  Groq (free AI models)
   └─ Pyodide runs and checks every question locally
```

| Folder | What's inside |
|---|---|
| `web/` | The app: one page, the built-in question bank and the background picture |
| `relay/` | The Cloudflare Worker that keeps the API key secret and builds every prompt itself |
| `levelup_aruai/` | Python engine: offline agents, a terminal game, and the question-bank generator |
| `tests/` | Python, browser and relay tests |

## Put it online
Follow **[DEPLOY.md](DEPLOY.md)**: free Groq + Cloudflare + GitHub Pages, about 20 minutes.

## Run it locally
```
npm install                                   # Pyodide for the browser tests
GROQ_API_KEY=... npm run dev:relay            # local relay on http://127.0.0.1:8787
cd web && python -m http.server 8000          # open http://localhost:8000
python -m levelup_aruai --rounds 5            # or play in the terminal
```

## Tests
```
npm run test:relay                            # relay unit tests (Node)
python -m pytest -q                           # Python + browser tests (needs: pip install pytest playwright)
python export_bank.py web/bank.json           # rebuild the built-in question bank
```

## Security
- The API key lives only in GitHub and Cloudflare **secrets**. It's never in this repository or in the page.
- The relay doesn't accept raw prompts, only answers the app's own website, and limits requests from each visitor.
