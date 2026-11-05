"""Compose a video: script JSON + design + brand -> a single animated HTML page.

The page is the video. It holds a paused GSAP timeline with one entry per scene;
the renderer seeks that timeline frame by frame and screenshots the result, and
the same page doubles as the in-app live preview.

Nothing here talks to the network or to ffmpeg — it only writes `index.html`.
"""
from __future__ import annotations

import html as _html
import json
import re
import unicodedata
from pathlib import Path

from . import assets_pool, themes

WPS = 2.6                  # words per second, used to time a card by its copy
MIN_D, MAX_D = 3.2, 9.0
FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

RTL_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


# ---------------------------------------------------------------- text utils

def esc(s: str) -> str:
    return _html.escape(str(s or ""), quote=False)


def rich(text: str) -> str:
    """**bold** -> accent-coloured inline highlight."""
    parts = re.split(r"\*\*(.+?)\*\*", str(text or ""))
    return "".join(f'<b class="hl">{esc(p)}</b>' if i % 2 else esc(p) for i, p in enumerate(parts))


def parse_num(value) -> int:
    s = str(value or "0").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    s = re.sub(r"[,\u066c\u066b\s]", "", s)
    try:
        return int(float(s))
    except ValueError:
        return 0


def is_rtl(text: str) -> bool:
    letters = 0
    rtl = 0
    for ch in text or "":
        if not ch.isalpha():
            continue
        letters += 1
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in RTL_RANGES):
            rtl += 1
    return letters > 0 and rtl / letters > 0.3


def digits(n: int, rtl: bool = True) -> str:
    s = str(n)
    return "".join(FA_DIGITS[int(d)] for d in s) if rtl else s


def title_html(big: str) -> str:
    """Two masked lines; the second one carries the accent colour."""
    lines = [ln for ln in str(big or "").split("\n") if ln.strip()] or [""]
    out = []
    for i, line in enumerate(lines[:3]):
        cls = "line l2" if (i == 1 and len(lines) > 1) else "line"
        out.append(f'<div class="{cls}"><div class="line-in">{esc(line)}</div></div>')
    return "".join(out)


def scene_duration(scene: dict) -> float:
    text = " ".join([scene.get("big", ""), scene.get("body", ""), scene.get("chip", ""),
                     " ".join(scene.get("bullets") or [])])
    n = max(3, len(text.split()))
    return round(min(MAX_D, max(MIN_D, n / WPS + 1.2)), 2)


# ---------------------------------------------------------------- scene blocks

def content_html(sc: dict, idx: int, layout: str, rtl: bool) -> str:
    kind = sc.get("kind", "fact")
    kicker = f'<div class="kicker">{esc(sc.get("kicker", ""))}</div>' if sc.get("kicker") else ""
    chip = f'<div class="chip">{esc(sc["chip"])}</div>' if sc.get("chip") else ""

    if kind == "stat":
        return f"""
      <div class="content">
        {kicker}
        <h1 class="title num"><div class="line"><div class="line-in">{digits(parse_num(sc.get('num', 0)), rtl)}<span class="unit">{esc(sc.get('unit',''))}</span></div></div></h1>
        <p class="para">{rich(sc.get('big',''))}</p>
        {chip}
      </div>"""

    if kind == "list":
        rows = "".join(f'<div class="row"><b class="rn">{digits(k + 1, rtl)}</b> {esc(x)}</div>'
                       for k, x in enumerate(sc.get("bullets") or []))
        return f"""
      <div class="content">
        {kicker}
        <h1 class="title sm">{title_html(sc.get('big', ''))}</h1>
        <div class="rows">{rows}</div>
      </div>"""

    para = f'<p class="para">{rich(sc["body"])}</p>' if sc.get("body") else ""
    head = f'<h1 class="title">{title_html(sc.get("big", ""))}</h1>'
    if layout == "band":
        return f"""
      <div class="band">{kicker}{head}</div>
      <div class="content below">{para}{chip}</div>"""
    if layout == "index":
        return f"""
      <div class="idx">{digits(idx + 1, rtl)}</div>
      <div class="content">
        {kicker}{head}<div class="rule"></div>{para}{chip}
      </div>"""
    return f"""
      <div class="content">
        {kicker}{head}<div class="rule"></div>{para}{chip}
      </div>"""


def cta_html(sc: dict, brand: dict) -> str:
    para = f'<p class="para">{rich(sc["body"])}</p>' if sc.get("body") else ""
    chip = f'<div class="chip solid">{esc(sc["chip"])}</div>' if sc.get("chip") else ""
    site = esc(brand.get("site") or "")
    return f"""
      <div class="content">
        <div class="kicker">{esc(sc.get('kicker') or brand.get('name') or '')}</div>
        <h1 class="title">{title_html(sc.get('big', ''))}</h1>
        {para}
        <div class="cta-row">{chip}<div class="domain"><span dir="ltr">{site}</span></div></div>
      </div>"""


# ---------------------------------------------------------------- css

