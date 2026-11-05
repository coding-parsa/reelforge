"""User hooks: drop a file in <home>/hooks and it runs inside the pipeline.

    before_script   may return {"script": {...}} to replace the AI entirely
    before_render   may return {"script":…, "design":…, "brand":…}
    after_render    gets the finished file (upload it, rename it, log it)

Python hooks run in a separate process of the same interpreter — the bundled one
when the app is packaged — so a broken hook can never take the app down. Node is
supported too if it is installed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import paths, store

STAGES = ("before_script", "before_render", "after_render")
TIMEOUT = 300


def hook_file(stage: str) -> Path | None:
    base = paths.hooks_dir()
    for ext in (".py", ".js", ".mjs"):
        p = base / f"{stage}{ext}"
        if p.exists():
            return p
    return None


def list_hooks() -> list[dict]:
    out = []
    for stage in STAGES:
        f = hook_file(stage)
        out.append({"stage": stage, "file": str(f) if f else None, "active": bool(f),
                    "kind": f.suffix.lstrip(".") if f else None})
    return out


def _interpreter(hook: Path, out_file: Path) -> list[str] | None:
    """Command that runs the hook. Python hooks report through a file: a windowed
    exe has no stdout, and that must not stop a hook from answering."""
    if hook.suffix == ".py":
        if getattr(sys, "frozen", False):
            return [sys.executable, "--run-hook", str(hook), "--out", str(out_file)]
        return [sys.executable, "-m", "reelforge.hookrunner", str(hook), "--out", str(out_file)]
    node = shutil.which("node")
    return [node, str(hook)] if node else None


def run(stage: str, payload: dict) -> dict:
    """Run the user's hook for this stage. Always returns a dict (never raises)."""
    if not store.get_setting("hooks_enabled", True):
        return {}
    hook = hook_file(stage)
    if not hook:
        return {}
    out_file = Path(tempfile.mkdtemp(prefix="rf-hook-")) / "out.json"
    cmd = _interpreter(hook, out_file)
    if not cmd:
        return {"_error": f"{stage}: Node.js is not installed, cannot run {hook.name}"}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               REELFORGE_STAGE=stage, REELFORGE_HOOK=str(hook))
    creation = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        proc = subprocess.run(cmd, input=json.dumps(payload, ensure_ascii=False, default=str),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT, env=env, creationflags=creation)
    except subprocess.TimeoutExpired:
        return {"_error": f"{stage}: timed out after {TIMEOUT}s"}
    except Exception as exc:
        return {"_error": f"{stage}: {exc}"}
    out = (proc.stdout or "").strip()
    if out_file.exists():
        try:
            out = out_file.read_text(encoding="utf-8").strip() or out
        except Exception:
            pass
        shutil.rmtree(out_file.parent, ignore_errors=True)
    if proc.returncode != 0:
        return {"_error": f"{stage} exit {proc.returncode}: {(proc.stderr or out)[-400:]}"}
    if not out:
        return {}
    try:
        data = json.loads(out)
        return data if isinstance(data, dict) else {}
    except Exception:
        # the hook printed prose; keep it as a log line, not a result
        return {"_log": out[-1000:]}


def context() -> dict:
    """Read-only config the hooks may need (never includes the API key)."""
    s = store.all_settings()
    return {
        "app": "reelforge",
        "home": str(paths.home_dir()),
        "assets": str(paths.assets_dir()),
        "out": str(paths.out_dir()),
        "brand": {k: s.get(k) for k in ("brand_name", "brand_latin", "brand_site", "brand_cta_title",
                                        "brand_cta_body", "brand_cta_chip", "brand_footer_cta")},
        "render": {"fps": s.get("fps"), "quality": s.get("render_quality")},
    }


def example_hook(stage: str, kind: str = "py") -> str:
    """Starter files the UI can drop into the hooks folder for the user."""
    py = {
        "before_script": '''"""before_script — build the script yourself instead of calling the AI.

Return {"script": {...}} and the AI step is skipped entirely.
`payload` has: project, article (title/text/blocks/url), config.
"""
def run(payload):
    article = payload["article"]
    return {}          # {} means: let Reelforge do its normal thing
''',
        "before_render": '''"""before_render — tweak the cards or the design right before rendering.

Return any of {"script":…, "design":…, "brand":…}; return {} to change nothing.
"""
def run(payload):
    script = payload["script"]
    return {}
''',
        "after_render": '''"""after_render — the video exists. Upload it, copy it, log it.

`payload` has: video, cover, script, meta, project, config.
Return a dict and it is shown on the project page (put your URL in "url").
"""
def run(payload):
    video = payload["video"]
    return {}
''',
    }[stage]
    js = '''// %s — Node hook. Print a JSON object on stdout; empty output means "no changes".
const chunks = [];
process.stdin.on("data", c => chunks.push(c));
process.stdin.on("end", () => {
  const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  // e.g. return {design: {...payload.design, theme: "ink_teal"}}
  process.stdout.write(JSON.stringify({}));
});
''' % stage
    return py if kind == "py" else js
