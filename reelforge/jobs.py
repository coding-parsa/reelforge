"""The pipeline: article -> script -> composed page -> mp4 -> metadata.

One worker thread renders one video at a time (a headless browser plus x264
already saturates a laptop). Projects sit in a queue, so "full auto" and
"human in the loop" are the same code path with one flag: review_gate.
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from pathlib import Path

from . import ai, assets_pool, autoscript, compose, hooks, ingest, paths, render, store, themes

_base_url = "http://127.0.0.1:8765"
_cancel: dict[str, threading.Event] = {}
_review: dict[str, bool] = {}
_quality: dict[str, str] = {}
_lock = threading.Lock()
_stop = threading.Event()
_wake = threading.Event()
_worker: threading.Thread | None = None
_current: str | None = None
_log: list[str] = []


def set_base_url(url: str) -> None:
    global _base_url
    _base_url = url.rstrip("/")


def base_url() -> str:
    return _base_url


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    with _lock:
        _log.append(line)
        del _log[:-400]
    print(line, flush=True)


def recent_log(n: int = 80) -> list[str]:
    with _lock:
        return _log[-n:]


def brand_from_settings() -> dict:
    s = store.all_settings()
    logo = (s.get("brand_logo") or "").strip()
    if not logo:
        cand = paths.assets_dir() / "logo.png"
        logo = "/assets/logo.png" if cand.exists() or (paths.bundled_assets_dir() / "logo.png").exists() else ""
    elif not logo.startswith("/"):
        p = Path(logo)
        logo = f"/assets/{p.name}" if p.exists() else ""
    return {
        "name": s.get("brand_name") or "",
        "latin": s.get("brand_latin") or "",
        "site": s.get("brand_site") or "",
        "logo": logo,
        "cta_title": s.get("brand_cta_title") or "",
        "cta_body": s.get("brand_cta_body") or "",
        "cta_chip": s.get("brand_cta_chip") or "",
        "footer_cta": s.get("brand_footer_cta") or "",
    }


# ---------------------------------------------------------------- compose helpers

def resolve_design(pid: str, design: dict | None) -> dict:
    design = dict(design or {})
    fixed = {k: design.get(k) for k in themes.AUTO_KEYS if design.get(k)}
    resolved = themes.pick(pid, fixed)
    resolved["format"] = design.get("format") or "9:16"
    resolved["mode"] = design.get("mode") or "auto"
    return resolved


def project_page_url(pid: str) -> str:
    return f"{_base_url}/render/{pid}/index.html"


def project_dir(pid: str) -> Path:
    return paths.projects_dir() / pid


def photo_url(project: dict) -> str | None:
    """Download the article's own lead image once and serve it from the project."""
    article = project.get("article") or {}
    img = article.get("image")
    if not img:
        return None
    pdir = project_dir(project["id"])
    pdir.mkdir(parents=True, exist_ok=True)
    name = ingest.fetch_image(img, pdir)
    return f"{_base_url}/projects/{project['id']}/{name}" if name else None


def compose_project(project: dict, *, design_override: dict | None = None,
                    brand_override: dict | None = None, script_override: dict | None = None) -> dict:
    pid = project["id"]
    script = script_override or project.get("script")
    if not script:
        raise RuntimeError("project has no script yet")
    design = design_override or resolve_design(pid, project.get("design"))
    brand = brand_override or project.get("brand") or brand_from_settings()
    pdir = project_dir(pid)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
    (pdir / "design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")
    (pdir / "brand.json").write_text(json.dumps(brand, ensure_ascii=False, indent=1), encoding="utf-8")
    info = compose.compose(
        script, design, brand, project_dir=pdir, seed=pid, photo=photo_url(project),
        assets=assets_pool.scan(), format_key=design.get("format") or "9:16",
        fps=int(store.get_setting("fps") or 30),
    )
    return info


