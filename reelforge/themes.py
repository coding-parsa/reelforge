"""Design system: theme packs, layouts, and the "never repeat a look" picker.

A design is six independent choices (theme x layout x background x transition x
frame x brand placement). The picker is seeded per project, and refuses anything
that appeared in the recent history, so a batch of 30 videos does not look like
30 copies of one template.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from . import paths, store

THEMES: dict[str, dict] = {
    "navy_gold": {"deep": "#081722", "surface": "#0b1d2b", "ink": "#faf9f6", "muted": "rgba(250,249,246,.82)",
                  "accent": "#f2d391", "accent_deep": "#5f4409", "glow_a": "rgba(199,154,60,.42)",
                  "glow_b": "rgba(56,148,190,.36)"},
    "forest_cream": {"deep": "#0d1f18", "surface": "#12291f", "ink": "#f3f1e7", "muted": "rgba(243,241,231,.82)",
                     "accent": "#dcc188", "accent_deep": "#4a3a12", "glow_a": "rgba(196,164,96,.40)",
                     "glow_b": "rgba(74,150,120,.34)"},
    "graphite_orange": {"deep": "#12100e", "surface": "#1c1814", "ink": "#f7f3ed", "muted": "rgba(247,243,237,.82)",
                        "accent": "#ffb173", "accent_deep": "#4a2200", "glow_a": "rgba(255,159,69,.40)",
                        "glow_b": "rgba(120,110,100,.34)"},
    "wine_sand": {"deep": "#1c0f14", "surface": "#2a161d", "ink": "#f7efe6", "muted": "rgba(247,239,230,.82)",
                  "accent": "#ecc39a", "accent_deep": "#4d2a12", "glow_a": "rgba(200,140,110,.38)",
                  "glow_b": "rgba(120,60,80,.36)"},
    "ink_teal": {"deep": "#061418", "surface": "#0a2027", "ink": "#eaf6f4", "muted": "rgba(234,246,244,.82)",
                 "accent": "#8fe0d5", "accent_deep": "#05403a", "glow_a": "rgba(111,211,199,.36)",
                 "glow_b": "rgba(30,90,120,.40)"},
    "plum_rose": {"deep": "#17101c", "surface": "#221630", "ink": "#f6ecf4", "muted": "rgba(246,236,244,.82)",
                  "accent": "#eeb3d0", "accent_deep": "#4a1c33", "glow_a": "rgba(227,166,200,.36)",
                  "glow_b": "rgba(90,60,140,.38)"},
    "slate_lime": {"deep": "#0e1416", "surface": "#16201f", "ink": "#eff4ee", "muted": "rgba(239,244,238,.82)",
                   "accent": "#cbe589", "accent_deep": "#2f3a10", "glow_a": "rgba(185,217,107,.34)",
                   "glow_b": "rgba(60,110,100,.36)"},
    "espresso_aqua": {"deep": "#191210", "surface": "#241a16", "ink": "#f5efe8", "muted": "rgba(245,239,232,.82)",
                      "accent": "#96d6e2", "accent_deep": "#0b3a44", "glow_a": "rgba(126,200,216,.34)",
                      "glow_b": "rgba(150,110,70,.34)"},
}

LAYOUTS = {
    "editorial": "Copy block bottom-left/right, rule above the paragraph.",
    "center": "Everything centred, maximum impact for one-liners.",
    "index": "Big ghost numeral behind the copy — reads like a numbered series.",
    "rail": "Vertical spine with a side label, editorial magazine feel.",
    "band": "Solid accent band across the frame; copy sits on it.",
    "auto": "Pick per video (recommended).",
}

BACKGROUNDS = {
    "footage": "Full-bleed video b-roll (needs clips in assets/broll).",
    "photo": "The article's own lead image, blurred and graded.",
    "duotone": "Two-colour wash over the footage — graphic, brand-safe.",
    "gradient": "Pure gradient mesh, no footage needed.",
    "split": "Footage top half, solid colour bottom half.",
    "auto": "Pick per video (recommended).",
}

TRANSITIONS = {"wipe": "Light sweep", "slide": "Colour bar slides across", "zoom": "Content punch-in",
               "flash": "White flash", "curtain": "Two-way curtain", "auto": "Pick per video"}

FRAMES = {"brackets": "Corner brackets", "border": "Hairline border", "rail": "Accent strip",
          "none": "No frame", "auto": "Pick per video"}

BRANDS = {"header": "Logo top corner", "minimal": "Small logo near the bottom",
          "vertical": "Rotated logo on the side", "none": "No logo", "auto": "Pick per video"}

FORMATS = {
    "9:16": {"w": 1080, "h": 1920, "label": "Vertical 9:16 (Reels, Shorts, TikTok)"},
    "1:1": {"w": 1080, "h": 1080, "label": "Square 1:1 (feed post)"},
    "16:9": {"w": 1920, "h": 1080, "label": "Landscape 16:9 (YouTube)"},
    "4:5": {"w": 1080, "h": 1350, "label": "Portrait 4:5 (Instagram feed)"},
}

AUTO_KEYS = ("theme", "layout", "background", "transition", "frame", "brand")


def load_custom_themes() -> dict[str, dict]:
    """Theme packs are plain JSON in <home>/themes, so anyone can add their own."""
    out: dict[str, dict] = {}
    for f in sorted(paths.themes_dir().glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if "themes" in data and isinstance(data["themes"], dict):
            for name, t in data["themes"].items():
                t = _normalize_theme(t)
                if t:
                    out[name] = t
            continue
        t = _normalize_theme(data)
        if t:
            out[str(data.get("name") or f.stem)] = t
    return out


REQUIRED = ("deep", "surface", "ink", "muted", "accent", "accent_deep", "glow_a", "glow_b")
FALLBACK_FILL = {"muted": "rgba(255,255,255,.8)", "glow_a": "rgba(255,255,255,.3)",
                 "glow_b": "rgba(0,0,0,.4)", "accent_deep": "#111111", "surface": "#111111",
                 "ink": "#ffffff"}


def _normalize_theme(t) -> dict | None:
    if not isinstance(t, dict) or "deep" not in t or "accent" not in t:
        return None
    out = {k: str(t.get(k, FALLBACK_FILL.get(k, "#000000"))) for k in REQUIRED}
    if "font" in t:
        out["font"] = str(t["font"])
    return out


def all_themes() -> dict[str, dict]:
    return {**THEMES, **load_custom_themes()}


def _key(d: dict) -> str:
    return "|".join(d[k] for k in AUTO_KEYS)


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def pick(design_seed: str, fixed: dict | None = None) -> dict:
    """Resolve a design. `fixed` keeps whatever the user chose and varies the rest."""
    fixed = dict(fixed or {})
    resolved: dict = {}
    auto = [k for k in AUTO_KEYS if fixed.get(k) in (None, "", "auto")]
    for k in AUTO_KEYS:
        if k not in auto:
            resolved[k] = fixed[k]
    if not auto:
        return resolved

    history = store.recent_recipes(24)
    seen = set(history)
    recent_themes = {h.split("|")[0] for h in history[-6:] if "|" in h}
    recent_layouts = {h.split("|")[1] for h in history[-4:] if "|" in h}
    catalog = {"theme": list(all_themes()), "layout": [k for k in LAYOUTS if k != "auto"],
               "background": [k for k in BACKGROUNDS if k != "auto"],
               "transition": [k for k in TRANSITIONS if k != "auto"],
               "frame": [k for k in FRAMES if k != "auto"],
               "brand": [k for k in BRANDS if k != "auto"]}
    rng = random.Random(_seed(design_seed))

    def complete() -> dict:
        full = dict(resolved)
        for k in auto:
            if k in ("layout", "background", "transition", "frame", "brand"):
                full[k] = rng.choice([c for c in catalog[k] if c not in seen])
            elif k == "theme":
                full[k] = rng.choice([c for c in catalog["theme"] if c not in recent_themes])
        return full

    for _ in range(400):
        full = complete()
        if _key(full) not in seen:
            break
    return {k: full[k] for k in AUTO_KEYS}


def describe(d: dict) -> str:
    return " · ".join(str(d.get(k, "")) for k in AUTO_KEYS)


def catalog() -> dict:
    themes = all_themes()
    return {
        "themes": [{"name": n, "deep": t["deep"], "accent": t["accent"], "ink": t.get("ink", "#fff")}
                   for n, t in themes.items()],
        "custom_themes": sorted(load_custom_themes()),
        "layouts": [{"name": k, "hint": v} for k, v in LAYOUTS.items()],
        "backgrounds": [{"name": k, "hint": v} for k, v in BACKGROUNDS.items()],
        "transitions": [{"name": k, "hint": v} for k, v in TRANSITIONS.items()],
        "frames": [{"name": k, "hint": v} for k, v in FRAMES.items()],
        "brands": [{"name": k, "hint": v} for k, v in BRANDS.items()],
        "formats": [{"name": k, "w": v["w"], "h": v["h"], "label": v["label"]} for k, v in FORMATS.items()],
    }
