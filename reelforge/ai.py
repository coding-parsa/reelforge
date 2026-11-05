"""AI layer: bring your own key, any provider, and prompts you can rewrite.

Supported out of the box:
  * OpenAI and every OpenAI-compatible endpoint (OpenRouter, Groq, DeepSeek, xAI,
    Together, Mistral, Fireworks, Ollama, LM Studio, vLLM…)
  * Anthropic (Claude)
  * Google Gemini

Nothing about the provider is hard-coded in the app: base URL, model and key are
user settings, and the prompt templates are editable text with {{placeholders}}.
"""
from __future__ import annotations

import json
import re
from typing import Any

import requests

from . import secrets as _secrets
from . import store

MAX_ARTICLE_CHARS = 14000
PROVIDERS = {
    "openai": {"label": "OpenAI-compatible", "default_base": "https://api.openai.com/v1",
               "hint": "Works with OpenAI, OpenRouter, Groq, DeepSeek, xAI, Together, Mistral, "
                       "Ollama, LM Studio, vLLM — anything that speaks /chat/completions."},
    "anthropic": {"label": "Anthropic", "default_base": "https://api.anthropic.com",
                  "hint": "Claude models (claude-3-5-sonnet-latest, claude-3-5-haiku-latest…)."},
    "gemini": {"label": "Google Gemini", "default_base": "https://generativelanguage.googleapis.com/v1beta",
               "hint": "gemini-2.0-flash, gemini-1.5-pro…"},
    "none": {"label": "No AI (write or script it yourself)", "default_base": "", "hint": ""},
}

DEFAULT_SCRIPT_PROMPT = """You write scripts for silent vertical short videos (Reels / Shorts / TikTok).
A card on screen must be readable in the time a scene lasts, so every word has to earn its place.

Article title: {{title}}
Article URL: {{url}}
Source language: {{source_language}}
Output language: {{language}}
Call to action (use exactly this, translated only if the output language differs): {{cta}}

ARTICLE
-------
{{article}}
-------

Return ONE JSON object, nothing else, in this exact shape:

{
  "title": "internal video title, max 60 chars",
  "scenes": [
    {"kind": "fact", "kicker": "2-3 words", "big": "line one\\nline two", "body": "one complete sentence", "chip": "max 4 words"},
    {"kind": "stat", "kicker": "2-3 words", "num": 25000, "unit": "people a year", "big": "what the number means", "chip": "max 4 words"},
    {"kind": "list", "kicker": "2-3 words", "big": "line one\\nline two", "bullets": ["item one", "item two", "item three"]},
    {"kind": "cta", "kicker": "brand name", "big": "line one\\nline two", "body": "one sentence with the offer", "chip": "button text"}
  ]
}

Hard rules — a script that breaks them is unusable:
1. {{scene_count}} scenes total. Scene 1 is the hook: the single most surprising or most expensive
   fact in the article, stated plainly. The last scene is the CTA and is always exactly the CTA above.
2. "big" is a headline and must be AT MOST 7 words, split into exactly two lines with \\n.
   No trailing punctuation. Exception: a "stat" card's "big" is one short line.
3. "fact" and "cta" cards have "body": ONE complete sentence, 12-30 words, in the article's language.
   "list" cards have 3-4 bullets instead, each at most 9 words. "stat" cards have no body.
4. "kicker" is 2-3 words and must NOT repeat the words of "big" — it adds a second layer of meaning
   (the cause, the trap, the cost), not a label.
5. "chip" is at most 4 words. Use it for the detail that does not fit in the headline.
6. Numbers: only numbers that appear in the article. "num" must be a plain integer (25000, not "25k").
   Put ranges and units in "unit" or "chip".
7. Never invent facts, quotes, dates or promises the article does not make. If the article is vague,
   be vague in the same way — do not sharpen it.
8. No references to tables, figures, sections, "as you can read below", no legal citations
   (§, "Article 16"), no TL;DR, no disclaimers.
9. Vary the card shapes: do not start every card the same way, and avoid the same headline pattern
   twice in one video.
10. The CTA scene keeps the brand's own words; do not rewrite the offer.
"""

DEFAULT_META_PROMPT = """You write the publishing metadata for a short video.

Video script (JSON): {{script}}
Language: {{language}}
Brand site: {{site}}

Return ONE JSON object:
{"title": "video title, max 70 chars, no clickbait emoji", 
 "description": "2-3 sentences for the platform description",
 "hashtags": ["#tag", "..."], 
 "hook_line": "the first line a viewer reads, max 90 chars"}

Use 5-8 hashtags, mixing broad and specific, in the video's language (Latin hashtags are fine).
Do not invent facts that are not in the script.
"""


class AIError(RuntimeError):
    pass


# ---------------------------------------------------------------- transport