def audio_plan(info: dict, project: dict) -> dict:
    """Turn the page's audio tags into absolute paths for the ffmpeg mix."""
    music = info.get("music")
    plan = {"music": None, "sfx": []}
    if music:
        p = paths.asset("music", music)
        plan["music"] = str(p) if p.exists() else None
    for s in info.get("sfx") or []:
        rel = s.get("src", "").replace("/assets/", "", 1)
        p = paths.asset(*Path(rel).parts)
        if p.exists():
            plan["sfx"].append({"src": str(p), "at": s.get("at", 0), "volume": s.get("volume", 0.35)})
    return plan


# ---------------------------------------------------------------- script step

def ensure_script(project: dict, job_id: int | None = None) -> dict:
    """Script from a hook, from the AI, or from the user's own editor."""
    pid = project["id"]
    if project.get("script"):
        return project
    article = project.get("article") or {}
    brand = project.get("brand") or brand_from_settings()

    hook_out = hooks.run("before_script", {"stage": "before_script", "project": pid,
                                           "article": article, "config": hooks.context()})
    if hook_out.get("_error"):
        log(f"hook before_script: {hook_out['_error']}")
    if isinstance(hook_out.get("script"), dict):
        store.update_project(pid, script=hook_out["script"], status="script_ready")
        log("script provided by hooks/before_script")
        return store.get_project(pid)

    if not store.get_setting("auto_generate", True):
        store.update_project(pid, status="needs_script")
        return store.get_project(pid)

    # No key? The article can still become cards on its own — the queue never dead-ends.
    if (store.get_setting("ai_provider") or "none") in ("none", ""):
        script, warn = autoscript.build(article, brand)
        meta = {**(project.get("meta") or {}), **autoscript.meta(article, script, brand)}
        store.update_project(pid, script=script, status="script_ready", meta=meta,
                             error="; ".join(warn)[:300] or None)
        log(f"script for {pid} built from the article (no AI configured)")
        return store.get_project(pid)

    if job_id:
        store.update_job(job_id, message="writing the script", progress=0.05)
    log(f"writing script for {pid} with {store.get_setting('ai_model')}")
    result = ai.generate_script(article, brand, scene_count=6,
                                extra=(project.get("meta") or {}).get("brief") or "")
    script = result["script"]
    script["title"] = script.get("title") or article.get("title", "")[:100]
    store.update_project(pid, script=script, status="script_ready",
                         error="; ".join(result.get("warnings") or [])[:400] or None)
    if store.get_setting("auto_meta", True):
        try:
            meta = ai.generate_meta(script, brand)
            store.update_project(pid, meta={**(project.get("meta") or {}), **meta})
        except Exception as exc:
            log(f"metadata skipped: {exc}")
    return store.get_project(pid)


# ---------------------------------------------------------------- render step

