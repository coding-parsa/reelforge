"""Build a script from an article with no model at all.

This is the floor of the product: paste an article, get cards. It reads the
extracted text, keeps the sentences that carry the point, and assembles
hook → number → two points → list → warning → CTA. The wording is the article's
own, so nothing is invented, and the rules are the same the AI is held to
(7-word headlines, one-sentence bodies, CTA verbatim).

It is deliberately plain rather than clever: a script that is honest beats a
script that is confident and wrong, and anyone can edit a card afterwards.
"""
from __future__ import annotations

import hashlib
import re

WORD_SPLIT = re.compile(r"\s+")

WARN_WORDS = ("باید", "توجه", "هشدار", "مهم", "ممنوع", "جریمه", "ریسک", "خطر", "اشتباه", "نکنید",
              "مشکل", "دیر", "از دست", "مراقب", "هزینه",
              "must", "warning", "important", "never", "risk", "penalty", "mistake", "avoid",
              "expensive", "delay", "problem", "careful", "cost", "fail")

REF_WORDS = ("جدول", "شکل", "تصویر", "نمودار", "در ادامه", "همین صفحه", "بالا", "زیر را",
             "table", "figure", "chart", "below", "above", "as you can see")

# headings that promise structure rather than say anything
BAD_HEADS = ("مقدمه", "بررسی کامل", "سوالات متداول", "سؤالات متداول", "منابع", "جمع‌بندی", "خلاصه",
             "فهرست مطالب", "سلب مسئولیت", "نتیجه‌گیری", "درباره", "تماس",
             "introduction", "overview", "faq", "summary", "conclusion", "table of contents",
             "disclaimer", "related", "about", "contact", "sources", "references")

# sentences about the page itself, not about the topic
META_SENTENCES = ("در این راهنما", "در این مقاله", "این مقاله", "این مطلب", "در ادامه", "همین صفحه",
                  "در این بخش", "در این نوشته", "این صفحه",
                  "in this guide", "in this article", "this article", "this guide", "this post",
                  "below you", "in this section")

LABELS = {
    "fa": {
        "hook": ["نکتهٔ اصلی", "چیزی که مهم است", "قبل از هر کاری"],
        "stat": ["عدد کلیدی", "رقم مهم", "سقف واقعی"],
        "point": ["نکتهٔ کاربردی", "جزئیات مهم", "قبل از اقدام"],
        "list": ["فهرست کوتاه", "چند نکته", "یک نگاه سریع"],
        "warn": ["هشدار", "اشتباه رایج", "مراقب باش"],
    },
    "en": {
        "hook": ["The point", "What matters", "Before anything"],
        "stat": ["The number", "Worth knowing", "The real limit"],
        "point": ["Worth knowing", "The detail", "Before you act"],
        "list": ["Quick list", "The short version", "At a glance"],
        "warn": ["Careful", "Common mistake", "Watch out"],
    },
}


def _w(text: str) -> list[str]:
    return [x for x in WORD_SPLIT.split(str(text or "").strip()) if x]


def _seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _clean(text: str) -> str:
    t = str(text or "")
    t = re.sub(r"\[[^\]]{0,80}\]|\((?:منبع|source)[^)]*\)", " ", t, flags=re.I)
    t = re.sub(r"https?://\S+", " ", t)
    for ch in ("\u200e", "\u200f", "\u202a", "\u202b", "\u202c"):
        t = t.replace(ch, "")
    t = re.sub(r"\s+", " ", t).strip(" .،؛:-—·")
    return t


def _clip(text: str, n_words: int) -> str:
    """Cut to n words, preferring a clause/sentence boundary over a dangling word."""
    parts = _w(text)
    if len(parts) <= n_words:
        return " ".join(parts)
    head = " ".join(parts[:n_words])
    for punct in (".", "؟", "?", "!", "،", "؛", ";", ","):
        cut = head.rfind(punct)
        if cut >= len(head) * 0.45:
            return head[:cut + (1 if punct in ".؟?!" else 0)].strip()
    tail = re.search(r"\s(و|که|اگر|با|در|برای|تا|از|به|بر|یا|ولی|اما|چون|and|or|but|with|for|to|of|in)$", head)
    if tail:
        head = head[:tail.start()].strip()
    return head + " …"