def chat(messages: list[dict], *, temperature: float | None = None, max_tokens: int = 3000,
         timeout: int = 180) -> str:
    """One completion. `messages` is [{role, content}, …] in OpenAI shape."""
    provider = (store.get_setting("ai_provider") or "openai").lower()
    model = (store.get_setting("ai_model") or "").strip()
    base = (store.get_setting("ai_base_url") or "").strip().rstrip("/")
    key = _secrets.unprotect(store.get_setting("ai_key") or "")
    temp = store.get_setting("ai_temperature")
    temp = float(temperature if temperature is not None else (temp if temp is not None else 0.7))

    if provider == "none":
        raise AIError("No AI provider configured. Open Settings → AI and add a key, or write the script by hand.")
    if not model:
        raise AIError("No model set in Settings → AI.")

    if provider == "anthropic":
        url = (base or PROVIDERS["anthropic"]["default_base"]) + "/v1/messages"
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        body = {"model": model, "max_tokens": max_tokens, "temperature": temp,
                "messages": [m for m in messages if m["role"] != "system"]}
        if system:
            body["system"] = system
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        resp = requests.post(url, json=body, headers=headers, timeout=timeout)
        if resp.status_code >= 400:
            raise AIError(_http_error("Anthropic", resp))
        data = resp.json()
        return "".join(part.get("text", "") for part in data.get("content", []) if isinstance(part, dict))

    if provider == "gemini":
        root = base or PROVIDERS["gemini"]["default_base"]
        url = f"{root}/models/{model}:generateContent?key={key}"
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [{"role": "user" if m["role"] != "assistant" else "model", "parts": [{"text": m["content"]}]}
                    for m in messages if m["role"] != "system"]
        body: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": temp,
                                                                          "maxOutputTokens": max_tokens}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        resp = requests.post(url, json=body, timeout=timeout)
        if resp.status_code >= 400:
            raise AIError(_http_error("Gemini", resp))
        data = resp.json()
        try:
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except Exception:
            raise AIError(f"Gemini returned an unexpected shape: {str(data)[:300]}")

    # ---- OpenAI-compatible (the default path)
    url = (base or PROVIDERS["openai"]["default_base"]) + "/chat/completions"
    body = {"model": model, "messages": messages, "temperature": temp, "max_tokens": max_tokens}
    extra = (store.get_setting("ai_extra") or "").strip()
    if extra:
        try:
            body.update(json.loads(extra))
        except Exception:
            pass
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise AIError(_http_error("provider", resp))
    data = resp.json()
    try:
        choice = data["choices"][0]["message"]
    except Exception:
        raise AIError(f"Unexpected response: {str(data)[:300]}")
    content = choice.get("content")
    if isinstance(content, list):        # some providers return content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _http_error(name: str, resp) -> str:
    detail = ""
    try:
        payload = resp.json()
        detail = payload.get("error", {}).get("message") if isinstance(payload.get("error"), dict) else str(payload)[:300]
    except Exception:
        detail = (resp.text or "")[:300]
    return f"{name} HTTP {resp.status_code}: {detail}"


def test_connection() -> dict:
    out = chat([{"role": "user", "content": "Reply with the single word: ok"}], temperature=0, max_tokens=16)
    return {"ok": True, "reply": (out or "").strip()[:80]}


# ---------------------------------------------------------------- JSON