def render_project(pid: str, job_id: int | None = None, *, review: bool | None = None,
                   quality: str | None = None) -> dict:
    project = store.get_project(pid)
    if not project:
        raise RuntimeError("project not found")
    project = ensure_script(project, job_id)
    script = project.get("script")
    if not script:
        store.update_project(pid, status="needs_script")
        return store.get_project(pid)

    gate = store.get_setting("review_gate", False) if review is None else review
    if gate:
        store.update_project(pid, status="review")
        store.update_job(job_id, status="done", progress=1, message="waiting for review") if job_id else None
        return store.get_project(pid)

    cancel = threading.Event()
    with _lock:
        _cancel[pid] = cancel

    def progress(fraction: float, message: str) -> None:
        if job_id:
            store.update_job(job_id, progress=round(fraction, 3), message=message)

    try:
        store.update_project(pid, status="rendering", error=None)
        if job_id:
            store.update_job(job_id, message="composing the page", progress=0.02)
        info = compose_project(project)
        store.update_project(pid, design={**(project.get("design") or {}), **info["design"]})

        hook_out = hooks.run("before_render", {"stage": "before_render", "project": pid,
                                               "script": script, "design": info["design"],
                                               "brand": project.get("brand") or brand_from_settings(),
                                               "config": hooks.context()})
        if hook_out.get("_error"):
            log(f"hook before_render: {hook_out['_error']}")
        if any(k in hook_out for k in ("script", "design", "brand")):
            patched = store.update_project(pid, **{k: hook_out[k] for k in ("script", "design", "brand")
                                                   if isinstance(hook_out.get(k), dict)})
            project = patched or project
            info = compose_project(project)
            store.update_project(pid, design={**(project.get("design") or {}), **info["design"]})

        out_dir = paths.out_dir() / pid
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "video.mp4"
        fps = int(store.get_setting("fps") or 30)
        quality = quality or store.get_setting("render_quality") or "high"
        result = render.render(project_dir(pid), info, out_path, page_url=project_page_url(pid),
                               fps=fps, quality=quality, audio_src=audio_plan(info, project),
                               progress=progress, cancel=cancel)
        store.remember_recipe("|".join(str(info["design"].get(k)) for k in themes.AUTO_KEYS))
        project = store.update_project(pid, status="done", video=result["video"], cover=result["cover"],
                                       duration=result["duration"], size_mb=result["size_mb"], error=None)
        if job_id:
            store.update_job(job_id, status="done", progress=1, message="done")
        log(f"rendered {pid} · {result['duration']}s · {result['size_mb']}MB")

        hook_after = hooks.run("after_render", {"stage": "after_render", "project": pid,
                                                "video": result["video"], "cover": result["cover"],
                                                "script": project.get("script"), "meta": project.get("meta"),
                                                "config": hooks.context()})
        if hook_after:
            meta = {**(project.get("meta") or {}), "hook": hook_after}
            store.update_project(pid, meta=meta)
        return store.get_project(pid)
    except InterruptedError:
        store.update_project(pid, status="draft", error="cancelled")
        if job_id:
            store.update_job(job_id, status="cancelled", message="cancelled")
        log(f"cancelled {pid}")
        return store.get_project(pid) or project
    except Exception as exc:
        detail = str(exc)[:600]
        store.update_project(pid, status="failed", error=detail)
        if job_id:
            store.update_job(job_id, status="failed", message=detail)
        log(f"FAILED {pid}: {detail}")
        log(traceback.format_exc(limit=3)[-1200:])
        return store.get_project(pid) or project
    finally:
        with _lock:
            _cancel.pop(pid, None)


# ---------------------------------------------------------------- queue worker

def enqueue(pid: str, review: bool | None = None, quality: str | None = None) -> None:
    if review is not None:
        _review[pid] = review
    if quality in ("high", "draft"):
        _quality[pid] = quality
    store.update_project(pid, status="queued", error=None)
    _wake.set()


def cancel(pid: str) -> None:
    with _lock:
        ev = _cancel.get(pid)
    if ev:
        ev.set()
    else:
        store.update_project(pid, status="draft")


def is_running(pid: str | None = None) -> bool:
    with _lock:
        return bool(_cancel) if pid is None else pid in _cancel


def worker_alive() -> bool:
    return bool(_worker and _worker.is_alive())


def _loop() -> None:
    global _current
    log("queue worker started")
    while not _stop.is_set():
        project = store.next_project("queued")
        if not project:
            _wake.wait(timeout=2.0)
            _wake.clear()
            continue
        pid = project["id"]
        with _lock:
            _current = pid
        job_id = store.new_job(pid, "render")
        try:
            render_project(pid, job_id, review=_review.pop(pid, None), quality=_quality.pop(pid, None))
        except Exception as exc:                 # the loop must survive anything
            log(f"worker error: {exc}")
            store.update_project(pid, status="failed", error=str(exc)[:400])
        finally:
            with _lock:
                _current = None
    log("queue worker stopped")


def start() -> None:
    global _worker
    if worker_alive():
        return
    _stop.clear()
    _worker = threading.Thread(target=_loop, name="reelforge-worker", daemon=True)
    _worker.start()


def stop() -> None:
    _stop.set()
    _wake.set()
    with _lock:
        for ev in _cancel.values():
            ev.set()


def status() -> dict:
    with _lock:
        return {"alive": worker_alive(), "current": _current, "log": _log[-40:]}