def _two_lines(text: str, max_words: int = 7) -> str:
    """Two balanced lines, never more than max_words in total."""
    words = _w(text)[:max_words]
    if len(words) <= 3:
        return " ".join(words)
    cut = (len(words) + 1) // 2
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])


def _headline(text: str, max_words: int = 7) -> str:
    """A headline from a heading: drop the colon clause, brackets and trailing 'and'."""
    t = re.split(r"[:؛;]", _clean(text))[0].strip()
    if t.count("(") != t.count(")"):
        t = re.sub(r"\([^)]*$", "", t).strip()
    words = _w(t)[:max_words]
    while words and words[-1].lower() in ("و", "با", "برای", "در", "از", "که", "تا", "and", "with", "for", "of", "to"):
        words.pop()
    return _two_lines(" ".join(words), max_words)


def _sentences(article: dict) -> list[str]:
    out = []
    for b in article.get("blocks") or []:
        if b.get("type") not in ("p", "quote", "li"):
            continue
        text = _clean(b.get("text", ""))
        for s in re.split(r"(?<=[.!?؟])\s+", text):
            s = s.strip()
            if 25 <= len(s) <= 300 and 5 <= len(_w(s)) <= 45:
                out.append(s)
    return out


def _readable(sentence: str, rtl: bool) -> bool:
    if "§" in sentence or sentence.count("(") != sentence.count(")"):
        return False
    latin = sum(1 for c in sentence if "a" <= c.lower() <= "z")
    if not rtl and latin < len(sentence) * 0.4:
        return False
    if rtl and latin > len(sentence) * 0.45:      # a Persian card with a wall of Latin text
        return False
    if sentence.strip().endswith((":", "،", ",")):
        return False
    return True


NUM = re.compile(r"(?P<num>[۰-۹0-9][۰-۹0-9,٬.]*)\s*(?P<unit>درصد|سال|ماه|هفته|روز|ساعت|ترم|هزار|میلیون|"
                 r"میلیارد|دلار|یورو|لیر|روبل|یوان|تومان|نفر|بار|درخواست|شرکت|کشور|"
                 r"percent|%|years?|months?|weeks?|days?|hours?|thousand|million|billion|"
                 r"euros?|dollars?|pounds?|people|applicants|companies|attempts|times?)", re.I)


def _find_stat(texts: list[str]) -> tuple[str, str, str] | None:
    for t in texts:
        m = NUM.search(t)
        if not m:
            continue
        num = m.group("num").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        num = re.sub(r"[,٬]", "", num)
        try:
            value = int(float(num))
        except ValueError:
            continue
        if value <= 0 or value > 100_000_000:
            continue
        return str(value), m.group("unit").strip(), t
    return None


POINT_TITLES = {
    "fa": {
        "cost": ("چه چیزی\nگران تمام می‌شود", "قیمت واقعی"),
        "pattern": ("اکثر مردم\nاین کار را می‌کنند", "الگوی رایج"),
        "rule": ("تنها شرط\nواقعی", "قاعدهٔ سخت"),
        "default": ("این را\nدست‌کم نگیر", "نکتهٔ مهم"),
    },
    "en": {
        "cost": ("What it\nactually costs", "The real price"),
        "pattern": ("What most\npeople do", "The pattern"),
        "rule": ("The one\nrequirement", "Hard rule"),
        "default": ("Worth\nknowing", "The detail"),
    },
}

COST_WORDS = ("هزینه", "پول", "یورو", "دلار", "تومان", "شهریه", "دستمزد", "درآمد", "پرداخت",
              "cost", "pay", "euro", "dollar", "price", "fee", "salary", "wage", "money")