def extract_json(text: str) -> dict:
    """Pull the first complete JSON object out of a model reply."""
    if not text:
        raise AIError("empty reply")
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    start = t.find("{")
    if start < 0:
        raise AIError("no JSON object in the reply")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = t[start:i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    fixed = re.sub(r",\s*([}\]])", r"\1", chunk)
                    fixed = fixed.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'")
                    return json.loads(fixed)
    raise AIError("the JSON object never closed")


# ---------------------------------------------------------------- prompts

def _template(key: str, fallback: str) -> str:
    custom = (store.get_setting(key) or "").strip()
    return custom or fallback


def _lang(article: dict) -> str:
    want = (store.get_setting("ai_language") or "auto").lower()
    if want != "auto":
        return want
    lang = article.get("lang") or "en"
    return {"und": "en"}.get(lang, lang)


def build_script_prompt(article: dict, brand: dict, scene_count: int = 6, extra: str = "") -> str:
    tpl = _template("prompt_script", DEFAULT_SCRIPT_PROMPT)
    body = (article.get("text") or "")[:MAX_ARTICLE_CHARS]
    if not body and article.get("blocks"):
        body = "\n\n".join(b["text"] for b in article["blocks"])[:MAX_ARTICLE_CHARS]
    cta = brand.get("cta_title") or ""
    if brand.get("cta_body"):
        cta = f"{cta}. {brand['cta_body']}".strip(". ")
    lang = _lang(article)
    values = {
        "title": article.get("title", ""),
        "url": article.get("url", ""),
        "article": body,
        "language": lang,
        "source_language": article.get("lang", "unknown"),
        "scene_count": scene_count,
        "cta": cta or "the brand's own call to action",
        "site": brand.get("site", ""),
        "brand": brand.get("name", ""),
        "extra": extra,
    }
    out = tpl
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", str(v))
    if extra:
        out += f"\n\nADDITIONAL INSTRUCTION FROM THE USER (obey it, it overrides tone/length defaults):\n{extra}\n"
    return out


def generate_script(article: dict, brand: dict, *, scene_count: int = 6, extra: str = "",
                    temperature: float | None = None) -> dict:
    prompt = build_script_prompt(article, brand, scene_count, extra)
    messages = [
        {"role": "system", "content": "You are a senior short-form video scriptwriter. "
                                      "You answer with a single JSON object and nothing else."},
        {"role": "user", "content": prompt},
    ]
    reply = chat(messages, temperature=temperature)
    try:
        data = extract_json(reply)
        script, warnings = normalize_script(data, brand, lang=_lang(article))
        return {"script": script, "warnings": warnings, "raw": reply[:4000]}
    except Exception as exc:
        # one corrective round-trip beats a broken video
        fix = messages + [
            {"role": "assistant", "content": reply[:4000]},
            {"role": "user", "content": f"That reply could not be used ({exc}). Reply again with ONLY the "
                                        f"JSON object, no prose, no code fences, following every rule."},
        ]
        reply2 = chat(fix, temperature=0.3)
        data = extract_json(reply2)
        script, warnings = normalize_script(data, brand, lang=_lang(article))
        return {"script": script, "warnings": warnings + ["the model needed a second attempt"], "raw": reply2[:4000]}


def generate_meta(script: dict, brand: dict) -> dict:
    tpl = _template("prompt_meta", DEFAULT_META_PROMPT)
    body = json.dumps({k: v for k, v in script.items() if k != "raw"}, ensure_ascii=False)[:6000]
    prompt = (tpl.replace("{{script}}", body)
                 .replace("{{language}}", script.get("lang") or "auto")
                 .replace("{{site}}", brand.get("site", "")))
    reply = chat([{"role": "system", "content": "You output one JSON object and nothing else."},
                  {"role": "user", "content": prompt}], temperature=0.6)
    try:
        data = extract_json(reply)
    except Exception:
        return {"title": script.get("title") or "", "description": "", "hashtags": [], "hook_line": ""}
    tags = data.get("hashtags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[,\s]+", tags) if t.strip()]
    return {
        "title": str(data.get("title") or "")[:120],
        "description": str(data.get("description") or ""),
        "hashtags": [t if str(t).startswith("#") else "#" + str(t).lstrip("#") for t in tags][:12],
        "hook_line": str(data.get("hook_line") or "")[:140],
    }


def rewrite_scene(scene: dict, instruction: str, article: dict, brand: dict) -> dict:
    """Human-in-the-loop: the user says what to change, the model rewrites one card."""
    prompt = f"""Rewrite ONE card of a short video script. Return only the JSON object for the card.

Card now: {json.dumps(scene, ensure_ascii=False)}
Instruction: {instruction}
Article context: {(article.get('text') or '')[:4000]}
Output language: {_lang(article)}
Rules: "big" max 7 words split on \\n into two lines (stat: one line), body 12-30 words if kind is
fact/cta, bullets 3-4 items max 9 words if kind is list, kicker 2-3 words that do not repeat "big",
chip max 4 words, numbers only from the article."""
    reply = chat([{"role": "system", "content": "You output one JSON object and nothing else."},
                  {"role": "user", "content": prompt}], temperature=0.6)
    data = extract_json(reply)
    merged = {**scene, **{k: v for k, v in data.items() if k in ("kind", "kicker", "big", "body", "chip",
                                                                "bullets", "num", "unit")}}
    return merged


# ---------------------------------------------------------------- normalise / validate

def _words(s: str) -> list[str]:
    return [w for w in str(s or "").replace("\n", " ").split(" ") if w]


def _split_headline(text: str, max_words: int = 7) -> str:
    """Force the two-line headline the design needs, cutting to the word limit."""
    words = _words(text)
    if not words:
        return ""
    words = words[:max_words]
    if len(words) <= 3:
        return " ".join(words)
    cut = (len(words) + 1) // 2
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])


