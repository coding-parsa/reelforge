"""HTTP surface: the local API plus the files the browser needs while it renders.

Everything binds to 127.0.0.1 only. POSTs must carry the `X-Reelforge` header,
which a random web page cannot add cross-origin without a CORS preflight we
never answer — that keeps a malicious site from driving the app.
"""
from __future__ import annotations

import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse

from . import ai, assets_pool, autoscript, hooks, ingest, jobs, paths, render, secrets, store, themes

APP_VERSION = "1.1.0"
web_dir = paths.bundled_dir() / "web"

app = FastAPI(title="Reelforge", version=APP_VERSION, docs_url=None, redoc_url=None)


# ---------------------------------------------------------------- helpers

async def body_json(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _guard(request: Request) -> None:
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        if request.headers.get("x-reelforge") != "1":
            raise HTTPException(403, "missing app header")


def public_settings() -> dict:
    s = store.all_settings()
    s["ai_key"] = secrets.mask(s.get("ai_key") or "")
    s["ai_key_set"] = bool(secrets.unprotect(store.get_setting("ai_key") or ""))
    s["paths"] = {
        "home": str(paths.home_dir()), "assets": str(paths.assets_dir()),
        "out": str(paths.out_dir()), "hooks": str(paths.hooks_dir()),
        "themes": str(paths.themes_dir()), "logs": str(paths.logs_dir()),
    }
    return s


def _safe_child(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(403, "path outside the app folder")
    return target


def range_file(path: Path, request: Request) -> Response:
    """Serve a file with HTTP Range support — <video> needs it to seek."""
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "not found")
    size = path.stat().st_size
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    rng = request.headers.get("range")
    if not rng:
        return FileResponse(path, media_type=mime,
                            headers={"Accept-Ranges": "bytes", "Cache-Control": "no-cache"})
    try:
        spec = rng.split("=", 1)[1]
        start_s, _, end_s = spec.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else size - 1
    except Exception:
        raise HTTPException(416, "bad range")
    if start >= size:
        raise HTTPException(416, "range not satisfiable")
    end = min(end, size - 1)
    length = end - start + 1

    def stream():
        with open(path, "rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                chunk = fh.read(min(262144, left))
                if not chunk:
                    break
                left -= len(chunk)
                yield chunk

    return StreamingResponse(stream(), status_code=206, media_type=mime,
                             headers={"Content-Range": f"bytes {start}-{end}/{size}",
                                      "Accept-Ranges": "bytes", "Content-Length": str(length)})


def _project_or_404(pid: str) -> dict:
    p = store.get_project(pid)
    if not p:
        raise HTTPException(404, "project not found")
    return p


# ---------------------------------------------------------------- bootstrap

@app.middleware("http")
async def _headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    page = web_dir / "index.html"
    if not page.exists():
        return "<h1>Reelforge</h1><p>Web UI not found next to the executable.</p>"
    return page.read_text(encoding="utf-8")


@app.get("/api/bootstrap")
def bootstrap() -> dict:
    bins = render.check_binaries()
    return {
        "version": APP_VERSION,
        "settings": public_settings(),
        "catalog": themes.catalog(),
        "assets": assets_pool.scan()["counts"],
        "hooks": hooks.list_hooks(),
        "binaries": bins,
        "projects": [_project_summary(p) for p in store.list_projects()],
        "queue": jobs.status(),
        "providers": [{"name": k, **v} for k, v in ai.PROVIDERS.items()],
        "presets": ai.PROVIDER_PRESETS,
        "ai_configured": (store.get_setting("ai_provider") or "none") not in ("none", ""),
        "prompts": {"script": ai.DEFAULT_SCRIPT_PROMPT, "meta": ai.DEFAULT_META_PROMPT},
        "platform": {"os": sys.platform, "frozen": paths.is_frozen(), "home": str(paths.home_dir())},
    }


def _project_summary(p: dict) -> dict:
    job = store.project_job(p["id"])
    return {
        "id": p["id"], "title": p.get("title") or "", "status": p.get("status") or "draft",
        "source_url": p.get("source_url") or "", "updated": p.get("updated"),
        "duration": p.get("duration"), "size_mb": p.get("size_mb"),
        "has_video": bool(p.get("video") and Path(p["video"]).exists()),
        "has_script": bool(p.get("script")), "error": p.get("error"),
        "job": {"status": job["status"], "progress": job["progress"], "message": job["message"]} if job else None,
    }


# ---------------------------------------------------------------- settings

@app.post("/api/settings")
async def save_settings(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    changed = []
    for key, value in data.items():
        if key == "ai_key":
            if isinstance(value, str) and value.startswith(("dpapi:", "plain:")):
                continue                      # untouched masked value
            store.set_setting("ai_key", secrets.protect(str(value or "").strip()))
            changed.append(key)
            continue
        if key not in store.DEFAULTS:
            continue
        try:
            if isinstance(store.DEFAULTS[key], bool):
                value = bool(value)
            elif isinstance(store.DEFAULTS[key], (int, float)) and not isinstance(value, bool):
                value = type(store.DEFAULTS[key])(value)
        except Exception:
            continue
        store.set_setting(key, value)
        changed.append(key)
    return {"ok": True, "changed": changed, "settings": public_settings()}


@app.get("/api/settings")
def read_settings() -> dict:
    return public_settings()


@app.post("/api/ai/test")
async def ai_test(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    # allow a dry run with values from the form before saving
    if data.get("model"):
        store.set_setting("ai_model", data["model"])
    if data.get("base_url"):
        store.set_setting("ai_base_url", data["base_url"])
    if data.get("provider"):
        store.set_setting("ai_provider", data["provider"])
    if data.get("key"):
        store.set_setting("ai_key", secrets.protect(str(data["key"])))
    try:
        return ai.test_connection()
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:500]}, status_code=200)


@app.post("/api/ai/detect")
async def ai_detect(request: Request) -> dict:
    """Paste a key, get a provider: the whole setup for people who don't know base URLs."""
    _guard(request)
    data = await body_json(request)
    result = ai.detect_provider(str(data.get("key") or ""))
    if data.get("apply"):
        store.set_setting("ai_provider", result["provider"])
        if result.get("base_url"):
            store.set_setting("ai_base_url", result["base_url"])
        if result.get("model"):
            store.set_setting("ai_model", result["model"])
        store.set_setting("ai_key", secrets.protect(str(data.get("key") or "").strip()))
    return result


@app.post("/api/ai/models")
async def ai_models(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    models = ai.list_models(base=(data.get("base_url") or None),
                            key=(data.get("key") if data.get("key") else None),
                            provider=(data.get("provider") or None))
    return {"ok": bool(models), "models": models,
            "error": None if models else "The endpoint did not answer with a model list — type the model name."}


@app.get("/api/ai/local")
def ai_local() -> dict:
    found = ai.find_local_models()
    return {"ok": bool(found), "servers": found,
            "hint": None if found else "No local model server found on this computer "
                                       "(Ollama, LM Studio, llama.cpp)."}


@app.get("/api/demo")
async def demo(request: Request) -> dict:
    """One click: a finished sample project so a new user can watch the product work."""
    _guard(request)
    brand = jobs.brand_from_settings()
    sample = """Four years of university is not the only way into a skilled job.

In Germany, an apprenticeship pays a wage from the first month, usually between 900 and 1200 euros,
and the employer covers the training. Half the week you work, half the week you are in school.

Most applicants send their file to three or four companies before anyone answers. The ones who
attach a short motivation letter in German get replies twice as often.

The contract is the only thing that matters for the visa. Without a signed contract you cannot
apply, and the process then takes eight to twelve weeks."""
    article = ingest.from_text(sample, "Apprenticeship in Germany")
    article["image"] = ""
    project = store.new_project(article["title"], "", "text")
    script, _ = autoscript.build(article, brand)
    meta = autoscript.meta(article, script, brand)
    store.update_project(project["id"],
                         article=article, script=script, meta=meta, brand=brand,
                         design={"mode": "auto", "theme": "navy_gold"},
                         status="draft")
    return {"ok": True, "project": store.get_project(project["id"])}


@app.get("/api/binaries")
def binaries() -> dict:
    return render.check_binaries()


@app.post("/api/binaries/detect")
async def binaries_detect(request: Request) -> dict:
    _guard(request)
    return render.check_binaries()


# ---------------------------------------------------------------- projects

@app.post("/api/project")
async def create_project(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    url = (data.get("url") or "").strip()
    text = (data.get("text") or "").strip()
    title = (data.get("title") or "").strip()
    pid = None
    if url:
        try:
            article = ingest.fetch(url)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)
        if article.get("listing"):
            return JSONResponse({"ok": False, "error": "That URL is a category/listing page — open a single article."},
                                status_code=200)
        project = store.new_project(article.get("title") or title or "Untitled", url, "url")
        pid = project["id"]
        store.update_project(pid, article=article, title=article.get("title") or title)
    elif text:
        article = ingest.from_text(text, title)
        project = store.new_project(title or article.get("title") or "Untitled", "", "text")
        pid = project["id"]
        store.update_project(pid, article=article)
    else:
        article = ingest.from_text("", title)
        project = store.new_project(title or "Untitled video", "", "text")
        pid = project["id"]
        store.update_project(pid, article=article)
    store.update_project(pid, brand=jobs.brand_from_settings(),
                         design={"mode": store.get_setting("default_design_mode") or "auto"})
    return {"ok": True, "project": store.get_project(pid)}


@app.get("/api/project/{pid}")
def get_project(pid: str) -> dict:
    p = _project_or_404(pid)
    out = dict(p)
    out["job"] = store.project_job(pid)
    out["page"] = f"/render/{pid}/index.html"
    out["video_url"] = f"/out/{pid}/video.mp4" if p.get("video") else None
    out["cover_url"] = f"/out/{pid}/cover.jpg" if p.get("cover") else None
    out["photo_url"] = f"/projects/{pid}/photo.jpg" if (paths.projects_dir() / pid / "photo.jpg").exists() else None
    return out


@app.patch("/api/project/{pid}")
async def patch_project(pid: str, request: Request) -> dict:
    _guard(request)
    _project_or_404(pid)
    data = await body_json(request)
    allowed = {k: v for k, v in data.items() if k in ("title", "script", "design", "brand", "meta", "status")}
    store.update_project(pid, **allowed)
    return {"ok": True, "project": store.get_project(pid)}


@app.delete("/api/project/{pid}")
async def delete_project(pid: str, request: Request) -> dict:
    _guard(request)
    _project_or_404(pid)
    store.delete_project(pid)
    for folder in (paths.projects_dir() / pid, paths.out_dir() / pid):
        shutil.rmtree(folder, ignore_errors=True)
    return {"ok": True}


@app.post("/api/project/{pid}/script")
async def write_script(pid: str, request: Request) -> dict:
    _guard(request)
    project = _project_or_404(pid)
    data = await body_json(request)
    mode = data.get("mode") or "ai"
    brand = project.get("brand") or jobs.brand_from_settings()
    article = project.get("article") or {}
    if mode == "blank":
        script = ai.blank_script(brand, ai._lang(article))
        store.update_project(pid, script=script, status="script_ready")
        return {"ok": True, "script": script, "warnings": []}
    if mode == "auto":
        script, warnings = autoscript.build(article, brand)
        meta = autoscript.meta(article, script, brand)
        store.update_project(pid, script=script, status="script_ready",
                             meta={**(project.get("meta") or {}), **meta},
                             error=None)
        return {"ok": True, "script": script, "warnings": warnings, "project": store.get_project(pid)}
    if (store.get_setting("ai_provider") or "none") == "none":
        return JSONResponse({"ok": False, "error": "No AI configured — use “Fill from the article” instead."},
                            status_code=200)
    try:
        result = ai.generate_script(project.get("article") or {}, brand,
                                    scene_count=int(data.get("scene_count") or 6),
                                    extra=(data.get("extra") or "").strip(),
                                    temperature=data.get("temperature"))
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:600]}, status_code=200)
    script = result["script"]
    script["title"] = script.get("title") or (project.get("title") or "")[:100]
    meta = project.get("meta") or {}
    if (data.get("extra") or "").strip():
        meta = {**meta, "brief": data["extra"].strip()}
    store.update_project(pid, script=script, meta=meta, status="script_ready",
                         error="; ".join(result.get("warnings") or [])[:400] or None)
    if store.get_setting("auto_meta", True) and not (meta.get("title") or meta.get("hashtags")):
        try:
            store.update_project(pid, meta={**meta, **ai.generate_meta(script, brand)})
        except Exception:
            pass
    return {"ok": True, "script": script, "warnings": result.get("warnings") or [],
            "project": store.get_project(pid)}