def css(theme: dict, brand: dict, rtl: bool, canvas: tuple[int, int], design_h: int = 1920,
        design_w: int = 1080) -> str:
    font = theme.get("font") or "Vazirmatn"
    scale = min(canvas[0] / design_w, canvas[1] / design_h)
    align = "right" if rtl else "left"
    return f"""
      @font-face {{ font-family:"Vazirmatn"; src:url("/assets/fonts/Vazirmatn-var.woff2") format("woff2"); font-weight:100 900; font-display:block; }}
      :root {{
        --deep:{theme['deep']}; --surface:{theme['surface']}; --ink:{theme['ink']}; --muted:{theme['muted']};
        --accent:{theme['accent']}; --accent-deep:{theme['accent_deep']}; --glow-a:{theme['glow_a']}; --glow-b:{theme['glow_b']};
        --cream:#faf9f6;
      }}
      *{{margin:0;padding:0;box-sizing:border-box}}
      html,body{{width:{canvas[0]}px;height:{canvas[1]}px;overflow:hidden;background:var(--deep);
        font-family:"{font}","Vazirmatn",system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
      /* the design is always laid out at its native size, then scaled to the canvas */
      .stage{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) scale({scale:.4f});
        width:{design_w}px;height:{design_h}px;overflow:hidden}}
      .stage::before{{content:"";position:absolute;inset:-6%;z-index:-1;
        background:radial-gradient(60% 45% at 78% 18%,var(--glow-a) 0%,transparent 70%),
                   radial-gradient(70% 55% at 18% 82%,var(--glow-b) 0%,transparent 72%),
                   linear-gradient(160deg,var(--surface) 0%,var(--deep) 68%);filter:blur(18px) saturate(1.1)}}
      #root{{position:relative;width:{design_w}px;height:{design_h}px;overflow:hidden}}
      .bgbase{{position:absolute;inset:0;background:var(--deep);z-index:0}}
      .broll{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 45%;
        filter:grayscale(.22) contrast(1.05) saturate(.9) brightness(.72);z-index:1}}
      .photo{{position:absolute;inset:-4%;background-size:cover;background-position:center 42%;
        filter:grayscale(.55) contrast(1.02) saturate(.45) brightness(.4) blur(14px)}}
      .scene{{position:absolute;inset:0;overflow:hidden;background:transparent;z-index:2}}
      .a1{{position:absolute;width:1200px;height:1200px;right:-320px;top:-420px;border-radius:50%;
        background:radial-gradient(circle,var(--glow-a) 0%,transparent 62%);filter:blur(10px)}}
      .a2{{position:absolute;width:1400px;height:1400px;left:-460px;bottom:-520px;border-radius:50%;
        background:radial-gradient(circle,var(--glow-b) 0%,transparent 64%);filter:blur(12px)}}
      .scrim{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(4,10,14,.66) 0%,rgba(4,10,14,.2) 30%,rgba(4,10,14,.34) 54%,rgba(4,10,14,.78) 74%,rgba(4,10,14,.96) 100%),linear-gradient(270deg,rgba(4,10,14,.55) 0%,transparent 62%)}}

      /* ---- background treatments ---- */
      .bg-gradient .broll, .bg-gradient .photo{{display:none}}
      .mesh{{position:absolute;inset:0;background:
        radial-gradient(60% 45% at 78% 18%,var(--glow-a) 0%,transparent 70%),
        radial-gradient(70% 55% at 18% 82%,var(--glow-b) 0%,transparent 72%),
        linear-gradient(160deg,var(--surface) 0%,var(--deep) 68%);z-index:1}}
      .bg-duotone .tint{{position:absolute;inset:0;background:linear-gradient(150deg,var(--glow-b),var(--glow-a));
        mix-blend-mode:color;opacity:.75;z-index:1}}
      .bg-duotone .veil{{position:absolute;inset:0;background:linear-gradient(180deg,transparent 10%,rgba(4,10,14,.55) 66%,rgba(4,10,14,.93) 100%);z-index:1}}
      .bg-split .split-top{{position:absolute;top:0;right:0;left:0;height:54%;overflow:hidden;z-index:1}}
      .bg-split .split-top .broll{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
      .bg-split .split-bottom{{position:absolute;bottom:0;right:0;left:0;height:46%;background:var(--surface);z-index:1}}
      .bg-split .edge{{position:absolute;top:54%;right:0;left:0;height:6px;background:var(--accent);z-index:2}}
      /* split frames: copy sits on the solid half, anchored to the bottom edge */
      .bg-split .content{{top:auto;bottom:120px;justify-content:flex-end}}
      .bg-split .foot{{display:none}}
      .bg-split .rows{{gap:14px;margin-top:26px}}
      .bg-split .row{{font-size:32px;padding:14px 20px;line-height:1.35}}
      .bg-split .layout-index .idx{{bottom:140px;font-size:200px}}
      .bg-split .title{{font-size:78px}}
      .bg-split .title.sm{{font-size:70px}}
      .bg-split .para{{font-size:42px;line-height:1.62}}
      .bg-split .kicker{{font-size:27px;padding:8px 20px;margin-bottom:20px}}
      .bg-split .chip{{font-size:32px;padding:12px 30px;margin-top:24px}}
      .bg-split .layout-index .idx{{bottom:300px}}
      .bg-split .foot{{bottom:120px}}

      /* ---- frames ---- */
      .frame{{position:absolute;inset:46px;z-index:7;pointer-events:none}}
      .frame-brackets .frame{{border:1px solid rgba(255,255,255,.16);border-radius:10px}}
      .frame-brackets .frame::before,.frame-brackets .frame::after{{content:"";position:absolute;width:48px;height:48px;border:3px solid var(--accent)}}
      .frame-brackets .frame::before{{bottom:-3px;left:-3px;border-right:0;border-top:0;border-radius:0 0 0 10px}}
      .frame-brackets .frame::after{{top:-3px;left:-3px;border-right:0;border-bottom:0;border-radius:10px 0 0 0}}
      .frame-border .frame{{border:2px solid rgba(255,255,255,.22);border-radius:2px}}
      .frame-rail .frame{{inset:0 0 0 auto;width:14px;background:var(--accent)}}
      .frame-none .frame{{display:none}}
      .grain{{position:absolute;inset:0;z-index:8;pointer-events:none;opacity:.075;mix-blend-mode:overlay;
        background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E")}}

      /* ---- brand ---- */
      .brand{{position:absolute;z-index:6;display:flex;align-items:center;gap:16px}}
      .brand .logo{{height:92px;width:74px;background-image:url("{brand.get('logo') or ''}");background-size:contain;background-repeat:no-repeat;background-position:center;filter:drop-shadow(0 8px 22px rgba(0,0,0,.55))}}
      .brand.no-logo .logo{{display:none}}
      .brand b{{font-size:29px;font-weight:800;color:var(--ink);line-height:1.15}}
      .brand span{{font-size:17px;letter-spacing:.22em;color:var(--muted);font-weight:600}}
      .brand-txt{{display:flex;flex-direction:column}}
      /* every placement is scoped to .brand: the body also carries a brand-* class */
      .brand.brand-header{{top:74px;{align}:78px;left:78px}}
      .brand.brand-vertical{{left:52px;top:50%;transform:translateY(-50%) rotate(180deg);writing-mode:vertical-rl;gap:10px}}
      .brand.brand-vertical .logo{{height:64px;width:52px}}
      .brand.brand-vertical b{{font-size:24px;letter-spacing:.06em}}
      .brand.brand-vertical span{{display:none}}
      .brand.brand-minimal{{{align}:84px;bottom:150px;gap:10px}}
      .brand.brand-minimal .logo{{height:56px;width:44px}}
      .brand.brand-minimal b{{font-size:22px;opacity:.92}}
      .brand.brand-minimal span{{display:none}}
      .brand.brand-none{{display:none}}

      /* ---- content + layouts ---- */
      .content{{position:absolute;right:84px;left:84px;bottom:600px;z-index:5;display:flex;flex-direction:column;align-items:{'flex-start'};justify-content:flex-end;text-align:{align}}}
      .content::before{{content:"";position:absolute;inset:-70px -90px -60px -90px;z-index:-1;pointer-events:none;
        background:radial-gradient(ellipse at 78% 55%,rgba(3,9,13,.86) 0%,rgba(3,9,13,.6) 46%,rgba(3,9,13,0) 78%);filter:blur(8px)}}
      .layout-center .content{{top:50%;bottom:auto;transform:translateY(-50%);left:120px;right:120px;align-items:stretch;text-align:center}}
      .layout-center .title{{width:100%}}
      .layout-center .para{{margin-left:auto;margin-right:auto}}
      .layout-center .content::before{{inset:-90px -120px;background:radial-gradient(ellipse at 50% 50%,rgba(3,9,13,.84) 0%,rgba(3,9,13,.5) 52%,transparent 80%)}}
      .layout-center .rule{{margin-right:auto;margin-left:auto;transform-origin:center center}}
      .layout-center .chip{{align-self:center}}
      .layout-band .band{{position:absolute;top:33%;right:0;left:0;z-index:5;background:var(--accent);
        padding:54px 84px 58px;box-shadow:0 30px 80px rgba(0,0,0,.45)}}
      .layout-band .band .kicker{{color:var(--accent-deep);background:rgba(0,0,0,.12);border-color:rgba(0,0,0,.24);margin-bottom:22px}}
      .layout-band .band .title{{color:var(--accent-deep);font-size:96px;text-shadow:none}}
      .layout-band .band .line.l2 .line-in{{color:var(--accent-deep);opacity:.72}}
      .layout-band .band .title .line-in{{text-align:{align}}}
      .layout-band .below{{bottom:560px;top:auto}}
      .layout-index .idx{{position:absolute;left:70px;bottom:610px;z-index:4;font-size:240px;font-weight:900;
        line-height:.8;color:var(--accent);opacity:.42;letter-spacing:-.05em}}
      .layout-index .content{{right:84px;left:330px}}
      .layout-rail .spine{{position:absolute;right:40px;top:0;bottom:0;width:8px;background:var(--accent);opacity:.85;z-index:6}}
      .layout-rail .spine-txt{{position:absolute;right:66px;top:50%;transform:translateY(-50%) rotate(180deg);
        writing-mode:vertical-rl;font-size:22px;letter-spacing:.3em;color:var(--muted);z-index:6}}
      .layout-rail .content{{right:150px;left:84px}}
      body[dir=ltr] .layout-rail .spine{{right:auto;left:40px}}
      body[dir=ltr] .layout-rail .spine-txt{{right:auto;left:66px;transform:translateY(-50%) rotate(180deg)}}
      body[dir=ltr] .layout-rail .content{{left:150px;right:84px}}
      body[dir=ltr] .layout-index .idx{{left:auto;right:70px}}
      body[dir=ltr] .layout-index .content{{left:84px;right:330px}}
      body[dir=ltr] .frame-rail .frame{{inset:0 auto 0 0}}
      body[dir=ltr] .layout-band .band .title .line-in{{text-align:left}}
      body[dir=ltr] .tr-wipe{{background:linear-gradient(-105deg,transparent 0%,var(--glow-a) 38%,rgba(255,255,255,.22) 52%,var(--glow-a) 66%,transparent 100%)}}

      .kicker{{font-size:32px;font-weight:800;color:var(--accent);background:rgba(6,14,20,.84);
        border:2px solid var(--accent);border-radius:999px;padding:10px 26px;margin-bottom:30px;opacity:.98}}
      .title{{font-size:110px;font-weight:900;line-height:1.16;color:var(--ink);
        text-shadow:0 6px 18px rgba(0,0,0,.85),0 14px 60px rgba(0,0,0,.7)}}
      .title.sm{{font-size:88px}}
      .line{{overflow:hidden;padding:12px 0}}
      .line-in{{display:block;will-change:transform}}
      .line.l2 .line-in{{color:var(--accent);text-shadow:0 4px 10px rgba(0,0,0,.95),0 10px 40px rgba(0,0,0,.85)}}
      .rule{{height:8px;width:200px;background:var(--accent);border-radius:4px;margin-top:28px}}
      .para{{font-size:49px;font-weight:600;line-height:1.7;color:var(--ink);margin-top:28px;max-width:920px;
        text-shadow:0 4px 16px rgba(0,0,0,.85);text-wrap:pretty}}
      .hl{{color:var(--accent);font-weight:800}}
      .title.num .line-in{{color:var(--accent);font-size:230px;line-height:.95;letter-spacing:-.03em}}
      .title.num .unit{{font-size:74px;color:var(--ink);opacity:.92;margin-right:20px;display:inline-block}}
      .stcap .line-in{{color:var(--ink);font-size:76px;font-weight:900;line-height:1.2;
        text-shadow:0 6px 18px rgba(0,0,0,.85),0 14px 50px rgba(0,0,0,.7)}}
      .stcap .line.l2 .line-in{{color:var(--accent)}}
      .rows{{display:flex;flex-direction:column;gap:24px;margin-top:40px;width:100%}}
      .row{{background:rgba(6,16,22,.82);border:1px solid rgba(255,255,255,.2);border-radius:20px;
        padding:20px 26px;font-size:39px;font-weight:600;color:#fff;line-height:1.4;text-align:{align}}}
      .rn{{color:var(--accent);font-weight:900;margin-inline:10px}}
      .chip{{font-size:38px;font-weight:700;color:var(--ink);border:3px solid var(--accent);border-radius:999px;
        padding:14px 38px;background:rgba(6,16,22,.72);margin-top:34px}}
      .chip.solid{{color:var(--cream);background:var(--surface);border-color:var(--surface);margin-top:0}}
      .foot{{position:absolute;right:84px;left:84px;bottom:420px;z-index:6;display:flex;flex-direction:column;gap:18px}}
      /* centred and split layouts move the copy down: keep the rail out of its way */
      .layout-center .foot,.layout-band .foot{{bottom:104px}}
      .bg-split .foot{{display:none}}
      .rail{{height:8px;width:100%;background:rgba(255,255,255,.3);border-radius:4px;overflow:hidden}}
      .railfill{{display:block;height:100%;width:100%;background:linear-gradient(90deg,var(--accent),var(--ink));transform-origin:right center}}
      body[dir=ltr] .railfill{{transform-origin:left center}}
      .site{{font-size:31px;font-weight:700;color:var(--ink);text-align:{align}}}
      .cta-row{{display:flex;align-items:center;gap:26px;margin-top:40px;flex-wrap:wrap}}
      .domain{{font-size:56px;font-weight:900;color:var(--accent-deep);direction:ltr;unicode-bidi:isolate;letter-spacing:.02em}}

      /* ---- CTA card ---- */
      .scene.cta{{background:var(--cream)}}
      .scene.cta .photo,.scene.cta .mesh,.scene.cta .tint,.scene.cta .veil,.scene.cta .split-top,.scene.cta .split-bottom,.scene.cta .edge{{display:none}}
      .scene.cta .scrim{{display:none}}
      .scene.cta .a1{{background:radial-gradient(circle,rgba(120,90,40,.12) 0%,transparent 62%)}}
      .scene.cta .a2{{background:radial-gradient(circle,rgba(20,60,90,.10) 0%,transparent 64%)}}
      .scene.cta .content::before{{display:none}}
      .scene.cta .brand b{{color:var(--surface)}}
      .scene.cta .brand span{{color:rgba(0,0,0,.55)}}
      .scene.cta .kicker{{color:var(--accent-deep);border-color:var(--accent-deep);background:rgba(0,0,0,.04);opacity:1}}
      .scene.cta .title{{color:var(--surface);text-shadow:none}}
      .scene.cta .line.l2 .line-in{{color:var(--accent-deep);text-shadow:none}}
      .scene.cta .para{{color:#1a2b33;text-shadow:none}}
      .scene.cta .hl{{color:var(--accent-deep)}}
      .scene.cta .rail{{background:rgba(0,0,0,.18)}}
      .scene.cta .railfill{{background:linear-gradient(90deg,var(--accent-deep),var(--accent))}}
      .scene.cta .site{{color:var(--surface)}}
      .scene.cta .spine{{background:var(--accent-deep)}}
      .scene.cta .spine-txt{{color:var(--surface);opacity:.62}}
      .scene.cta .frame{{border-color:rgba(0,0,0,.18)!important}}
      .scene.cta .frame::before,.scene.cta .frame::after{{border-color:var(--accent-deep)!important}}
      .scene.cta.frame-rail .frame{{background:var(--accent-deep)}}

      /* ---- transitions ---- */
      .tr{{position:absolute;inset:0;z-index:20;pointer-events:none}}
      .tr-wipe{{background:linear-gradient(105deg,transparent 0%,var(--glow-a) 38%,rgba(255,255,255,.22) 52%,var(--glow-a) 66%,transparent 100%);mix-blend-mode:screen}}
      .tr-slide{{background:var(--accent);opacity:.5}}
      .tr-flash{{background:var(--cream)}}
      .tr-curtain-top{{background:linear-gradient(180deg,var(--deep),transparent);height:40%;opacity:.72}}
      .tr-curtain-bot{{background:linear-gradient(0deg,var(--deep),transparent);height:40%;top:auto;bottom:0;opacity:.72}}
    """