def normalize_script(data: dict, brand: dict, lang: str = "en") -> tuple[dict, list[str]]:
    warn: list[str] = []
    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise AIError("the reply has no scenes")
    scenes: list[dict] = []
    for i, s in enumerate(raw_scenes):
        if not isinstance(s, dict):
            continue
        kind = str(s.get("kind") or "fact").lower()
        if kind not in ("fact", "stat", "list", "cta"):
            kind = "fact"
        out: dict[str, Any] = {"kind": kind,
                               "kicker": " ".join(_words(s.get("kicker"))[:4]),
                               "big": str(s.get("big") or "").strip(),
                               "body": str(s.get("body") or "").strip(),
                               "chip": " ".join(_words(s.get("chip"))[:4])}
        if kind == "stat":
            num = s.get("num")
            try:
                from .compose import parse_num
                out["num"] = parse_num(num)
            except Exception:
                out["num"] = 0
            out["unit"] = str(s.get("unit") or "").strip()[:30]
            out["big"] = " ".join(_words(out["big"]))[:90]
            out["body"] = ""
            if not out["num"]:
                warn.append(f"scene {i + 1}: stat card without a usable number — turned into a fact card")
                out["kind"] = "fact"
                out["body"] = out["body"] or str(s.get("body") or "")
        elif kind == "list":
            bullets = s.get("bullets") or []
            if isinstance(bullets, str):
                bullets = [b.strip() for b in bullets.split("|") if b.strip()]
            bullets = [" ".join(_words(b)[:10]) for b in bullets if str(b).strip()][:4]
            out["bullets"] = bullets
            out["body"] = ""
            if len(bullets) < 2:
                warn.append(f"scene {i + 1}: list card had fewer than 2 usable bullets — turned into a fact card")
                out["kind"] = "fact"
                out["body"] = str(s.get("body") or "")
            else:
                out["big"] = "\n".join(ln for ln in str(out["big"]).split("\n") if ln.strip()) or _split_headline("", 0)
        if out["kind"] in ("fact", "cta"):
            lines = [ln for ln in out["big"].split("\n") if ln.strip()]
            if len(lines) > 2:
                out["big"] = "\n".join(lines[:2])
                warn.append(f"scene {i + 1}: headline had {len(lines)} lines, kept two")
            if len(_words(out["big"])) > 7:
                out["big"] = _split_headline(out["big"], 7)
                warn.append(f"scene {i + 1}: headline trimmed to 7 words")
        if out["kind"] == "fact" and out["body"] and len(_words(out["body"])) > 40:
            out["body"] = " ".join(_words(out["body"])[:34]) + "…"
            warn.append(f"scene {i + 1}: body trimmed")
        scenes.append(out)

    if len(scenes) < 2:
        raise AIError("the reply produced fewer than two usable scenes")

    body_scenes = [s for s in scenes if s["kind"] != "cta"]
    has_cta = any(s["kind"] == "cta" for s in scenes)
    cta = next((s for s in scenes if s["kind"] == "cta"), None)
    if not has_cta:
        cta = {"kind": "cta", "kicker": brand.get("name") or "",
               "big": _split_headline(brand.get("cta_title") or "Learn more", 7),
               "body": brand.get("cta_body") or "", "chip": brand.get("cta_chip") or ""}
        warn.append("no CTA card in the reply — used the brand's CTA")
    else:
        # the CTA card must never drop the brand's offer
        if not cta.get("chip") and brand.get("cta_chip"):
            cta["chip"] = brand["cta_chip"]
        if not cta.get("body") and brand.get("cta_body"):
            cta["body"] = brand["cta_body"]
    keep = [s for s in scenes if s["kind"] != "cta"][:6]
    final = keep + [cta]
    for s in final:
        for k in ("kicker", "big", "chip", "body"):
            s[k] = re.sub(r"[ \t]+", " ", str(s.get(k) or "")).strip()
    script = {
        "title": str(data.get("title") or "")[:120],
        "lang": lang,
        "scenes": final,
        "generated": {"by": "ai", "model": store.get_setting("ai_model"), "at": _now()},
    }
    return script, warn


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M")


def blank_script(brand: dict, lang: str = "en") -> dict:
    """A usable starting point for people who would rather write than prompt."""
    return {
        "title": "New video",
        "lang": lang,
        "scenes": [
            {"kind": "fact", "kicker": "The hook", "big": "Your most\nsurprising fact",
             "body": "One complete sentence that makes someone stop scrolling.", "chip": "Short chip"},
            {"kind": "stat", "kicker": "The number", "num": 0, "unit": "unit",
             "big": "What the number means", "chip": "Context"},
            {"kind": "list", "kicker": "What to know", "big": "Three things\nthat matter",
             "bullets": ["First point", "Second point", "Third point"]},
            {"kind": "cta", "kicker": brand.get("name") or "Your brand",
             "big": _split_headline(brand.get("cta_title") or "Read the full guide", 7),
             "body": brand.get("cta_body") or "", "chip": brand.get("cta_chip") or "Open"},
        ],
        "generated": {"by": "hand", "at": _now()},
    }