@app.post("/api/project/{pid}/scene")
async def rewrite_scene(pid: str, request: Request) -> dict:
    _guard(request)
    project = _project_or_404(pid)
    data = await body_json(request)
    index = int(data.get("index") or 0)
    instruction = (data.get("instruction") or "").strip()
    script = project.get("script") or {}
    scenes = script.get("scenes") or []
    if not (0 <= index < len(scenes)):
        raise HTTPException(400, "scene index out of range")
    if not instruction:
        return JSONResponse({"ok": False, "error": "Tell the AI what to change."}, status_code=200)
    try:
        new_scene = ai.rewrite_scene(scenes[index], instruction, project.get("article") or {},
                                     project.get("brand") or jobs.brand_from_settings())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:500]}, status_code=200)
    scenes[index] = new_scene
    script["scenes"] = scenes
    store.update_project(pid, script=script)
    return {"ok": True, "script": script}


@app.post("/api/project/{pid}/meta")
async def make_meta(pid: str, request: Request) -> dict:
    _guard(request)
    project = _project_or_404(pid)
    brand = project.get("brand") or jobs.brand_from_settings()
    if not project.get("script"):
        return JSONResponse({"ok": False, "error": "Write the script first."}, status_code=200)
    if (store.get_setting("ai_provider") or "none") == "none":
        meta = autoscript.meta(project.get("article") or {}, project["script"], brand)
        store.update_project(pid, meta={**(project.get("meta") or {}), **meta})
        return {"ok": True, "meta": store.get_project(pid).get("meta"), "mode": "auto"}
    try:
        meta = ai.generate_meta(project["script"], brand)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:500]}, status_code=200)
    store.update_project(pid, meta={**(project.get("meta") or {}), **meta})
    return {"ok": True, "meta": store.get_project(pid).get("meta")}


