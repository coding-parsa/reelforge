"""The asset pool: b-roll clips, music beds, sound effects, photos.

Everything is optional. With an empty `assets/` folder Reelforge still renders —
it falls back to gradient / photo backgrounds and a silent track — so a first
run works before the user has downloaded a single clip.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from pathlib import Path

from . import paths

VIDEO_EXT = (".mp4", ".webm", ".mov", ".mkv")
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")

# filename tag -> words that should pull that footage in
TOPIC_WORDS: dict[str, list[str]] = {
    "china": ["چین", "چینی", "پکن", "china", "beijing"],
    "russia": ["روسیه", "روسی", "مسکو", "russia", "moscow"],
    "turkey": ["ترکیه", "ترکی", "استانبول", "turkey", "istanbul"],
    "germany": ["آلمان", "آلمانی", "germany", "berlin"],
    "visa": ["ویزا", "اقامت", "پاسپورت", "پرونده", "visa", "passport", "documents"],
    "money": ["هزینه", "پول", "بورس", "شهریه", "دستمزد", "مالیات", "cost", "money", "budget"],
    "study": ["تحصیل", "دانشجو", "دانشگاه", "بورسیه", "کلاس", "امتحان", "مدرک", "study",
              "student", "university", "campus"],
    "job": ["کار", "استخدام", "شغل", "کارفرما", "رزومه", "job", "office", "interview"],
    "travel": ["سفر", "پرواز", "فرودگاه", "مهاجرت", "travel", "airport", "flight"],
}
TOPIC_TAGS = {
    "china": ["china", "beijing", "city"],
    "russia": ["russia", "moscow", "train"],
    "turkey": ["istanbul", "airport", "city"],
    "germany": ["germany", "train", "city"],
    "visa": ["passport", "documents", "airport", "suitcase"],
    "money": ["money", "bank", "city"],
    "study": ["student", "students", "university", "classroom", "library", "exam", "graduation", "campus"],
    "job": ["office", "meeting", "laptop", "writing", "handshake"],
    "travel": ["airport", "suitcase", "train", "city-life", "urban", "street-life", "map"],
}

_dur_cache: dict[str, float] = {}
_dur_lock = threading.Lock()
_cache_file = paths.data_dir() / "clip_durations.json"


def _load_cache() -> None:
    global _dur_cache
    if _dur_cache:
        return
    try:
        _dur_cache = json.loads(_cache_file.read_text(encoding="utf-8"))
    except Exception:
        _dur_cache = {}


def h(*parts) -> int:
    return int(hashlib.md5("".join(str(p) for p in parts).encode("utf-8")).hexdigest(), 16)


def clip_duration(path: Path) -> float:
    """Cached ffprobe duration; 0.0 when unknown (the renderer then ignores looping)."""
    from .render import ffmpeg_bin  # local import keeps module import cheap
    key = str(path)
    _load_cache()
    with _dur_lock:
        if key in _dur_cache:
            return float(_dur_cache[key])
    ff = ffmpeg_bin("ffprobe")
    dur = 0.0
    if ff:
        try:
            out = subprocess.run([ff, "-v", "error", "-show_entries", "format=duration",
                                  "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
                                 capture_output=True, text=True, timeout=30)
            dur = round(float(out.stdout.strip()), 2)
        except Exception:
            dur = 0.0
    with _dur_lock:
        _dur_cache[key] = dur
        try:
            _cache_file.write_text(json.dumps(_dur_cache), encoding="utf-8")
        except Exception:
            pass
    return dur


def _files(sub: str, exts: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for base in (paths.assets_dir() / sub, paths.bundled_assets_dir() / sub):
        if base.is_dir():
            out += [p for p in sorted(base.iterdir()) if p.is_file() and p.suffix.lower() in exts]
    # de-duplicate by name, user pool wins
    seen: dict[str, Path] = {}
    for p in out:
        seen.setdefault(p.name, p)
    return list(seen.values())


def scan() -> dict:
    broll = _files("broll", VIDEO_EXT)
    music = _files("music", AUDIO_EXT)
    photos = _files("", IMAGE_EXT) + _files("photos", IMAGE_EXT)
    sfx: dict[str, str] = {}
    for p in _files("sfx", AUDIO_EXT):
        stem = p.stem.lower()
        for kind in ("whoosh", "tick", "thump", "pop", "hit", "click"):
            if stem.startswith(kind) and kind not in sfx:
                sfx[kind] = str(p)
    return {
        "broll": [str(p) for p in broll],
        "music": [str(p) for p in music],
        "photos": [str(p) for p in photos],
        "sfx": sfx,
        "counts": {"broll": len(broll), "music": len(music), "sfx": len(sfx), "photos": len(photos)},
    }


def tag_of(path: str) -> str:
    name = Path(path).stem
    return name.rsplit("-", 1)[0].lower() if "-" in name else name.lower()


def topics_in(text: str) -> list[str]:
    low = text.lower()
    return [t for t, words in TOPIC_WORDS.items() if any(w in low for w in words)]


def pick_clip(pool: list[str], text: str, seed: str, used: set[str]) -> str | None:
    """Prefer footage whose filename topic matches the card's words."""
    if not pool:
        return None
    by_tag: dict[str, list[str]] = {}
    for c in pool:
        by_tag.setdefault(tag_of(c), []).append(c)
    topics = topics_in(text)
    ranked: list[str] = []
    for t in topics:
        for tag in TOPIC_TAGS.get(t, []):
            ranked += [c for c in by_tag.get(tag, []) if c not in used]
    fresh = [c for c in pool if c not in used]
    if not ranked:
        ranked = fresh
    if not ranked:
        ranked = fresh or pool
    return ranked[h(seed, text[:40]) % len(ranked)]


def pick_music(pool: list[str], seed: str) -> str | None:
    if not pool:
        return None
    return pool[h(seed, "music") % len(pool)]
