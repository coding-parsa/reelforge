"""Input: pull the actual text out of a URL, or take what the user pasted.

No BeautifulSoup, no lxml — a small HTMLParser that keeps headings, paragraphs,
list items and quotes, drops navigation/scripts/boilerplate, and picks the lead
image. Good enough for blogs, docs and news, and it keeps the app dependency-free.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from html.parser import HTMLParser

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 Reelforge/1.0"}

SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form", "svg", "iframe",
             "noscript", "button", "select", "textarea", "label", "template"}
JUNK_HEADINGS = ("related", "مطالب مرتبط", "مقالات مرتبط", "خواندنی", "نظرات", "دیدگاه", "comments",
                 "share", "اشتراک", "منابع", "references", "سلب مسئولیت", "disclaimer",
                 "درباره نویسنده", "about the author", "بیشتر بخوانید", "read more")
PROMO = ("مشاوره", "رایگان", "تماس", "تیم ما", "همراهی", "ثبت‌نام کنید", "همین حالا", "کلیک",
         "واتساپ", "اینستاگرام", "شماره", "subscribe", "newsletter", "sign up", "cookie")

_WS = re.compile(r"[ \t\u00a0]+")
_NL = re.compile(r"\s*\n\s*")


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.blocks: list[dict] = []
        self.title = ""
        self.h1 = ""
        self.image = ""
        self.description = ""
        self._buf: list[str] = []
        self._mode: str | None = None
        self._skip_depth = 0
        self._in_title = False

    # -- helpers
    def _flush(self) -> None:
        if not self._mode:
            self._buf = []
            return
        text = _WS.sub(" ", "".join(self._buf)).strip()
        self._buf = []
        if len(text) >= 2:
            self.blocks.append({"type": self._mode, "text": text})
        self._mode = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "blockquote", "figcaption", "td"):
            self._flush()
            if tag == "h1":
                self._mode = "h1"
            elif tag in ("h2", "h3", "h4"):
                self._mode = "h2"
            elif tag == "li":
                self._mode = "li"
            elif tag == "blockquote":
                self._mode = "quote"
            elif tag == "figcaption":
                self._mode = "cap"
            else:
                self._mode = "p"
        elif tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            content = (a.get("content") or "").strip()
            if prop in ("og:image", "twitter:image") and content and not self.image:
                self.image = content
            elif prop in ("og:title", "twitter:title") and content and not self.title:
                self.title = content
            elif prop in ("description", "og:description") and content and not self.description:
                self.description = content
        elif tag == "img" and not self.image:
            src = a.get("src") or a.get("data-src") or ""
            if src and not src.startswith("data:"):
                self.image = src
        elif tag == "br":
            self._buf.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "blockquote", "figcaption", "td"):
            self._flush()

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        if self._mode:
            self._buf.append(data.replace("\n", " "))


def _clean_block(text: str) -> str:
    t = _WS.sub(" ", text).strip()
    t = re.sub(r"\s+([،؛:.!؟])", r"\1", t)
    return t


def parse_html(html: str, url: str = "") -> dict:
    r = _Reader()
    try:
        r.feed(html)
    except Exception:
        pass
    r._flush()

    blocks: list[dict] = []
    for b in r.blocks:
        text = _clean_block(b["text"])
        if b["type"] == "h1" and not r.h1:
            r.h1 = text
        if len(text) < 2:
            continue
        if b["type"] in ("p", "quote") and len(text.split()) < 6:
            continue
        if b["type"] == "h2" and len(text.split()) < 2:
            continue
        blocks.append({"type": b["type"], "text": text})

    # drop everything after a "related posts / comments" heading
    for i, b in enumerate(blocks):
        if b["type"] == "h2" and any(j in b["text"].lower() for j in JUNK_HEADINGS):
            blocks = blocks[:i]
            break
    # promo boxes near the end of an article are not content
    trimmed: list[dict] = []
    for b in blocks:
        if b["type"] == "li" and any(p in b["text"] for p in PROMO) and len(b["text"].split()) < 12:
            continue
        if trimmed and trimmed[-1]["text"] == b["text"]:
            continue
        trimmed.append(b)
    blocks = trimmed

    title = (r.h1 or r.title or r.description).strip()
    title = re.sub(r"\s+[|\-–—]\s+.*$", "", title).strip() if len(title) > 45 else title
    words = sum(len(b["text"].split()) for b in blocks)
    image = r.image
    if image and url:
        image = urllib.parse.urljoin(url, image)
    text = "\n\n".join(b["text"] for b in blocks)
    headings = sum(1 for b in blocks if b["type"] == "h2")
    long_paras = sum(1 for b in blocks if b["type"] == "p" and len(b["text"].split()) > 45)
    listing = headings >= 6 and long_paras < 2
    return {
        "listing": listing,
        "url": url,
        "title": title[:220],
        "description": r.description[:400],
        "image": image,
        "blocks": blocks,
        "word_count": words,
        "text": text,
        "lang": detect_lang(text),
        "fetched": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def detect_lang(text: str) -> str:
    sample = (text or "")[:2000]
    fa = sum(1 for c in sample if "\u0600" <= c <= "\u06ff")
    latin = sum(1 for c in sample if "a" <= c.lower() <= "z")
    if fa > latin * 0.6:
        return "fa"
    if latin:
        return "en"
    return "und"


def from_text(text: str, title: str = "") -> dict:
    """Everything the user pasted or typed becomes a one-block "article"."""
    raw = (text or "").strip()
    blocks: list[dict] = []
    for chunk in re.split(r"\n\s*\n", raw):
        clean = _clean_block(chunk)
        if clean:
            blocks.append({"type": "p", "text": clean})
    if not blocks and raw:
        blocks = [{"type": "p", "text": _clean_block(raw)}]
    words = sum(len(b["text"].split()) for b in blocks)
    first_line = blocks[0]["text"][:120] if blocks else ""
    return {
        "url": "", "title": (title or first_line)[:220], "description": "",
        "image": "", "blocks": blocks, "word_count": words,
        "text": "\n\n".join(b["text"] for b in blocks),
        "lang": detect_lang(raw), "fetched": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def fetch(url: str, timeout: int = 45, retries: int = 2) -> dict:
    """Download and parse a page. Throws a readable error when the site blocks us."""
    last = ""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}")
            if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                resp.encoding = resp.apparent_encoding or "utf-8"
            doc = parse_html(resp.text, resp.url)
            if doc["word_count"] < 40:
                raise RuntimeError("page looked empty (JavaScript-only or blocked)")
            return doc
        except Exception as exc:
            last = str(exc)[:200]
            if attempt < retries:
                time.sleep(2 + attempt * 3)
    raise RuntimeError(f"could not read {url}: {last}")


def fetch_image(url: str, dest_dir, name: str = "photo.jpg") -> str | None:
    """Cache the article's lead image locally so previews and renders agree."""
    from pathlib import Path
    if not url:
        return None
    dest = Path(dest_dir) / name
    if dest.exists() and dest.stat().st_size > 2000:
        return dest.name
    try:
        resp = requests.get(url, headers=UA, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 2000:
            dest.write_bytes(resp.content)
            return dest.name
    except Exception:
        pass
    return None


BLOCKED_SEGMENTS = {"blog", "news", "fa", "en", "de", "tr", "ar", "ru", "zh", "cn", "category",
                    "categories", "tag", "tags", "author", "page", "feed", "search", "index"}


def looks_like_article(url: str) -> bool:
    """A sitemap lists everything; keep the pages that look like one article."""
    import urllib.parse
    segs = [s for s in urllib.parse.urlparse(url).path.split("/") if s]
    if len(segs) < 2:
        return False
    last = urllib.parse.unquote(segs[-1]).lower()
    if "%20" in url or " " in url:
        return False
    if last in BLOCKED_SEGMENTS or len(last) < 12 or last.isdigit():
        return False
    if "-" not in last and "_" not in last:
        return False
    if re.fullmatch(r"\d{4}", last) or last.startswith("page-"):
        return False
    return True


def sitemap(url: str, prefix: str = "", limit: int = 200) -> list[str]:
    """Collect article URLs from a sitemap (follows one level of sitemap-index)."""
    def _locs(target: str) -> list[str]:
        resp = requests.get(target, headers=UA, timeout=45)
        resp.raise_for_status()
        return re.findall(r"<loc>\s*(.*?)\s*</loc>", resp.text)

    found: list[str] = []
    try:
        locs = _locs(url)
    except Exception as exc:
        raise RuntimeError(f"sitemap unreadable: {exc}")
    children = [u for u in locs if u.endswith((".xml", ".xml.gz"))]
    pages = [u for u in locs if u not in children]
    for child in children[:20]:
        try:
            pages += [u for u in _locs(child) if not u.endswith((".xml", ".xml.gz"))]
        except Exception:
            continue
    seen: set[str] = set()
    for u in pages:
        if prefix and prefix not in u:
            continue
        if not looks_like_article(u):
            continue
        if u in seen:
            continue
        seen.add(u)
        found.append(u)
        if len(found) >= limit:
            break
    return found
