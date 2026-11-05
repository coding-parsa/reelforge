"""Generate the small binary assets Reelforge ships: sound effects and the app icon.

Everything here is synthesised from scratch (ffmpeg / PIL), so the repo carries no
third-party media licences. Run from the repo root:

    python packaging/build_assets.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX = ROOT / "assets" / "sfx"
ICON = ROOT / "packaging" / "reelforge.ico"

FF = "ffmpeg"


def sfx() -> None:
    SFX.mkdir(parents=True, exist_ok=True)
    jobs = {
        # a short filtered-noise sweep: the "whoosh" between cards
        "whoosh.mp3": (
            "-f lavfi -i anoisesrc=d=0.62:c=pink:a=0.7",
            "highpass=f=240,lowpass=f=7000,"
            "afade=t=in:st=0:d=0.16,afade=t=out:st=0.17:d=0.45,"
            "volume=1.1,loudnorm=I=-22:TP=-3",
        ),
        # a dry click for list rows
        "tick.mp3": (
            '-f lavfi -i "aevalsrc=0.45*sin(2*PI*2100*t)*exp(-70*t):d=0.09:s=48000"',
            "loudnorm=I=-24:TP=-4",
        ),
        # a low hit under the CTA card
        "thump.mp3": (
            '-f lavfi -i "aevalsrc=0.85*sin(2*PI*72*t)*exp(-13*t)+0.25*sin(2*PI*144*t)*exp(-22*t):d=0.45:s=48000"',
            "loudnorm=I=-18:TP=-3",
        ),
    }
    for name, (src, af) in jobs.items():
        out = SFX / name
        cmd = f'{FF} -hide_banner -loglevel error -y {src} -af "{af}" -c:a libmp3lame -b:a 128k "{out}"'
        subprocess.run(cmd, shell=True, check=True)
        print("wrote", out.relative_to(ROOT), out.stat().st_size, "bytes")


def icon() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not available — skipping the icon (the exe then uses the default one)")
        return
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=56, fill=(10, 12, 16, 255))
    # an R drawn as geometry so the icon never depends on an installed font
    gold = (240, 194, 107, 255)
    d.rounded_rectangle([70, 48, 108, 208], radius=6, fill=gold)                    # stem
    d.rounded_rectangle([104, 48, 168, 120], radius=36, fill=gold)                  # bowl
    d.rounded_rectangle([118, 66, 168, 102], radius=18, fill=(10, 12, 16, 255))     # bowl hole
    d.polygon([(138, 116), (176, 116), (206, 208), (168, 208)], fill=gold)          # leg
    d.ellipse([184, 26, 220, 62], fill=(111, 214, 196, 255))                        # accent dot
    img.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", ICON.relative_to(ROOT))


if __name__ == "__main__":
    sfx()
    icon()
