# Architecture

Reelforge is small on purpose: one Python package, one HTML page, two external binaries.

```
reelforge/
├─ launcher.py    start the local server, open a window (app-mode Edge/Chrome or pywebview)
├─ server.py      FastAPI: JSON API + the files the browser needs while rendering (Range requests)
├─ store.py       SQLite: projects, jobs, settings, recipe history
├─ secrets.py     DPAPI at rest (Windows), plain-with-a-warning elsewhere
├─ ingest.py      URL / sitemap → clean article blocks (stdlib HTMLParser, no bs4)
├─ ai.py          provider adapters, prompt templates, JSON repair + normaliser
├─ compose.py     script + design + brand → one animated HTML page (GSAP timeline)
├─ themes.py      theme packs, layouts, and the anti-repetition design picker
├─ assets_pool.py b-roll / music / sfx discovery and topic matching
├─ render.py      headless Chromium over CDP → JPEG frames → ffmpeg → mp4
├─ jobs.py        the worker thread and the pipeline (compose → hooks → render → hooks)
├─ hooks.py       user scripts in a child process of the same interpreter
└─ web/           the UI (vanilla JS, no build step)
```

## The page is the video

`compose.py` writes `projects/<id>/index.html`: a 1080×1920 document with one `<section>` per scene and a
**paused GSAP timeline** that knows when every element enters. It exposes a tiny API:

```js
window.rf.seek(t)   // deterministic: timeline + every <video> seeked to t
window.rf.play()    // real-time playback for the preview
```

`render.py` opens that page in headless Chromium over the DevTools protocol, calls `rf.seek(t)` for each
frame, screenshots it, and pipes the JPEGs into ffmpeg's `image2pipe` demuxer. Audio is not captured from
the page at all: the same timeline data becomes an ffmpeg filter graph (music bed with fades + effect
one-shots at their timestamps), so the mix is sample-accurate and the page can stay muted.

Because the Studio shows the same page in an iframe, preview and output cannot disagree — and a change to
the design is a change to CSS, not to a rendering engine.

## The design picker

`themes.pick(seed, fixed)` chooses the six dimensions a video needs, seeded by the project id, and rejects
any combination (or theme, or layout) that appears in the last 24 renders (`recipes` table). That is the
whole anti-template mechanism, and it is why a 50-video batch looks like 50 videos instead of 50 copies.

## The pipeline

`jobs.py` runs one worker thread — a headless browser plus x264 already saturates a laptop, and two of them
fight over cores. A project moves through:

```
draft → queued → (script) → (review) → rendering → done | failed
```

`review_gate` and `auto_render` in settings are the only difference between hands-off and human-in-the-loop:
the code path is identical.

## Failure behaviour

- A render that dies leaves `status=failed` with the real error, and the queue moves on.
- A hook that raises, hangs (5 min) or prints junk is logged and ignored.
- A stale `rendering` project is released back to the queue on the next import.
- Everything the AI returns goes through `ai.normalize_script`: scene count, word limits, two-line
  headlines, CTA preserved verbatim. A bad reply is retried once with the validation error attached.

## Why no Electron / Remotion / Node

The renderer only needs "a browser that can screenshot" and "ffmpeg". Edge ships with Windows and Chrome is
everywhere, so the app is a 18 MB exe instead of a 200 MB runtime, and a contributor needs
`pip install -r requirements.txt` — nothing else.
