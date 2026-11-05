"""SQLite store: settings, projects, jobs, and the recipe history.

One connection, one lock: every write is short, and the render worker is a
thread, so this is simpler and safer than a connection pool.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Any

from . import paths

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY,
  title TEXT,
  source_url TEXT,
  source_kind TEXT,
  article TEXT,
  script TEXT,
  design TEXT,
  brand TEXT,
  meta TEXT,
  status TEXT,
  video TEXT,
  cover TEXT,
  duration REAL,
  size_mb REAL,
  error TEXT,
  created TEXT,
  updated TEXT
);
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT,
  kind TEXT,
  status TEXT,
  progress REAL DEFAULT 0,
  message TEXT,
  created TEXT,
  updated TEXT
);
CREATE TABLE IF NOT EXISTS recipes(
  key TEXT PRIMARY KEY,
  used TEXT
);
"""

DEFAULTS: dict[str, Any] = {
    # ---- AI ----
    "ai_provider": "openai",          # openai | anthropic | gemini | none
    "ai_base_url": "https://api.openai.com/v1",
    "ai_model": "gpt-4o-mini",
    "ai_key": "",                     # encrypted at rest
    "ai_temperature": 0.7,
    "ai_language": "auto",            # auto | fa | en | de | tr | ar | ru
    "ai_extra": "",                   # extra JSON merged into the request body
    "ai_headers": "",                 # extra JSON headers (Azure: {"api-key": "..."} / gateways)
    "prompt_script": "",             # empty = the built-in template in ai.py
    "prompt_meta": "",
    # ---- automation ----
    "auto_generate": True,            # queue: write the script when missing
    "script_mode": "auto",            # auto (AI if configured, else the article) | ai | manual
    "auto_render": True,              # queue: render right after the script exists
    "review_gate": False,             # queue: stop at "needs review" instead of rendering
    "default_design_mode": "auto",    # auto (varied) | fixed
    "default_theme": "auto",
    # ---- brand ----
    "brand_name": "Reelforge",
    "brand_latin": "REELFORGE",
    "brand_site": "example.com",
    "brand_logo": "",                 # path (usually <assets>/logo.png)
    "brand_cta_title": "Read the full guide",
    "brand_cta_body": "Everything in one place. **Free to start.**",
    "brand_cta_chip": "Open the guide",
    "brand_footer_cta": "Follow for more",
    # ---- render ----
    "fps": 30,
    "render_quality": "high",         # high | draft
    "music_volume": 0.3,
    "sfx_enabled": True,
    "cover": True,
    "auto_meta": True,
    "assets_dir": "",
    "browser_path": "",
    "ffmpeg_path": "",
    "hooks_enabled": True,
    # ---- ui ----
    "ui_lang": "en",
    "onboarded": False,
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(paths.db_path(), check_same_thread=False, timeout=30)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _conn.executescript(SCHEMA)
            _conn.commit()
        return _conn


def init() -> None:
    connect()
    with _lock:
        c = connect()
        for k, v in DEFAULTS.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
        c.commit()


# ---------------------------------------------------------------- settings

def get_setting(key: str, default: Any = None) -> Any:
    if key in DEFAULTS and default is None:
        default = DEFAULTS[key]
    with _lock:
        row = connect().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return default


def set_setting(key: str, value: Any) -> None:
    with _lock:
        c = connect()
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, json.dumps(value, ensure_ascii=False)))
        c.commit()


def all_settings() -> dict[str, Any]:
    out = dict(DEFAULTS)
    with _lock:
        for row in connect().execute("SELECT key,value FROM settings"):
            try:
                out[row["key"]] = json.loads(row["value"])
            except Exception:
                pass
    return out


# ---------------------------------------------------------------- projects

_PROJECT_FIELDS = ["title", "source_url", "source_kind", "article", "script", "design", "brand",
                   "meta", "status", "video", "cover", "duration", "size_mb", "error"]