PREVIEW_RUNTIME = """
      // ---- Reelforge runtime: one API for the renderer and the live preview ----
      const VIDEOS = Array.from(document.querySelectorAll('video.clip'));
      let previewTimer = null;
      function syncVideos(t, playing) {
        VIDEOS.forEach(v => {
          const s = parseFloat(v.dataset.start || 0), d = parseFloat(v.dataset.duration || 0);
          const ms = parseFloat(v.dataset.mediaStart || 0);
          const active = t >= s - 0.04 && t < s + d;
          if (active) {
            const target = ms + (t - s);
            if (playing) {
              if (v.paused) { v.currentTime = target; v.play().catch(() => {}); }
            } else {
              if (!v.paused) v.pause();
              if (Math.abs(v.currentTime - target) > 0.05) v.currentTime = target;
            }
          } else if (!v.paused) { v.pause(); }
        });
      }
      window.rf = {
        duration: TOTAL_DURATION,
        mode: 'idle',
        seek(t) {
          this.mode = 'seek';
          if (window.rfPause) window.rfPause();
          tl.seek(t, false);
          syncVideos(t, false);
          return { t: tl.time(), duration: TOTAL_DURATION };
        },
        play(from) {
          this.mode = 'play';
          if (typeof from === 'number') tl.seek(from, false);
          tl.play();
          const tick = () => {
            syncVideos(tl.time(), true);
            const bar = document.getElementById('rf-bar');
            if (bar) bar.style.width = (tl.time() / TOTAL_DURATION * 100).toFixed(2) + '%';
            if (tl.time() < TOTAL_DURATION - 0.02) previewTimer = requestAnimationFrame(tick);
            else this.pause();
          };
          cancelAnimationFrame(previewTimer);
          previewTimer = requestAnimationFrame(tick);
        },
        pause() {
          tl.pause(); cancelAnimationFrame(previewTimer);
          VIDEOS.forEach(v => v.pause());
          document.querySelectorAll('audio').forEach(a => a.pause());
        },
        time() { return tl.time(); }
      };
      window.rfPause = () => window.rf.pause();
      if (location.search.includes('preview')) {
        // the iframe is much smaller than the canvas: scale the whole page to fit it
        const CW = __CANVAS_W__, CH = __CANVAS_H__;
        const fit = () => {
          const k = Math.min(window.innerWidth / CW, window.innerHeight / CH) || 1;
          document.documentElement.style.zoom = k;   // Chromium: scales layout, not just paint
          document.body.style.margin = '0';
        };
        fit();
        window.addEventListener('resize', fit);
        document.querySelectorAll('audio').forEach(a => { try { a.volume = parseFloat(a.dataset.volume || 0.3); } catch (e) {} });
        const start = () => {
          document.removeEventListener('click', start);
          document.querySelectorAll('audio').forEach(a => { a.currentTime = 0; a.play().catch(() => {}); });
          window.rf.play(0);
        };
        document.addEventListener('click', start, { once: true });
        window.addEventListener('message', e => {
          if (e.data === 'play') start();
          if (e.data === 'pause') window.rf.pause();
        });
      }
"""


