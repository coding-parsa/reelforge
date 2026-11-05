"""Start the local server and show it in a real window.

No Electron, no bundled Chromium: the UI is served from 127.0.0.1 and shown with
the browser's app mode (Edge ships with Windows, Chrome with macOS), which looks
like a native window and costs nothing to distribute. pywebview is used instead
when the user has it installed.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import jobs, paths, render, store


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def port_file() -> Path:
    return paths.data_dir() / "port.json"


def existing_instance() -> str | None:
    """URL of a live instance — but only if it is the same version as this exe.

    A window left open from the previous release would otherwise be reused after an
    update, and every bug you just fixed keeps happening.
    """
    try:
        info = json.loads(port_file().read_text(encoding="utf-8"))
        port = int(info["port"])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/about", timeout=1.5) as r:
            if r.status != 200:
                return None
            running = json.loads(r.read().decode("utf-8", "replace")).get("version")
        from . import server
        if running and running != server.APP_VERSION:
            print(f"An older Reelforge ({running}) is running on port {port}; replacing it.")
            _stop_instance(int(info.get("pid") or 0))
            _close_stale_windows(port)
            time.sleep(1.5)
            return None
        return f"http://127.0.0.1:{port}/"
    except Exception:
        return None


def _close_stale_windows(port: int) -> None:
    """The old build's window now points at a dead server: close it instead of leaving a corpse."""
    if os.name != "nt":
        return
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
          f"Where-Object {{ $_.CommandLine -like '*--app=http://127.0.0.1:{port}/*' }} | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=20)
    except Exception:
        pass


def _stop_instance(pid: int) -> None:
    """Only ever kills a process whose image is this app."""
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)
        else:
            os.kill(pid, 15)
    except Exception:
        pass


def wait_ready(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/about", timeout=1.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def open_window(url: str, title: str = "Reelforge") -> subprocess.Popen | None:
    """App-mode browser window; falls back to the default browser."""
    try:
        import webview  # optional: pip install pywebview
        webview.create_window(title, url, width=1480, height=960, min_size=(1100, 720))
        webview.start()
        return None
    except Exception:
        pass

    exe = render.browser_bin()
    profile = paths.data_dir() / "window-profile"
    profile.mkdir(parents=True, exist_ok=True)
    if exe:
        args = [exe, f"--app={url}", "--window-size=1480,960", "--window-position=80,50",
                f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
                "--disable-features=Translate", "--app-auto-launched"]
        try:
            creation = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            return subprocess.Popen(args, creationflags=creation)
        except Exception:
            pass
    webbrowser.open(url)
    return None


def _ensure_streams() -> None:
    """A windowed exe has no stdout/stderr; uvicorn and our own logs need one."""
    if sys.stdout is None or sys.stderr is None:
        fh = open(paths.logs_dir() / "app.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = fh
        if sys.stderr is None:
            sys.stderr = fh


def run(args) -> int:
    _ensure_streams()
    if args.run_hook:
        from .hookrunner import main as hook_main
        sys.argv = ["hookrunner", args.run_hook] + (["--out", args.hook_out] if args.hook_out else [])
        return hook_main()

    paths.ensure_home()
    store.init()
    if not args.new and existing_instance():
        url = existing_instance()
        if url:
            print(f"Reelforge is already running at {url}")
            if not args.no_window:
                open_window(url)
            return 0

    port = args.port or free_port()
    port_file().write_text(json.dumps({"port": port, "pid": os.getpid()}), encoding="utf-8")
    jobs.set_base_url(f"http://127.0.0.1:{port}")

    import uvicorn
    from .server import app

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                            access_log=False, loop="asyncio")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="reelforge-http", daemon=True)
    thread.start()
    if not wait_ready(port):
        print("server failed to start", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{port}/"
    print(f"Reelforge {url}")

    if args.no_window:
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        proc = open_window(url)
        if proc is not None:
            proc.wait()
        else:
            # window closed by pywebview/webbrowser: keep serving until interrupted
            try:
                while thread.is_alive():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
    server.should_exit = True
    jobs.stop()
    time.sleep(0.3)
    try:
        port_file().unlink(missing_ok=True)
    except Exception:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reelforge", description="Reelforge — AI short-video studio")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-window", action="store_true", help="serve only (open the URL yourself)")
    ap.add_argument("--new", action="store_true", help="start a second instance")
    ap.add_argument("--run-hook", default="", help=argparse.SUPPRESS)
    ap.add_argument("--out", dest="hook_out", default="", help=argparse.SUPPRESS)
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args(argv)
    if args.version:
        from . import server
        print(f"Reelforge {server.APP_VERSION}")
        return 0
    return run(args)