@app.post("/api/project/{pid}/preview")
async def preview(pid: str, request: Request) -> dict:
    """Recompose the page so the editor preview matches what will be rendered."""
    _guard(request)
    project = _project_or_404(pid)
    data = await body_json(request)
    if isinstance(data.get("script"), dict):
        store.update_project(pid, script=data["script"])
    if isinstance(data.get("design"), dict):
        store.update_project(pid, design={**(project.get("design") or {}), **data["design"]})
    project = store.get_project(pid)
    if not project.get("script"):
        return {"ok": False, "error": "no script yet"}
    try:
        info = jobs.compose_project(project)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:500]}, status_code=200)
    return {"ok": True, "page": f"/render/{pid}/index.html?preview=1&t={int(time.time() * 1000)}",
            "total": info["total"], "duration": info["total"], "scenes": info["scenes"],
            "design": info["design"], "rtl": info["rtl"]}


@app.post("/api/project/{pid}/render")
async def start_render(pid: str, request: Request) -> dict:
    _guard(request)
    _project_or_404(pid)
    data = await body_json(request)
    jobs.enqueue(pid, review=bool(data.get("review")) if "review" in data else False,
                 quality=data.get("quality"))
    return {"ok": True, "queued": True}


@app.post("/api/project/{pid}/cancel")
async def cancel_render(pid: str, request: Request) -> dict:
    _guard(request)
    jobs.cancel(pid)
    return {"ok": True}


