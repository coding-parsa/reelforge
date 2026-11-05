# Contributing to Reelforge

Thanks for wanting to help. The project is deliberately small; the best contributions are the ones that
keep it that way.

## Getting set up

```bash
git clone https://github.com/<you>/reelforge && cd reelforge
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt        # macOS/Linux: .venv/bin/pip
.venv/Scripts/python run.py                          # serves on a random port + opens a window
.venv/Scripts/python run.py --no-window --port 8700  # server only, for front-end work
```

You need **ffmpeg** on PATH and **Chrome/Edge** installed. No Node, no build step for the UI.

## Where things live

- `reelforge/web/` — the UI. Vanilla JS in one file, no framework, no bundler. Keep it that way.
- `reelforge/compose.py` — the design system (CSS + scene HTML + GSAP timeline). Design changes go here.
- `reelforge/render.py` — CDP frame capture and the ffmpeg mix.
- `reelforge/ai.py` — provider transport and the prompt/normaliser. Prompt changes are high-impact.
- `hooks/examples/` — user-facing scripting examples; they must stay runnable.

## What a good PR looks like

1. **One thing.** A fix, a feature, or a refactor — not two of them at once.
2. **A screenshot or a rendered frame** for anything visual. PRs that change the look without one get
   asked for one.
3. **No new dependencies** unless there is no reasonable stdlib path. The whole point is
   `pip install -r requirements.txt` and go.
4. **Test it against a real article**, not a toy string: `python run.py`, paste a URL, render a draft.
5. **Say what you did not test.** An honest "only checked on Windows" is worth more than silence.

## Style

- Python 3.11, type hints where they help, f-strings, no classes for the sake of classes.
- Comments explain *why*, not *what* — the code already says what.
- Keep functions small enough to read on one screen.
- UI copy is sentence case, short, and never says "Oops".

## Adding a theme

Append to `THEMES` in `reelforge/themes.py` (eight colour keys), or drop a JSON file in the user's
`themes/` folder — the second path needs no code change, which is the point.

## Adding a provider

`reelforge/ai.py:chat()` has one branch per wire format (OpenAI-compatible, Anthropic, Gemini). Anything
that speaks `/chat/completions` already works through the OpenAI branch — add a preset in `PROVIDERS`
instead of a branch.

## Reporting a bug

Include the app version (Settings → Interface), what you expected, what happened, and the log from
**Settings → Paths → logs** (or `%LOCALAPPDATA%\Reelforge\logs\app.log`).
