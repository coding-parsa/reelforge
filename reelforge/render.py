"""Render: drive a headless Chromium browser over CDP, then encode with ffmpeg.

Why this way: the video *is* the HTML page. We open it, seek its GSAP timeline
frame by frame, screenshot each frame and pipe the JPEGs straight into ffmpeg.
No Node, no Remotion, no npm — the only two external things are a Chromium-based
browser (Edge ships with Windows, Chrome anywhere) and ffmpeg.

The same page is what the app shows as a live preview, so what you see in the
editor is what lands in the file.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from . import paths, store

# ---------------------------------------------------------------- binaries

WIN_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
NIX_BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge", "/snap/bin/chromium",
]


def browser_bin() -> str | None:
    """Locate a Chromium-based browser. Cached in settings so users can override it."""
    custom = (store.get_setting("browser_path") or "").strip()
    if custom and Path(custom).exists():
        return custom
    for env in ("REELFORGE_BROWSER", "CHROME_PATH"):
        if os.environ.get(env) and Path(os.environ[env]).exists():
            return os.environ[env]
    candidates = WIN_BROWSERS if os.name == "nt" else NIX_BROWSERS
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("chrome", "chromium", "chromium-browser", "msedge", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def ffmpeg_bin(name: str = "ffmpeg") -> str | None:
    exe = f"{name}.exe" if os.name == "nt" else name
    custom = (store.get_setting("ffmpeg_path") or "").strip()
    if custom:
        p = Path(custom)
        if p.is_file() and p.name.lower().startswith(name):
            return str(p)
        if p.is_dir() and (p / exe).exists():
            return str(p / exe)
    for d in (paths.bin_dir(), paths.bundled_dir() / "bin", paths.app_root() / "bin"):
        if (d / exe).exists():
            return str(d / exe)
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        for d in (r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin",
                  str(Path.home() / "ffmpeg" / "bin"), str(Path.home() / "scoop" / "shims")):
            if (Path(d) / exe).exists():
                return str(Path(d) / exe)
    return None


def check_binaries() -> dict:
    ff, fp = ffmpeg_bin("ffmpeg"), ffmpeg_bin("ffprobe")
    br = browser_bin()
    return {
        "ffmpeg": ff, "ffprobe": fp, "browser": br,
        "ok": bool(ff and br),
        "hints": {
            "ffmpeg": None if ff else "Install ffmpeg and put ffmpeg.exe in the app's bin/ folder (or set the path in Settings).",
            "browser": None if br else "Install Chrome or Edge, or set the browser path in Settings.",
        },
    }


# ---------------------------------------------------------------- minimal CDP client

class CDPError(RuntimeError):
    pass


class CDP:
    """A very small Chrome DevTools Protocol client (websocket + request/response)."""

    def __init__(self, ws_url: str, timeout: float = 60.0):
        import websocket  # websocket-client
        self.ws = websocket.create_connection(ws_url, timeout=timeout, max_size=None,
                                              suppress_origin=True)
        self._id = 0
        self._lock = threading.Lock()

    def send(self, method: str, params: dict | None = None, timeout: float = 120.0) -> dict:
        with self._lock:
            self._id += 1
            mid = self._id
            self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            self.ws.settimeout(timeout)
            while True:
                raw = self.ws.recv()
                if not raw:
                    raise CDPError("browser closed the connection")
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if msg.get("id") == mid:
                    if "error" in msg:
                        raise CDPError(f"{method}: {msg['error'].get('message')}")
                    return msg.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = False, timeout: float = 120.0):
        res = self.send("Runtime.evaluate",
                        {"expression": expression, "awaitPromise": await_promise,
                         "returnByValue": True, "userGesture": True}, timeout=timeout)
        if res.get("exceptionDetails"):
            detail = res["exceptionDetails"]
            raise CDPError(str(detail.get("exception", {}).get("description") or detail))
        return res.get("result", {}).get("value")

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _http_json(port: int, path: str, tries: int = 80, delay: float = 0.15):
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:            # browser still starting
            last = exc
            time.sleep(delay)
    raise CDPError(f"browser did not answer on port {port}: {last}")


class Browser:
    """A headless browser with one page, kept alive for a whole render."""

    def __init__(self, url: str, width: int, height: int, scale: float = 1.0, log=print):
        self.url, self.width, self.height, self.scale = url, width, height, scale
        self.log = log
        self.proc: subprocess.Popen | None = None
        self.cdp: CDP | None = None
        self.profile = Path(tempfile.mkdtemp(prefix="reelforge-profile-"))

    def __enter__(self) -> "Browser":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        exe = browser_bin()
        if not exe:
            raise RuntimeError("No Chromium-based browser found (install Chrome or Edge).")
        port = _free_port()
        args = [
            exe, "--headless=new", f"--remote-debugging-port={port}",
            f"--user-data-dir={self.profile}",
            f"--window-size={self.width},{self.height}",
            "--hide-scrollbars", "--mute-audio", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
            "--autoplay-policy=no-user-gesture-required", "--force-device-scale-factor=1",
            "--remote-allow-origins=*",
            "--disable-features=CalculateNativeWinOcclusion",
            "about:blank",
        ]
        creation = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=creation)
        targets = _http_json(port, "/json/list")
        page = next((t for t in targets if t.get("type") == "page"), None)
        if not page:
            raise CDPError("browser opened without a page target")
        for attempt in range(3):
            try:
                self.cdp = CDP(page["webSocketDebuggerUrl"])
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(0.4)
                targets = _http_json(port, "/json/list")
                page = next((t for t in targets if t.get("type") == "page"), page)
        assert self.cdp
        self.cdp.send("Page.enable")
        self.cdp.send("Runtime.enable")
        self.cdp.send("Emulation.setDeviceMetricsOverride",
                      {"width": self.width, "height": self.height,
                       "deviceScaleFactor": self.scale, "mobile": False})
        self.cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
        self.cdp.send("Page.navigate", {"url": self.url})
        self.wait_ready()

    def wait_ready(self, timeout: float = 30.0) -> dict:
        expr = """(async () => {
          await document.fonts.ready;
          const vids = Array.from(document.querySelectorAll('video.clip'));
          await Promise.all(vids.map(v => new Promise(res => {
            if (v.readyState >= 2) return res(true);
            v.addEventListener('loadeddata', () => res(true), {once: true});
            v.addEventListener('error', () => res(false), {once: true});
            setTimeout(() => res(false), 12000);
          })));
          return {refs: !!window.rf, fonts: document.fonts.status, videos: vids.length,
                  ok: vids.filter(v => v.readyState >= 2).length};
        })()"""
        deadline = time.time() + timeout
        last: dict | None = None
        while time.time() < deadline:
            try:
                last = self.cdp.evaluate(expr, await_promise=True)
                if last and last.get("refs"):
                    return last
            except CDPError:
                pass
            time.sleep(0.2)
        raise CDPError(f"page did not become ready: {last}")

    def seek(self, t: float) -> None:
        self.cdp.evaluate(f"window.rf.seek({t:.3f})")

    def frame(self, quality: int = 95) -> bytes:
        res = self.cdp.send("Page.captureScreenshot",
                            {"format": "jpeg", "quality": quality, "fromSurface": True,
                             "captureBeyondViewport": False, "optimizeForSpeed": True}, timeout=60)
        return base64.b64decode(res["data"])

    def stop(self) -> None:
        if self.cdp:
            try:
                self.cdp.send("Browser.close", timeout=5)
            except Exception:
                pass
            self.cdp.close()
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=8)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        shutil.rmtree(self.profile, ignore_errors=True)


# ---------------------------------------------------------------- audio

def build_audio(plan: dict, total: float, out_wav: Path, *, music_volume: float = 0.3,
                sfx_enabled: bool = True, log=print) -> Path | None:
    """Mix music + sound effects into one wav with ffmpeg filter graphs."""
    ff = ffmpeg_bin("ffmpeg")
    if not ff:
        return None
    music = plan.get("music")
    sfx = [s for s in (plan.get("sfx") or []) if sfx_enabled and Path(s.get("src", "")).exists()]
    if not music and not sfx:
        return None

    inputs: list[str] = []
    if music and Path(music).exists():
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    for s in sfx:
        inputs += ["-i", str(s["src"])]

    fade_in, fade_out = 1.4, min(2.2, max(0.5, total * 0.1))
    parts = [f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={music_volume:.3f},"
             f"atrim=0:{total},asetpts=N/SR/TB,afade=t=in:st=0:d={fade_in},"
             f"afade=t=out:st={max(0.0, total - fade_out):.2f}:d={fade_out:.2f}[base]"]
    labels = ["[base]"]
    for k, s in enumerate(sfx):
        delay = int(max(0.0, float(s.get("at", 0))) * 1000)
        parts.append(f"[{k + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"volume={float(s.get('volume', 0.35)):.3f},adelay={delay}:all=1[s{k}]")
        labels.append(f"[s{k}]")
    parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,"
                                    f"alimiter=limit=0.95,atrim=0:{total}[aout]")

    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(parts), "-map", "[aout]", "-ar", "48000", "-ac", "2",
           "-t", f"{total}", str(out_wav)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_wav if out_wav.exists() and out_wav.stat().st_size > 1000 else None


# ---------------------------------------------------------------- render

def render(project_dir: Path, info: dict, out_path: Path, *, page_url: str, fps: int = 30,
           quality: str = "high", audio_src: dict | None = None, progress=None,
           cancel: threading.Event | None = None, log=print) -> dict:
    """Capture every frame of the composed page and encode the mp4."""
    ff = ffmpeg_bin("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg not found")
    total = float(info["total"])
    canvas = info.get("canvas") or {"w": 1080, "h": 1920}
    width, height = int(canvas["w"]), int(canvas["h"])
    draft = quality == "draft"
    scale = 0.5 if draft else 1.0
    jpeg_q = 84 if draft else 90
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(total * fps)))
    step = 1.0 / fps

    def tick(done: int, msg: str) -> None:
        if progress:
            progress(min(0.98, done / frames * 0.94), msg)

    wav = build_audio(audio_src or {}, total, project_dir / "audio.wav",
                      music_volume=float(store.get_setting("music_volume") or 0.3),
                      sfx_enabled=bool(store.get_setting("sfx_enabled")), log=log)

    with Browser(page_url, width, height, scale=scale, log=log) as br:
        stats = br.cdp.evaluate("(() => ({refs: !!window.rf, dur: window.rf ? window.rf.duration : 0}))()")
        if not (stats or {}).get("refs"):
            raise RuntimeError("page did not expose the render API")
        tick(0, "capturing frames")

        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "image2pipe", "-vcodec", "mjpeg", "-framerate", str(fps), "-i", "-"]
        if wav:
            cmd += ["-i", str(wav)]
        cmd += ["-map", "0:v"]
        if wav:
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast" if draft else "faster",
                "-crf", "24" if draft else "18", "-pix_fmt", "yuv420p",
                "-profile:v", "high", "-movflags", "+faststart", "-r", str(fps), str(out_path)]

        creation = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, creationflags=creation)
        try:
            for i in range(frames):
                if cancel is not None and cancel.is_set():
                    raise InterruptedError("cancelled")
                br.seek(i * step)
                png = br.frame(jpeg_q)
                enc.stdin.write(png)
                if i % 5 == 0:
                    tick(i, f"frame {i}/{frames}")
        except (BrokenPipeError, OSError) as exc:
            err = (enc.stderr.read() or b"").decode("utf-8", "replace")[-600:] if enc.stderr else ""
            raise RuntimeError(f"ffmpeg stopped early: {err or exc}")
        finally:
            try:
                enc.stdin.close()
            except Exception:
                pass
            code = enc.wait(timeout=300)
        if code != 0:
            err = (enc.stderr.read() or b"").decode("utf-8", "replace")[-600:] if enc.stderr else ""
            raise RuntimeError(f"ffmpeg exited {code}: {err}")

    if cancel is not None and cancel.is_set():
        raise InterruptedError("cancelled")
    tick(frames, "writing cover")
    duration = probe_duration(out_path)
    cover = None
    if store.get_setting("cover", True):
        cover = make_cover(out_path, out_path.parent / "cover.jpg")
        if cover:
            attach_cover(out_path, cover)
    if progress:
        progress(1.0, "done")
    return {"video": str(out_path), "cover": str(cover) if cover else None,
            "duration": duration, "size_mb": round(out_path.stat().st_size / 1e6, 2) if out_path.exists() else 0}


def probe_duration(path: Path) -> float:
    ff = ffmpeg_bin("ffprobe")
    if not ff:
        return 0.0
    try:
        out = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
                             capture_output=True, text=True, timeout=60)
        return round(float(out.stdout.strip()), 2)
    except Exception:
        return 0.0


def make_cover(video: Path, cover: Path, at: float = 0.04) -> Path | None:
    ff = ffmpeg_bin("ffmpeg")
    if not ff:
        return None
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(at), "-i", str(video),
                    "-frames:v", "1", "-q:v", "2", str(cover)], capture_output=True)
    return cover if cover.exists() else None


def attach_cover(video: Path, cover: Path) -> None:
    """Embed the cover as an attached picture (Telegram/Aparat pick it up as a thumbnail)."""
    ff = ffmpeg_bin("ffmpeg")
    if not ff:
        return
    tmp = video.with_suffix(".withcover.mp4")
    try:
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(cover),
                        "-map", "0", "-map", "1", "-c", "copy", "-c:v:1", "mjpeg",
                        "-disposition:v:1", "attached_pic", "-metadata:s:v:1", "title=Cover", str(tmp)],
                       capture_output=True, timeout=300)
        if tmp.exists() and tmp.stat().st_size > video.stat().st_size * 0.9:
            tmp.replace(video)
        else:
            tmp.unlink(missing_ok=True)
    except Exception:
        tmp.unlink(missing_ok=True)


def still_frame(out_path: Path, cover: Path) -> None:
    """Fallback when only a single frame is needed (thumbnail without a video)."""
    shutil.copyfile(cover, out_path)