@app.get("/api/project/{pid}/job")
def project_job(pid: str) -> dict:
    _project_or_404(pid)
    return {"job": store.project_job(pid), "project": _project_summary(store.get_project(pid))}


@app.post("/api/project/{pid}/frame")
async def single_frame(pid: str, request: Request) -> dict:
    """A quick thumbnail of the composed page without rendering the whole video."""
    _guard(request)
    project = _project_or_404(pid)
    if not project.get("script"):
        return {"ok": False, "error": "no script yet"}
    info = jobs.compose_project(project)
    seed = time.strftime("%H%M%S")
    with render.Browser(jobs.project_page_url(pid), info["canvas"]["w"], info["canvas"]["h"]) as br:
        br.seek(float(info["scenes"][0]["start"]) + 1.4)
        data = br.frame(92)
    shot = paths.projects_dir() / pid / f"thumb_{seed}.jpg"
    shot.write_bytes(data)
    return {"ok": True, "url": f"/projects/{pid}/{shot.name}"}


# ---------------------------------------------------------------- queue

@app.post("/api/queue/import")
async def queue_import(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    mode = data.get("mode") or "urls"
    created, skipped, errors = [], 0, []
    urls: list[str] = []
    if mode == "sitemap":
        try:
            urls = ingest.sitemap(data.get("sitemap") or "", data.get("prefix") or "",
                                  int(data.get("limit") or 50))
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)
    else:
        raw = data.get("urls") or []
        if isinstance(raw, str):
            raw = [u.strip() for u in raw.splitlines()]
        urls = [u.strip() for u in raw if str(u).strip()]
    known = {p.get("source_url") for p in store.list_projects(1000)}
    for url in urls:
        if not url.lower().startswith(("http://", "https://")):
            errors.append(f"{url[:40]}: not a URL")
            continue
        if url in known:
            skipped += 1
            continue
        try:
            article = ingest.fetch(url)
        except Exception as exc:
            errors.append(f"{url[-40:]}: {str(exc)[:120]}")
            continue
        if article.get("listing"):
            errors.append(f"{url[-40:]}: looks like a category/listing page, not an article")
            continue
        project = store.new_project(article.get("title") or url[-40:], url, "url")
        store.update_project(project["id"], article=article, brand=jobs.brand_from_settings(),
                             design={"mode": store.get_setting("default_design_mode") or "auto"},
                             status="queued" if store.get_setting("auto_render", True) else "draft")
        created.append(project["id"])
        time.sleep(1.2)                    # be polite to small sites
    if created and store.get_setting("auto_render", True):
        jobs.start()
    return {"ok": True, "created": created, "count": len(created), "skipped": skipped,
            "errors": errors[:20], "queue": jobs.status()}


