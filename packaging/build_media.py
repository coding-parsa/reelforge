"""Generate the starter media Reelforge ships: abstract b-roll loops and quiet pads.

Everything is synthesised with ffmpeg, so the repository and the installer carry
no third-party footage or music licences. The clips are deliberately abstract —
slow light, grain, soft motion — because they sit *behind* text and must never
compete with it.

    python packaging/build_media.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BROLL = ROOT / "assets" / "broll"
MUSIC = ROOT / "assets" / "music"
FF = "ffmpeg"

W, H, D, FPS = 720, 1280, 8, 24

# name, chroma amplitude (blue-ish, red-ish), drift speed — each clip gets its own weather
CLIPS = [
    ("ambient-01", 38, -26, 0.012),   # cool blue
    ("ambient-02", -32, 30, 0.009),   # warm amber
    ("ambient-03", 30, 24, 0.015),    # teal / sand
    ("ambient-04", -22, -34, 0.007),  # violet
]


def broll() -> None:
    BROLL.mkdir(parents=True, exist_ok=True)
    for name, cb_amp, cr_amp, speed in CLIPS:
        # a slow colour field: luma and both chroma planes drift at different rates,
        # then heavy blur turns it into weather rather than a pattern
        plasma = (f"geq=lum='92+62*sin(X/{W // 3}+T*{speed * 60})+44*sin(Y/{H // 4}-T*{speed * 45})"
                  f"+18*sin((X+Y)/230+T*0.4)':"
                  f"cb='128+{cb_amp}*sin(Y/{H // 3}+T*{speed * 48})':"
                  f"cr='128+{cr_amp}*cos(X/{W // 2}-T*{speed * 33})'")
        out = BROLL / f"{name}.mp4"
        cmd = [FF, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", f"nullsrc=s={W}x{H}:d={D}:r={FPS}",
               "-vf", f"{plasma},eq=saturation=1.25:contrast=1.02,"
                      f"gblur=sigma=26,noise=alls=7:allf=t+u,vignette=PI/5,format=yuv420p",
               "-c:v", "libx264", "-preset", "slow", "-crf", "29", "-t", str(D),
               "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
        print("broll", out.name, round(out.stat().st_size / 1024), "KB")


# name, chord (Hz), tremolo rate
PADS = [
    ("pad-01", [110.00, 164.81, 220.00, 329.63], 0.07),   # A minor-ish
    ("pad-02", [98.00, 146.83, 196.00, 293.66], 0.05),    # G
    ("pad-03", [130.81, 196.00, 261.63, 392.00], 0.09),   # C
]


def music() -> None:
    MUSIC.mkdir(parents=True, exist_ok=True)
    for name, chord, trem in PADS:
        parts = "+".join(f"{0.11 / (i + 1):.3f}*sin(2*PI*{f}*t)*(1+0.35*sin(2*PI*{trem + i * 0.013}*t))"
                         for i, f in enumerate(chord))
        # a slow filter sweep keeps it from sounding like a held organ note
        expr = f"aevalsrc='({parts})*(0.85+0.15*sin(2*PI*0.03*t))':d=45:s=48000"
        out = MUSIC / f"{name}.mp3"
        cmd = [FF, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", expr,
               "-af", "lowpass=f=900,highpass=f=60,aecho=0.7:0.6:220|420:0.28|0.18,"
                      "afade=t=in:st=0:d=3,afade=t=out:st=41:d=4,loudnorm=I=-26:TP=-6,"
                      "aformat=sample_rates=48000:channel_layouts=stereo",
               "-c:a", "libmp3lame", "-b:a", "96k", "-t", "45", str(out)]
        subprocess.run(cmd, check=True)
        print("music", out.name, round(out.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    broll()
    music()