PATTERN_WORDS = ("اکثر", "بیشتر", "معمولاً", "همیشه", "خیلی‌ها", "بعضی", "اغلب",
                 "most", "usually", "often", "always", "many", "few", "sometimes")
RULE_WORDS = ("باید", "فقط", "لازم", "شرط", "ممنوع", "اجازه", "بدون",
              "must", "only", "need", "require", "cannot", "without", "allowed")


def _point_titles(sentence: str, lang: str) -> tuple[str, str]:
    pool = POINT_TITLES["fa" if lang == "fa" else "en"]
    low = sentence.lower()
    if any(w in low for w in COST_WORDS):
        kind = "cost"
    elif any(w in low for w in PATTERN_WORDS):
        kind = "pattern"
    elif any(w in low for w in RULE_WORDS):
        kind = "rule"
    else:
        kind = "default"
    big, kicker = pool[kind]
    return big, kicker


def _cta(brand: dict) -> dict:
    return {
        "kind": "cta",
        "kicker": brand.get("name") or "",
        "big": _two_lines(brand.get("cta_title") or "Read the full guide", 7),
        "body": brand.get("cta_body") or "",
        "chip": brand.get("cta_chip") or "",
    }


def build(article: dict, brand: dict) -> tuple[dict, list[str]]:
    """Return (script, warnings). Always yields at least a hook and a CTA."""
    warnings: list[str] = []
    lang = article.get("lang") or "en"
    rtl = lang == "fa"
    labels = LABELS["fa" if rtl else "en"]
    seed = _seed((article.get("title") or "") + (article.get("url") or ""))

    def label(kind: str, index: int) -> str:
        options = labels[kind]
        return options[(seed + index) % len(options)]

    title = _clean(article.get("title") or "")
    paras = [_clean(b.get("text", "")) for b in article.get("blocks") or []
             if b.get("type") == "p" and len(_w(b.get("text", ""))) >= 12]
    sents = _sentences(article)
    used: set[str] = set()

    def take(n_words: int, pool: list[str] | None = None, avoid_refs: bool = True) -> str:
        candidates = pool if pool is not None else sents
        for strict in ((True, False) if avoid_refs else (False,)):
            for cand in candidates:
                if not _readable(cand, rtl):
                    continue
                if any(m in cand.lower() for m in META_SENTENCES):
                    continue
                key = cand[:50]
                if key in used:
                    continue
                if strict and any(r in cand.lower() for r in REF_WORDS):
                    continue
                used.add(key)
                return _clip(cand, n_words)
        return ""

    scenes: list[dict] = []

    # 1. hook — the article's own opening, on the title
    if len(_w(title)) > 9 and ":" in title:
        head, _, tail = title.partition(":")
        if len(_w(head)) >= 4:
            title = head.strip()
    lead = take(30, paras[:3]) or _clip(article.get("description") or title, 30)
    scenes.append({"kind": "fact", "kicker": label("hook", 0),
                   "big": _two_lines(title or lead, 7), "body": lead, "chip": ""})

    # 2. the number, if the article has one that means something
    stat = _find_stat(paras[:8])
    if stat:
        num, unit, source = stat
        clause = next((c.strip() for c in re.split(r"[،؛،,.]", source) if num in c), "")
        if 2 <= len(_w(clause)) <= 12:
            scenes.append({"kind": "stat", "kicker": label("stat", 1), "num": int(num), "unit": unit,
                           "big": _clip(clause, 9), "chip": f"{num} {unit}"[:38]})

    # 3–4. two points from the article's own headings, with the paragraph that
    # actually sits under that heading (a card whose text belongs to another section
    # is worse than no card at all)
    blocks = article.get("blocks") or []
    for idx, head in enumerate(blocks):
        if len(scenes) >= 4:
            break
        if head.get("type") != "h2":
            continue
        text = _clean(head.get("text", ""))
        if not text or len(_w(text)) < 2 or len(text) > 90:
            continue
        if any(text.lower().startswith(j) for j in BAD_HEADS):
            continue
        big = _headline(text, 7)
        if not big or big.lower() in {s["big"].lower() for s in scenes}:
            continue
        pool: list[str] = []
        for nxt in blocks[idx + 1: idx + 4]:
            if nxt.get("type") == "h2":
                break
            if nxt.get("type") in ("p", "quote"):
                pool += [x.strip() for x in re.split(r"(?<=[.!?؟])\s+", _clean(nxt.get("text", "")))
                         if 25 <= len(x.strip()) <= 300]
        body = ""
        for cand in pool:
            if _readable(cand, rtl) and not any(m in cand.lower() for m in META_SENTENCES) \
                    and cand[:50] not in used:
                used.add(cand[:50])
                body = _clip(cand, 26)
                break
        if not body:
            body = take(26)
        if not body:
            continue
        scenes.append({"kind": "fact", "kicker": label("point", len(scenes)), "big": big,
                       "body": body, "chip": ""})

    # 4b. no headings (or too few cards): use the strongest remaining sentences.
    # The headline is a neutral frame and the sentence itself is the body, so nothing
    # is invented — the reader still gets the article's own words.
    while len(scenes) < 4:
        body = take(26)
        if not body:
            break
        big, kicker = _point_titles(body, lang)
        if big in {s["big"] for s in scenes}:
            break
        scenes.append({"kind": "fact", "kicker": kicker, "big": big, "body": body, "chip": ""})

    # 5. a list, if the article has one
    bullets = []
    for b in article.get("blocks") or []:
        if b.get("type") != "li":
            continue
        text = _clean(b.get("text", ""))
        if not (2 <= len(_w(text)) <= 12) or text.endswith(":") or text in bullets:
            continue
        if not _readable(text, rtl):
            continue
        bullets.append(_clip(text, 9))
        if len(bullets) == 4:
            break
    if len(bullets) >= 3:
        scenes.append({"kind": "list", "kicker": label("list", len(scenes)),
                       "big": _two_lines("Four things that matter" if not rtl else "چهار نکتهٔ مهم", 7),
                       "bullets": bullets, "chip": ""})

    # 6. the sentence that warns you, if there is one
    warn = ""
    for s in sents:
        if any(w in s.lower() for w in WARN_WORDS) and _readable(s, rtl) and s[:50] not in used:
            warn = _clip(s, 26)
            break
    if warn:
        scenes.append({"kind": "fact", "kicker": label("warn", len(scenes)),
                       "big": _two_lines("The part people miss" if not rtl else "بخشی که از دست می‌رود", 7),
                       "body": warn, "chip": ""})

    if len(scenes) < 3:
        warnings.append("the article was thin — only a couple of cards could be filled, edit freely")

    scenes = scenes[:5] + [_cta(brand)]
    script = {"title": (title or "New video")[:90], "lang": lang, "scenes": scenes,
              "generated": {"by": "auto", "at": _now()}}
    return script, warnings


def meta(article: dict, script: dict, brand: dict) -> dict:
    """Publishing text without a model: the article's own words plus honest hashtags."""
    lang = script.get("lang") or article.get("lang") or "en"
    title = _clean(article.get("title") or script.get("title") or "")[:70]
    first = ""
    for b in article.get("blocks") or []:
        if b.get("type") == "p":
            first = _clip(_clean(b.get("text", "")), 26)
            break
    tags = ["#" + re.sub(r"[^\w\u0600-\u06FF]+", "", (brand.get("name") or "video")).lower()]
    for word in (_w(title.lower()))[:12]:
        w = re.sub(r"[^\w\u0600-\u06FF]+", "", word)
        if len(w) > 4 and w not in tags:
            tags.append("#" + w)
        if len(tags) >= 6:
            break
    hook = script["scenes"][0]["big"].replace("\n", " ") if script.get("scenes") else title
    return {"title": title, "description": first, "hashtags": tags[:6], "hook_line": hook[:110],
            "source": "auto"}


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M")