@app.post("/api/queue/start")
async def queue_start(request: Request) -> dict:
    _guard(request)
    jobs.start()
    return {"ok": True, "queue": jobs.status()}


@app.post("/api/queue/stop")
async def queue_stop(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    if data.get("hard"):
        jobs.stop()
    else:
        store.set_setting("auto_render_queue", False)
    return {"ok": True, "queue": jobs.status()}


@app.get("/api/queue")
def queue_state() -> dict:
    """Anything in flight plus the most recent finished items, so the table is never a void."""
    recent = store.list_projects(40)
    return {"queue": jobs.status(), "projects": [_project_summary(p) for p in recent],
            "jobs": store.recent_jobs(20)}


@app.post("/api/queue/retry")
async def queue_retry(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    ids = data.get("ids") or []
    for pid in ids:
        jobs.enqueue(pid, review=False)
    return {"ok": True, "count": len(ids)}


# ---------------------------------------------------------------- assets, hooks, system

@app.get("/api/assets")
def asset_state() -> dict:
    return assets_pool.scan()


@app.post("/api/assets/rescan")
async def assets_rescan(request: Request) -> dict:
    _guard(request)
    return assets_pool.scan()


@app.get("/api/hooks")
def hooks_state() -> dict:
    return {"hooks": hooks.list_hooks(), "folder": str(paths.hooks_dir())}


@app.post("/api/hooks/example")
async def hooks_example(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    stage = data.get("stage") or "before_render"
    kind = data.get("kind") or "py"
    if stage not in hooks.STAGES:
        raise HTTPException(400, "unknown stage")
    target = paths.hooks_dir() / f"{stage}.{kind}"
    if target.exists() and not data.get("overwrite"):
        return {"ok": False, "error": f"{target.name} already exists"}
    target.write_text(hooks.example_hook(stage, kind), encoding="utf-8")
    return {"ok": True, "file": str(target), "hooks": hooks.list_hooks()}


@app.post("/api/open")
async def open_folder(request: Request) -> dict:
    _guard(request)
    data = await body_json(request)
    which = data.get("which") or "home"
    target = {"home": paths.home_dir(), "assets": paths.assets_dir(), "out": paths.out_dir(),
              "hooks": paths.hooks_dir(), "themes": paths.themes_dir(), "logs": paths.logs_dir()}.get(which)
    if data.get("path"):
        target = Path(data["path"])
    if not target or not Path(target).exists():
        raise HTTPException(404, "folder not found")
    try:
        if os.name == "nt":
            os.startfile(str(target))                    # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return {"ok": True, "path": str(target)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/log")
def app_log() -> dict:
    return {"lines": jobs.recent_log(120)}


@app.get("/api/about")
def about() -> dict:
    return {"version": APP_VERSION, "home": str(paths.home_dir()),
            "python": sys.version.split()[0], "frozen": paths.is_frozen(),
            "binaries": render.check_binaries()}


# ---------------------------------------------------------------- file routes

@app.get("/vendor/{name}")
def vendor(name: str, request: Request):
    return range_file(_safe_child(web_dir / "vendor", name), request)


@app.get("/ui/{name:path}")
def ui_file(name: str, request: Request):
    return range_file(_safe_child(web_dir, name), request)


@app.get("/assets/{rel:path}")
def asset_file(rel: str, request: Request):
    p = paths.asset(*Path(rel).parts)
    if not p.exists():
        raise HTTPException(404, "asset not found")
    return range_file(p, request)


@app.get("/render/{pid}/{name:path}")
def render_file(pid: str, name: str, request: Request):
    root = paths.projects_dir() / pid
    return range_file(_safe_child(root, name), request)


@app.get("/projects/{pid}/{name:path}")
def project_asset(pid: str, name: str, request: Request):
    root = paths.projects_dir() / pid
    return range_file(_safe_child(root, name), request)


@app.get("/out/{pid}/{name:path}")
def output_file(pid: str, name: str, request: Request):
    root = paths.out_dir() / pid
    return range_file(_safe_child(root, name), request)


@app.get("/favicon.svg")
def favicon_svg():
    p = web_dir / "favicon.svg"
    if p.exists():
        return FileResponse(p, media_type="image/svg+xml")
    return Response(status_code=204)


@app.get("/favicon.ico")
def favicon():
    p = web_dir / "favicon.svg"
    if p.exists():
        return FileResponse(p, media_type="image/svg+xml")
    return Response(status_code=204)


# ---------------------------------------------------------------- lifecycle

@app.on_event("startup")
def _startup() -> None:
    paths.ensure_home()
    store.init()
    jobs.start()
    jobs.log(f"Reelforge {APP_VERSION} · home {paths.home_dir()}")


@app.on_event("shutdown")
def _shutdown() -> None:
    jobs.stop()