# ---------------------------------------------------------------- build

def compose(spec: dict, design: dict, brand: dict, *, project_dir: Path, seed: str,
            photo: str | None = None, assets: dict | None = None, format_key: str = "9:16",
            fps: int = 30) -> dict:
    """Write index.html for this script and return timing + audio info."""
    project_dir.mkdir(parents=True, exist_ok=True)
    assets = assets or assets_pool.scan()
    theme = themes.all_themes().get(design.get("theme") or "navy_gold") or themes.THEMES["navy_gold"]

    scenes = [dict(s) for s in spec.get("scenes") or []]
    if not scenes:
        raise ValueError("script has no scenes")

    rtl = is_rtl(" ".join(str(s.get("big", "")) + str(s.get("body", "")) for s in scenes))
    canvas = themes.FORMATS.get(format_key, themes.FORMATS["9:16"])

    t0 = 0.0
    for s in scenes:
        s["_dur"] = scene_duration(s)
        s["_start"] = round(t0, 2)
        t0 += s["_dur"]
    total = round(t0, 2)

    design = dict(design)
    for k in themes.AUTO_KEYS:
        design.setdefault(k, "auto")
    layout = design["layout"] if design["layout"] in themes.LAYOUTS else "editorial"
    bg = design["background"] if design["background"] in themes.BACKGROUNDS else "gradient"
    if bg == "footage" and not assets["broll"]:
        bg = "photo" if photo else "gradient"
    if bg == "split" and not assets["broll"]:
        bg = "photo" if photo else "duotone"
    if bg in ("photo", "duotone", "split") and not assets["broll"] and not photo:
        bg = "gradient"

    clips = assets["broll"]
    music_pool = assets["music"]
    sfx = assets.get("sfx") or {}
    track = assets_pool.pick_music(music_pool, seed)

    vid_html: list[str] = []
    scene_html: list[str] = []
    tweens: list[str] = []
    pre_sets: list[str] = []
    audio_tags: list[str] = []
    audio_plan: list[dict] = []
    used: set[str] = set()

    if track:
        audio_tags.append(f'<audio id="music" class="clip" data-start="0" data-duration="{total}" '
                          f'data-volume="0.30" data-fade-in="1.4" data-fade-out="2.2" '
                          f'src="/assets/music/{esc(Path(track).name)}"></audio>')

    for i, s in enumerate(scenes):
        st, du = s["_start"], s["_dur"]
        kind = s.get("kind", "fact")
        is_cta = kind == "cta"
        sel = f"#s{i}"
        text = " ".join([s.get("kicker", ""), s.get("big", ""), s.get("body", ""),
                         " ".join(s.get("bullets") or []), s.get("chip", "")])

        media = ""
        if not is_cta and bg in ("footage", "duotone", "split"):
            clip = assets_pool.pick_clip(clips, text, f"{seed}:{i}", used)
            if clip:
                used.add(clip)
                cname = Path(clip).name
                cdur = assets_pool.clip_duration(Path(clip))
                start_off = round(((assets_pool.h(seed, i) % 500) / 100) + 0.4, 2)
                if cdur > 1.0:
                    start_off = round(min(start_off, max(0.0, cdur - min(du, cdur) - 0.1)), 2)
                vtag = (f'<video class="broll clip" id="v{i}" data-start="{st}" data-duration="{du}" '
                        f'data-media-start="{start_off}" data-clip-duration="{cdur}" '
                        f'src="/assets/broll/{esc(cname)}" muted playsinline preload="auto"></video>')
                if bg == "split":
                    vid_html.append(f'      <div class="split-top">{vtag}</div>')
                else:
                    vid_html.append("      " + vtag)

        body = cta_html(s, brand) if is_cta else content_html(s, i, layout, rtl)
        extra = ""
        if bg == "duotone":
            extra += '<div class="tint"></div><div class="veil"></div>'
        elif bg == "gradient":
            extra += '<div class="mesh"></div>'
        elif bg == "split" and not is_cta:
            extra += '<div class="split-bottom"></div><div class="edge"></div>'
        elif bg == "photo" and not is_cta:
            extra += f'<div class="photo" style="background-image:url(\'{photo}\')"></div>'
        if layout == "rail":
            extra += f'<div class="spine"></div><div class="spine-txt">{esc(brand.get("latin") or "")}</div>'

        brand_cls = " no-logo" if not brand.get("logo") else ""
        scene_html.append(f"""
    <section class="scene clip{' cta' if is_cta else ''}" id="s{i}" data-start="{st}" data-duration="{du}"{'' if i == 0 else ' style="opacity:0"'}>
      {extra}
      <div class="a1"></div><div class="a2"></div>
      <div class="scrim"></div>
      <div class="brand{brand_cls}">
        <div class="logo" role="img" aria-label="{esc(brand.get('name') or '')}"></div>
        <div class="brand-txt"><b>{esc(brand.get('name') or '')}</b><span>{esc(brand.get('latin') or '')}</span></div>
      </div>
      {body}
      <div class="frame"></div><div class="grain"></div>
      <footer class="foot"><div class="rail"><i class="railfill"></i></div>
        <div class="site">{esc(brand.get('footer_cta') if is_cta else brand.get('site'))}</div></footer>
    </section>""")

        # ---- motion
        tweens.append(f'  tl.fromTo("{sel} .photo, {sel} .broll", {{scale:1.05}}, {{scale:1.14, duration:{du}, ease:"none"}}, {st});')
        tweens.append(f'  tl.fromTo("{sel} .a1", {{xPercent:-8, yPercent:-4, opacity:.2}}, {{xPercent:8, yPercent:6, opacity:.5, duration:{du}, ease:"none"}}, {st});')
        if i > 0:
            tweens.append(f'  tl.fromTo("{sel} .kicker", {{opacity:0, y:-18}}, {{opacity:1, y:0, duration:.4, ease:"power3.out"}}, {st + 0.06});')

        if kind == "stat":
            tweens.append(f'  tl.fromTo("{sel} .title.num .line-in", {{opacity:0, y:24}}, {{opacity:1, y:0, duration:.5, ease:"power3.out"}}, {st + 0.16});')
        elif kind == "list":
            tweens.append(f'  tl.fromTo("{sel} .title .line-in", {{yPercent:112}}, {{yPercent:0, duration:.55, stagger:.08, ease:"power3.out"}}, {st + 0.08});')
            tweens.append(f'  tl.fromTo("{sel} .row", {{opacity:0, x:40}}, {{opacity:1, x:0, duration:.45, stagger:.16, ease:"power3.out"}}, {st + 0.38});')
            for k in range(len(s.get("bullets") or [])):
                if sfx.get("tick"):
                    audio_tags.append(f'<audio id="sfx-t{i}-{k}" class="clip" data-start="{round(st + 0.38 + 0.16 * k, 2)}" '
                                      f'data-duration="0.07" data-volume="0.26" src="/assets/sfx/{esc(Path(sfx["tick"]).name)}"></audio>')
                    audio_plan.append({"src": f"/assets/sfx/{Path(sfx['tick']).name}", "at": round(st + 0.38 + 0.16 * k, 2),
                                       "volume": 0.26})
        elif i == 0:
            tweens.append(f'  tl.fromTo("{sel} .content", {{scale:1.02, opacity:1}}, {{scale:1, duration:1.2, ease:"power2.out"}}, 0);')
        else:
            tweens.append(f'  tl.fromTo("{sel} .title .line-in", {{yPercent:112, opacity:0}}, {{yPercent:0, opacity:1, duration:.6, stagger:.09, ease:"expo.out"}}, {st + 0.1});')
            tweens.append(f'  tl.fromTo("{sel} .rule", {{scaleX:0}}, {{scaleX:1, duration:.5, ease:"power2.out", transformOrigin:"right center"}}, {st + 0.4});')
            if s.get("body"):
                tweens.append(f'  tl.fromTo("{sel} .para", {{opacity:0, y:26}}, {{opacity:1, y:0, duration:.55, ease:"power2.out"}}, {st + 0.5});')
        if s.get("chip"):
            tweens.append(f'  tl.fromTo("{sel} .chip", {{opacity:0, y:20, scale:.95}}, {{opacity:1, y:0, scale:1, duration:.45, ease:"back.out(1.6)"}}, {st + 0.55});')
        if is_cta:
            tweens.append(f'  tl.fromTo("{sel} .domain", {{opacity:0, scale:.9}}, {{opacity:1, scale:1, duration:.55, ease:"back.out(1.4)"}}, {st + 0.7});')
            if sfx.get("thump"):
                audio_tags.append(f'<audio id="sfx-thump" class="clip" data-start="{round(st, 2)}" data-duration="0.34" '
                                  f'data-volume="0.5" src="/assets/sfx/{esc(Path(sfx["thump"]).name)}"></audio>')
                audio_plan.append({"src": f"/assets/sfx/{Path(sfx['thump']).name}", "at": round(st, 2), "volume": 0.5})
        # progress rail
        if rtl:
            tweens.append(f'  tl.fromTo("{sel} .railfill", {{scaleX:{round(st / total, 4)}}}, {{scaleX:{round((st + du) / total, 4)}, duration:{du}, ease:"none", transformOrigin:"right center"}}, {st});')
        else:
            tweens.append(f'  tl.fromTo("{sel} .railfill", {{scaleX:{round((st + du) / total, 4)}}}, {{scaleX:{round(st / total, 4)}, duration:{du}, ease:"none", transformOrigin:"left center"}}, {st});')

        if i > 0:
            tweens.append(f'  tl.fromTo("{sel}", {{opacity:0}}, {{opacity:1, duration:.2, ease:"none"}}, {st});')
            if design["transition"] == "zoom":
                tweens.append(f'  tl.fromTo("{sel} .content", {{scale:1.12, filter:"blur(8px)"}}, {{scale:1, filter:"blur(0px)", duration:.6, ease:"power3.out"}}, {st});')
            else:
                tweens.append(f'  tl.fromTo("{sel} .content", {{scale:1.04}}, {{scale:1, duration:.45, ease:"power3.out"}}, {st});')
            if sfx.get("whoosh"):
                audio_tags.append(f'<audio id="sfx-w{i}" class="clip" data-start="{round(max(st - 0.12, 0), 2)}" data-duration="0.42" '
                                  f'data-volume="0.36" src="/assets/sfx/{esc(Path(sfx["whoosh"]).name)}"></audio>')
                audio_plan.append({"src": f"/assets/sfx/{Path(sfx['whoosh']).name}", "at": round(max(st - 0.12, 0), 2),
                                   "volume": 0.36})
        if i < len(scenes) - 1:
            tweens.append(f'  tl.to("{sel}", {{opacity:0, duration:.18, ease:"none"}}, {st + du - 0.18});')

    # ---- transitions between scenes
    tr = design["transition"]
    tr_html = ""
    for i, s in enumerate(scenes):
        if i == 0:
            continue
        at = round(s["_start"] - 0.24, 2)
        if tr == "wipe":
            tr_html = '<div class="tr tr-wipe" id="trw"></div>'
            pre_sets.append('gsap.set("#trw", {xPercent: -130});')
            tweens.append(f'  tl.set("#trw", {{xPercent:-130}}, {at});')
            tweens.append(f'  tl.to("#trw", {{xPercent:130, duration:.55, ease:"power3.inOut"}}, {at});')
        elif tr == "slide":
            tr_html = '<div class="tr tr-slide" id="trs"></div>'
            pre_sets.append('gsap.set("#trs", {xPercent: -110});')
            tweens.append(f'  tl.set("#trs", {{xPercent:-110}}, {at});')
            tweens.append(f'  tl.to("#trs", {{xPercent:110, duration:.5, ease:"power3.inOut"}}, {at});')
        elif tr == "flash":
            tr_html = '<div class="tr tr-flash" id="trf" style="opacity:0"></div>'
            tweens.append(f'  tl.set("#trf", {{opacity:0}}, {at});')
            tweens.append(f'  tl.to("#trf", {{opacity:.5, duration:.12, ease:"power1.in"}}, {at});')
            tweens.append(f'  tl.to("#trf", {{opacity:0, duration:.3, ease:"power1.out"}}, {at + 0.12});')
        elif tr == "curtain":
            tr_html = ('<div class="tr tr-curtain-top" id="trct"></div>'
                       '<div class="tr tr-curtain-bot" id="trcb"></div>')
            pre_sets.append('gsap.set("#trct", {yPercent: -100});')
            pre_sets.append('gsap.set("#trcb", {yPercent: 100});')
            tweens.append(f'  tl.set("#trct", {{yPercent:-100}}, {at});')
            tweens.append(f'  tl.set("#trcb", {{yPercent:100}}, {at});')
            tweens.append(f'  tl.to(["#trct", "#trcb"], {{yPercent:0, duration:.22, ease:"power2.in"}}, {at});')
            tweens.append(f'  tl.to("#trct", {{yPercent:-100, duration:.26, ease:"power2.out"}}, {at + 0.24});')
            tweens.append(f'  tl.to("#trcb", {{yPercent:100, duration:.26, ease:"power2.out"}}, {at + 0.24});')

    page = f"""<!doctype html>
<html lang="{'fa' if rtl else 'en'}" dir="{'rtl' if rtl else 'ltr'}" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={canvas['w']}, height={canvas['h']}" />
    <title>{esc(spec.get('title') or seed)}</title>
    <script src="/vendor/gsap.min.js"></script>
    <style>{css(theme, brand, rtl, (canvas['w'], canvas['h']))}</style>
  </head>
  <body class="layout-{layout} bg-{bg} frame-{design['frame']} brand-{design['brand']}">
    <div class="stage">
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{canvas['w']}" data-height="{canvas['h']}">
      <div class="bgbase"></div>
{chr(10).join(vid_html)}
{''.join(scene_html)}
      {tr_html}
{chr(10).join(audio_tags)}
    </div>
    </div>
    <script>
      {chr(10).join(pre_sets)}
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tweens)}
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
      tl.seek(0);
      const TOTAL_DURATION = {total};
      {PREVIEW_RUNTIME.replace("__CANVAS_W__", str(canvas['w'])).replace("__CANVAS_H__", str(canvas['h']))}
    </script>
  </body>
</html>
"""
    (project_dir / "index.html").write_text(page, encoding="utf-8")
    info = {
        "total": total,
        "scenes": [{"kind": s.get("kind", "fact"), "start": s["_start"], "duration": s["_dur"]} for s in scenes],
        "design": design,
        "theme": design.get("theme"),
        "rtl": rtl,
        "music": Path(track).name if track else None,
        "sfx": audio_plan,
        "format": format_key,
        "canvas": canvas,
        "fps": fps,
    }
    (project_dir / "meta.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def clean_text(s: str) -> str:
    """Normalise the invisible junk that arrives from web pages and LLMs."""
    s = unicodedata.normalize("NFC", str(s or ""))
    for ch in ("\u200e", "\u200f", "\u202a", "\u202b", "\u202c", "\u2066", "\u2067", "\u2069", "\ufeff"):
        s = s.replace(ch, "")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()
