"""EXAMPLE — do something with the finished file: upload it, file it, log it.

Copy to `<home>/hooks/after_render.py`. Whatever dict you return is stored on the
project and shown in the UI, so put the public URL in "url".

Only standard-library code here on purpose: this runs inside the app's own
interpreter, so third-party packages may not be installed. Call an external tool
with subprocess when you need one (e.g. your own uploader CLI).
"""
import json
import os
import shutil
import urllib.request


def run(payload):
    video = payload["video"]
    cover = payload.get("cover")
    title = (payload.get("script") or {}).get("title", "video")

    # 1. copy the files somewhere your team can pick them up
    drop = os.path.join(os.path.expanduser("~"), "Reelforge-done")
    os.makedirs(drop, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:60].strip() or "video"
    target = os.path.join(drop, safe + ".mp4")
    shutil.copy2(video, target)

    # 2. call your own uploader, if you have one on PATH
    # subprocess.run(["my-uploader", target], check=True)

    # 3. or POST it somewhere that accepts a file path
    # body = json.dumps({"title": title}).encode()
    # urllib.request.urlopen(urllib.request.Request(
    #     "https://example.com/api/ingest", data=body,
    #     headers={"Content-Type": "application/json"}), timeout=30)

    return {"url": "file:///" + target.replace("\\", "/"), "copied_to": target}
