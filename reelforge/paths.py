"""Filesystem layout for Reelforge.

One rule: everything the user can touch lives in a single *home* folder, so a
portable copy on a USB stick behaves exactly like the installed one.

    <home>/
      data/reelforge.db     projects, queue, settings
      assets/               fonts, logo, broll/, music/, sfx/   (user-editable)
      projects/<id>/        composed index.html + script.json + recipe.json
      out/                  finished mp4 + cover jpg
      hooks/                user python/js hooks (see hooks/README.md)
      themes/               drop-in theme packs (*.json)
      logs/
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running from the packaged .exe (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Folder the program itself lives in (read-only starter assets sit here)."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def bundled_dir() -> Path:
    """Read-only files shipped with the program (fonts, logo, web UI, gsap)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return Path(__file__).resolve().parent


def home_dir() -> Path:
    """Writable root. Portable mode: `portable.txt` next to the exe, or REELFORGE_HOME."""
    env = os.environ.get("REELFORGE_HOME")
    if env:
        p = Path(env).expanduser()
    elif (app_root() / "portable.txt").exists() or (app_root() / "data").is_dir():
        # a data/ folder beside the program means the user wants everything local
        p = app_root()
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        p = Path(base) / "Reelforge"
    else:
        p = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "reelforge"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sub(name: str) -> Path:
    p = home_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path: return _sub("data")
def projects_dir() -> Path: return _sub("projects")
def out_dir() -> Path: return _sub("out")
def hooks_dir() -> Path: return _sub("hooks")
def themes_dir() -> Path: return _sub("themes")
def logs_dir() -> Path: return _sub("logs")
def bin_dir() -> Path: return _sub("bin")


def assets_dir() -> Path:
    """User asset pool. May be overridden in settings; defaults to <home>/assets."""
    from . import store            # local import: store imports paths
    custom = (store.get_setting("assets_dir") or "").strip()
    if custom:
        p = Path(custom).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass
    p = home_dir() / "assets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def asset(*parts: str) -> Path:
    """Resolve an asset, preferring the user pool, falling back to the bundled one."""
    rel = Path(*parts)
    user = assets_dir() / rel
    if user.exists():
        return user
    return bundled_dir() / "assets" / rel


def db_path() -> Path:
    return data_dir() / "reelforge.db"


HOOK_README = """# Hooks

Drop one file per stage in this folder and Reelforge runs it inside the pipeline.
`before_script` can build the script itself (no AI), `before_render` can change the
cards or the design, `after_render` gets the finished video (upload it, copy it, log it).

    before_script.py   {"project","article","config"}        -> {"script": {...}}
    before_render.py   {"project","script","design","brand"} -> {"script","design","brand"}
    after_render.py    {"project","video","cover","meta"}    -> {"url": "https://…"}

Python hooks define `run(payload)` and return a dict; `payload` is also a global.
JavaScript hooks (`*.js`) print JSON on stdout and run with Node.
Any output the app does not understand is ignored, and a crashing hook is logged
instead of stopping the render.
"""

ASSETS_README = """# Assets

Optional media. Reelforge renders without any of it (gradient / photo backgrounds,
silent video) — add files here to get b-roll, music and sound effects.

    broll/   .mp4 clips. Name them by topic: china-01.mp4, money-02.mp4,
             student-03.mp4 — the renderer picks the clip whose name matches the card.
    music/   .mp3 beds, one is picked per video and looped under the whole thing.
    sfx/     whoosh.mp3, tick.mp3, thump.mp3 (three starter sounds ship with the app).
    logo.png your logo, used by the brand block on every card.

Everything here is only read locally; nothing is uploaded.
"""

THEME_EXAMPLE = """{
  "name": "midnight_rose",
  "deep": "#120b16",
  "surface": "#1d1024",
  "ink": "#f8eef7",
  "muted": "rgba(248,238,247,.82)",
  "accent": "#f4a8c8",
  "accent_deep": "#4a1230",
  "glow_a": "rgba(244,168,200,.38)",
  "glow_b": "rgba(90,50,140,.40)"
}
"""


def ensure_home() -> None:
    """Create the folder layout and the starter files a first run needs."""
    data_dir(); projects_dir(); out_dir(); logs_dir(); bin_dir()
    hooks = hooks_dir(); themes = themes_dir(); assets = assets_dir()
    for sub in ("broll", "music", "sfx", "fonts"):
        (assets / sub).mkdir(parents=True, exist_ok=True)
    for path, text in ((hooks / "README.md", HOOK_README),
                       (assets / "README.md", ASSETS_README),
                       (themes / "example-theme.json", THEME_EXAMPLE)):
        if not path.exists():
            try:
                path.write_text(text, encoding="utf-8")
            except OSError:
                pass
    # starter hooks live in the repo / bundle; copy them once
    src = bundled_dir() / "hooks" / "examples"
    if src.is_dir():
        dest = hooks / "examples"
        if not dest.exists():
            import shutil
            shutil.copytree(src, dest, dirs_exist_ok=True)