def _row_to_project(row: sqlite3.Row) -> dict:
    p = {k: row[k] for k in row.keys()}
    for k in ("article", "script", "design", "brand", "meta"):
        if p.get(k):
            try:
                p[k] = json.loads(p[k])
            except Exception:
                p[k] = None
    return p


def new_project(title: str = "Untitled", source_url: str = "", source_kind: str = "text") -> dict:
    pid = uuid.uuid4().hex[:12]
    now = _now()
    with _lock:
        c = connect()
        c.execute("INSERT INTO projects(id,title,source_url,source_kind,status,created,updated) "
                  "VALUES(?,?,?,?,?,?,?)", (pid, title, source_url, source_kind, "draft", now, now))
        c.commit()
    return get_project(pid)


def get_project(pid: str) -> dict | None:
    with _lock:
        row = connect().execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return _row_to_project(row) if row else None


def list_projects(limit: int = 200) -> list[dict]:
    with _lock:
        rows = connect().execute("SELECT * FROM projects ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
    return [_row_to_project(r) for r in rows]


def update_project(pid: str, **fields) -> dict | None:
    clean = {k: v for k, v in fields.items() if k in _PROJECT_FIELDS}
    for k in ("article", "script", "design", "brand", "meta"):
        if k in clean and not isinstance(clean[k], (str, type(None))):
            clean[k] = json.dumps(clean[k], ensure_ascii=False)
    clean["updated"] = _now()
    cols = ", ".join(f"{k}=?" for k in clean)
    with _lock:
        c = connect()
        c.execute(f"UPDATE projects SET {cols} WHERE id=?", (*clean.values(), pid))
        c.commit()
    return get_project(pid)


def delete_project(pid: str) -> None:
    with _lock:
        c = connect()
        c.execute("DELETE FROM projects WHERE id=?", (pid,))
        c.execute("DELETE FROM jobs WHERE project_id=?", (pid,))
        c.commit()


def next_project(status: str = "queued") -> dict | None:
    with _lock:
        row = connect().execute("SELECT * FROM projects WHERE status=? ORDER BY created LIMIT 1", (status,)).fetchone()
    return _row_to_project(row) if row else None


# ---------------------------------------------------------------- jobs

def new_job(project_id: str, kind: str) -> int:
    now = _now()
    with _lock:
        c = connect()
        cur = c.execute("INSERT INTO jobs(project_id,kind,status,progress,message,created,updated) "
                        "VALUES(?,?,?,?,?,?,?)", (project_id, kind, "running", 0, "", now, now))
        c.commit()
        return int(cur.lastrowid)


def update_job(job_id: int, **fields) -> None:
    allowed = {k: v for k, v in fields.items() if k in ("status", "progress", "message")}
    if not allowed:
        return
    allowed["updated"] = _now()
    cols = ", ".join(f"{k}=?" for k in allowed)
    with _lock:
        c = connect()
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*allowed.values(), job_id))
        c.commit()


def get_job(job_id: int) -> dict | None:
    with _lock:
        row = connect().execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None


def project_job(project_id: str) -> dict | None:
    with _lock:
        row = connect().execute("SELECT * FROM jobs WHERE project_id=? ORDER BY id DESC LIMIT 1",
                                (project_id,)).fetchone()
    return dict(row) if row else None


def recent_jobs(limit: int = 30) -> list[dict]:
    with _lock:
        rows = connect().execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- recipe history
# Keeps consecutive videos from sharing a look: the picker avoids the last N keys.

def recent_recipes(n: int = 24) -> list[str]:
    with _lock:
        rows = connect().execute("SELECT key FROM recipes ORDER BY used DESC LIMIT ?", (n,)).fetchall()
    return [r["key"] for r in rows]


def remember_recipe(key: str) -> None:
    with _lock:
        c = connect()
        c.execute("INSERT OR REPLACE INTO recipes(key,used) VALUES(?,?)", (key, _now()))
        c.execute("DELETE FROM recipes WHERE key NOT IN (SELECT key FROM recipes ORDER BY used DESC LIMIT 500)")
        c.commit()
